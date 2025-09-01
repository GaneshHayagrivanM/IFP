"""
Utility functions for scrapers.
"""
import time
import random
from typing import List, Dict, Any
from urllib.parse import urlparse, urljoin
import hashlib


def generate_user_agent_pool() -> List[str]:
    """Generate a pool of user agents for rotation."""
    return [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
    ]


def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """Add random delay between requests."""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def normalize_url(url: str, base_url: str = None) -> str:
    """Normalize URL by making it absolute and cleaning parameters."""
    if base_url and not url.startswith('http'):
        url = urljoin(base_url, url)
    
    # Remove common tracking parameters
    tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'ref', 'tag']
    parsed = urlparse(url)
    
    # For now, return as-is but this could be extended to clean params
    return url


def extract_price_from_text(text: str) -> float:
    """Extract price from text using various patterns."""
    import re
    
    if not text:
        return None
    
    # Remove common currency symbols and clean text
    cleaned = re.sub(r'[₹,\s]', '', text)
    
    # Try to match price patterns
    patterns = [
        r'(\d+\.?\d*)',  # Basic number
        r'Rs\.?(\d+\.?\d*)',  # Rs. prefix
        r'INR\s*(\d+\.?\d*)',  # INR prefix
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return None


def hash_content(content: str) -> str:
    """Generate hash for content deduplication."""
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    import re
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return sanitized[:255]  # Limit length


def batch_items(items: List[Any], batch_size: int = 100) -> List[List[Any]]:
    """Split items into batches."""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def is_valid_product_url(url: str, site: str) -> bool:
    """Check if URL is a valid product URL for the given site."""
    if not url:
        return False
    
    site_patterns = {
        'amazon': ['/dp/', '/gp/product/'],
        'flipkart': ['/p/', '/product/'],
        'myntra': ['/buy', '/product/']
    }
    
    patterns = site_patterns.get(site.lower(), [])
    return any(pattern in url for pattern in patterns)


def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
    
    import re
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters that might cause issues
    cleaned = re.sub(r'[^\w\s\-.,!?()\'"]', '', cleaned)
    
    return cleaned


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return ""


def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0):
    """Retry function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)