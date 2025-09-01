"""
Base scraper interface with common functionality.
"""
import time
import requests
import urllib.robotparser
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Generator
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

from ..config.settings import settings
from ..config.logging_config import loggers
from ..data.models import ProductModel, ReviewModel, PricingModel, SiteEnum


class RateLimiter:
    """Rate limiting utility for ethical scraping."""
    
    def __init__(self, max_requests_per_second: float = 0.5):
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = {}
    
    def wait_if_needed(self, domain: str):
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        if domain in self.last_request_time:
            time_since_last = current_time - self.last_request_time[domain]
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
        
        self.last_request_time[domain] = time.time()


class RobotsChecker:
    """Robots.txt compliance checker."""
    
    def __init__(self):
        self.robots_cache = {}
    
    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """Check if URL can be fetched according to robots.txt."""
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            if base_url not in self.robots_cache:
                robots_url = urljoin(base_url, "/robots.txt")
                rp = urllib.robotparser.RobotFileParser()
                rp.set_url(robots_url)
                rp.read()
                self.robots_cache[base_url] = rp
            
            return self.robots_cache[base_url].can_fetch(user_agent, url)
        except Exception as e:
            loggers["scraper"].warning(f"Error checking robots.txt for {url}: {e}")
            return True  # Allow by default if robots.txt check fails


class BaseScraper(ABC):
    """Base scraper interface with common functionality."""
    
    def __init__(self, site: SiteEnum, user_agent: str = None):
        self.site = site
        self.logger = loggers["scraper"]
        self.rate_limiter = RateLimiter(settings.MAX_REQUESTS_PER_SECOND)
        self.robots_checker = RobotsChecker()
        
        # HTTP session setup
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent or settings.USER_AGENTS.get(site.value, settings.USER_AGENTS["amazon"]),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Retry strategy
        retry_strategy = Retry(
            total=settings.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.site_config = settings.SITES.get(site.value, {})
    
    def make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Make a rate-limited, robots.txt-compliant HTTP request.
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object or None if request failed
        """
        try:
            # Check robots.txt compliance
            if not self.robots_checker.can_fetch(url):
                self.logger.warning(f"Robots.txt disallows fetching {url}")
                return None
            
            # Rate limiting
            domain = urlparse(url).netloc
            self.rate_limiter.wait_if_needed(domain)
            
            # Make request
            response = self.session.get(
                url, 
                timeout=settings.REQUEST_TIMEOUT,
                **kwargs
            )
            response.raise_for_status()
            
            self.logger.debug(f"Successfully fetched {url}")
            return response
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            return None
    
    def extract_text_safe(self, element, default: str = "") -> str:
        """Safely extract text from BeautifulSoup element."""
        try:
            return element.get_text(strip=True) if element else default
        except Exception:
            return default
    
    def extract_attribute_safe(self, element, attribute: str, default: str = "") -> str:
        """Safely extract attribute from BeautifulSoup element."""
        try:
            return element.get(attribute, default) if element else default
        except Exception:
            return default
    
    def clean_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text."""
        try:
            import re
            # Remove currency symbols and extract numbers
            price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
            if price_match:
                return float(price_match.group().replace(',', ''))
        except Exception:
            pass
        return None
    
    def generate_product_id(self, url: str, name: str) -> str:
        """Generate a unique product ID from URL and name."""
        import hashlib
        combined = f"{self.site.value}_{url}_{name}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def generate_review_id(self, product_id: str, content: str, reviewer: str = "") -> str:
        """Generate a unique review ID."""
        import hashlib
        combined = f"{product_id}_{content[:100]}_{reviewer}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def generate_price_id(self, product_id: str) -> str:
        """Generate a unique price ID."""
        import hashlib
        timestamp = str(int(time.time()))
        combined = f"{product_id}_{timestamp}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    @abstractmethod
    def search_products(self, query: str, category: str = None, max_pages: int = 5) -> Generator[Dict, None, None]:
        """
        Search for products on the site.
        
        Args:
            query: Search query
            category: Product category
            max_pages: Maximum pages to scrape
            
        Yields:
            Dictionary containing product search results
        """
        pass
    
    @abstractmethod
    def scrape_product_details(self, product_url: str) -> Optional[ProductModel]:
        """
        Scrape detailed product information.
        
        Args:
            product_url: URL of the product page
            
        Returns:
            ProductModel instance or None if scraping failed
        """
        pass
    
    @abstractmethod
    def scrape_product_reviews(self, product_url: str, max_reviews: int = 100) -> List[ReviewModel]:
        """
        Scrape product reviews.
        
        Args:
            product_url: URL of the product page
            max_reviews: Maximum number of reviews to scrape
            
        Returns:
            List of ReviewModel instances
        """
        pass
    
    @abstractmethod
    def scrape_product_pricing(self, product_url: str) -> Optional[PricingModel]:
        """
        Scrape current pricing information.
        
        Args:
            product_url: URL of the product page
            
        Returns:
            PricingModel instance or None if scraping failed
        """
        pass
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()