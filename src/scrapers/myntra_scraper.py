"""
Myntra.com scraper implementation.
"""
import re
from typing import Dict, List, Optional, Generator
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from datetime import datetime

from .base_scraper import BaseScraper
from ..data.models import ProductModel, ReviewModel, PricingModel, SiteEnum, ProductCategory
from ..config.logging_config import loggers


class MyntraScraper(BaseScraper):
    """Myntra.com specific scraper implementation."""
    
    def __init__(self):
        super().__init__(SiteEnum.MYNTRA)
        self.base_url = "https://www.myntra.com"
        self.search_url = "https://www.myntra.com/shop"
    
    def search_products(self, query: str, category: str = None, max_pages: int = 5) -> Generator[Dict, None, None]:
        """Search for products on Myntra."""
        try:
            # Build search parameters
            params = {
                'q': query,
                'p': 1
            }
            
            # Add category filter if specified
            if category == 'clothing':
                params['categories'] = 'Clothing'
            
            for page in range(1, max_pages + 1):
                if page > 1:
                    params['p'] = page
                
                response = self.make_request(self.search_url, params=params)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find product containers
                product_containers = soup.find_all('li', class_='product-base') or \
                                   soup.find_all('div', class_='product-productMetaInfo')
                
                if not product_containers:
                    self.logger.warning(f"No products found on page {page}")
                    break
                
                for container in product_containers:
                    product_data = self._extract_search_result(container)
                    if product_data:
                        yield product_data
                
        except Exception as e:
            self.logger.error(f"Error searching Myntra products: {e}")
    
    def _extract_search_result(self, container) -> Optional[Dict]:
        """Extract product data from search result container."""
        try:
            # Product URL
            link_element = container.find('a') or container.find('a', class_='product-base')
            if not link_element:
                return None
            
            product_url = urljoin(self.base_url, link_element.get('href', ''))
            
            # Product name
            title_element = container.find('h3', class_='product-brand') or \
                           container.find('h4', class_='product-product')
            if not title_element:
                return None
            
            brand = self.extract_text_safe(container.find('h3', class_='product-brand'))
            product_name = self.extract_text_safe(container.find('h4', class_='product-product'))
            name = f"{brand} {product_name}".strip()
            
            # Price
            price_element = container.find('span', class_='product-discountedPrice') or \
                           container.find('div', class_='product-price')
            price = self.clean_price(self.extract_text_safe(price_element)) if price_element else None
            
            # Rating
            rating_element = container.find('span', class_='product-rating')
            rating = None
            if rating_element:
                rating_text = self.extract_text_safe(rating_element)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Image
            img_element = container.find('img', class_='img-responsive')
            image_url = self.extract_attribute_safe(img_element, 'src')
            
            return {
                'url': product_url,
                'name': name,
                'price': price,
                'rating': rating,
                'image': image_url,
                'site': 'myntra'
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting Myntra search result: {e}")
            return None
    
    def scrape_product_details(self, product_url: str) -> Optional[ProductModel]:
        """Scrape detailed product information from Myntra."""
        try:
            response = self.make_request(product_url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Product name and brand
            brand_element = soup.find('h1', class_='pdp-title') or \
                           soup.find('span', class_='pdp-brand')
            brand = self.extract_text_safe(brand_element)
            
            name_element = soup.find('h1', class_='pdp-name') or \
                          soup.find('span', class_='pdp-name')
            product_name = self.extract_text_safe(name_element)
            
            name = f"{brand} {product_name}".strip()
            if not name:
                return None
            
            # Product ID from URL and name
            product_id = self.generate_product_id(product_url, name)
            
            # Category - Myntra is primarily clothing/fashion
            category = ProductCategory.CLOTHING
            
            # Description
            description_element = soup.find('div', class_='pdp-product-description-content') or \
                                 soup.find('div', class_='product-details')
            description = self.extract_text_safe(description_element)
            
            # Specifications
            specifications = {}
            spec_containers = soup.find_all('div', class_='index-rowKey') + \
                            soup.find_all('div', class_='product-details-item')
            
            for i, container in enumerate(spec_containers):
                if i >= 10:  # Limit to 10 specifications
                    break
                key_element = container.find('span') or container
                key = self.extract_text_safe(key_element)
                
                # Try to find corresponding value
                value_container = container.find_next_sibling() or \
                                container.find_next('div', class_='index-rowValue')
                if value_container:
                    value = self.extract_text_safe(value_container)
                    if key and value:
                        specifications[key] = value
            
            # Images
            images = []
            image_containers = soup.find_all('div', class_='image-grid-image') or \
                             soup.find_all('img', class_='img-responsive')
            
            for container in image_containers[:5]:  # Limit to 5 images
                if container.name == 'img':
                    img_url = self.extract_attribute_safe(container, 'src')
                else:
                    img_element = container.find('img')
                    img_url = self.extract_attribute_safe(img_element, 'src') if img_element else None
                
                if img_url and img_url not in images:
                    # Convert to high resolution if possible
                    if 'w_200' in img_url:
                        img_url = img_url.replace('w_200', 'w_500')
                    images.append(img_url)
            
            # Stock status
            in_stock = True
            stock_elements = soup.find_all('div', class_='size-buttons-size-button') + \
                           soup.find_all('span', class_='myntraweb-sprite')
            
            available_sizes = 0
            for element in stock_elements:
                if 'available' in self.extract_text_safe(element).lower():
                    available_sizes += 1
            
            # If no sizes are available, product is out of stock
            if len(stock_elements) > 0 and available_sizes == 0:
                in_stock = False
            
            return ProductModel(
                product_id=product_id,
                site=SiteEnum.MYNTRA,
                name=name,
                category=category,
                brand=brand,
                url=product_url,
                description=description,
                specifications=specifications,
                images=images,
                in_stock=in_stock
            )
            
        except Exception as e:
            self.logger.error(f"Error scraping Myntra product details: {e}")
            return None
    
    def scrape_product_reviews(self, product_url: str, max_reviews: int = 100) -> List[ReviewModel]:
        """Scrape product reviews from Myntra."""
        reviews = []
        try:
            # Get product ID for reviews
            product_name = self._get_product_name(product_url)
            if not product_name:
                return reviews
            
            product_id = self.generate_product_id(product_url, product_name)
            
            # Myntra reviews are often loaded via AJAX, try to get from main page first
            response = self.make_request(product_url)
            if not response:
                return reviews
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find review containers
            review_containers = soup.find_all('div', class_='user-review') or \
                              soup.find_all('div', class_='review-item')
            
            scraped_count = 0
            for container in review_containers:
                if scraped_count >= max_reviews:
                    break
                
                review = self._extract_review(container, product_id)
                if review:
                    reviews.append(review)
                    scraped_count += 1
            
            # If no reviews found on main page, try reviews endpoint
            if not reviews:
                reviews_url = product_url.replace('/buy', '/reviews')
                if reviews_url != product_url:
                    response = self.make_request(reviews_url)
                    if response:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        review_containers = soup.find_all('div', class_='user-review-main')
                        
                        for container in review_containers:
                            if scraped_count >= max_reviews:
                                break
                            
                            review = self._extract_review(container, product_id)
                            if review:
                                reviews.append(review)
                                scraped_count += 1
            
        except Exception as e:
            self.logger.error(f"Error scraping Myntra reviews: {e}")
        
        return reviews
    
    def _get_product_name(self, product_url: str) -> Optional[str]:
        """Get product name from URL for ID generation."""
        try:
            response = self.make_request(product_url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            brand_element = soup.find('h1', class_='pdp-title') or \
                           soup.find('span', class_='pdp-brand')
            brand = self.extract_text_safe(brand_element)
            
            name_element = soup.find('h1', class_='pdp-name') or \
                          soup.find('span', class_='pdp-name')
            product_name = self.extract_text_safe(name_element)
            
            return f"{brand} {product_name}".strip() if brand or product_name else None
        except Exception:
            return None
    
    def _extract_review(self, container, product_id: str) -> Optional[ReviewModel]:
        """Extract review data from review container."""
        try:
            # Review title
            title_element = container.find('div', class_='user-review-reviewTitle') or \
                           container.find('h4', class_='review-title')
            title = self.extract_text_safe(title_element)
            
            # Review content
            content_element = container.find('div', class_='user-review-reviewText') or \
                             container.find('div', class_='review-text')
            content = self.extract_text_safe(content_element)
            if not content:
                return None
            
            # Rating
            rating_element = container.find('div', class_='user-review-rating') or \
                           container.find('span', class_='review-rating')
            rating = 5.0  # Default
            if rating_element:
                rating_text = self.extract_text_safe(rating_element)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Reviewer name
            reviewer_element = container.find('div', class_='user-review-left') or \
                              container.find('span', class_='reviewer-name')
            reviewer_name = self.extract_text_safe(reviewer_element)
            
            # Verified purchase - Myntra typically shows verified purchases
            verified_purchase = True  # Assume verified for Myntra
            
            # Review date
            date_element = container.find('div', class_='user-review-date') or \
                          container.find('span', class_='review-date')
            review_date = None
            if date_element:
                date_text = self.extract_text_safe(date_element)
                try:
                    # Parse common date formats
                    date_patterns = [
                        r'(\d{1,2} \w+ \d{4})',
                        r'(\w+ \d{1,2}, \d{4})',
                        r'(\d{1,2}/\d{1,2}/\d{4})'
                    ]
                    for pattern in date_patterns:
                        date_match = re.search(pattern, date_text)
                        if date_match:
                            try:
                                review_date = datetime.strptime(date_match.group(1), '%d %b %Y')
                            except ValueError:
                                try:
                                    review_date = datetime.strptime(date_match.group(1), '%b %d, %Y')
                                except ValueError:
                                    review_date = datetime.strptime(date_match.group(1), '%d/%m/%Y')
                            break
                except Exception:
                    pass
            
            review_id = self.generate_review_id(product_id, content, reviewer_name)
            
            return ReviewModel(
                review_id=review_id,
                product_id=product_id,
                site=SiteEnum.MYNTRA,
                title=title,
                content=content,
                rating=rating,
                reviewer_name=reviewer_name,
                verified_purchase=verified_purchase,
                review_date=review_date
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting Myntra review: {e}")
            return None
    
    def scrape_product_pricing(self, product_url: str) -> Optional[PricingModel]:
        """Scrape current pricing information from Myntra."""
        try:
            response = self.make_request(product_url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Product ID
            brand_element = soup.find('h1', class_='pdp-title') or \
                           soup.find('span', class_='pdp-brand')
            brand = self.extract_text_safe(brand_element)
            
            name_element = soup.find('h1', class_='pdp-name') or \
                          soup.find('span', class_='pdp-name')
            product_name = self.extract_text_safe(name_element)
            
            name = f"{brand} {product_name}".strip()
            product_id = self.generate_product_id(product_url, name)
            
            # Current price
            current_price = None
            price_elements = [
                soup.find('span', class_='pdp-price'),
                soup.find('div', class_='product-discountedPrice'),
                soup.find('span', class_='product-price')
            ]
            
            for element in price_elements:
                if element:
                    price = self.clean_price(self.extract_text_safe(element))
                    if price:
                        current_price = price
                        break
            
            if current_price is None:
                return None
            
            # Original price (MRP)
            original_price = None
            mrp_element = soup.find('span', class_='pdp-mrp') or \
                         soup.find('div', class_='product-strike')
            if mrp_element:
                original_price = self.clean_price(self.extract_text_safe(mrp_element))
            
            # Discount calculation
            discount_percentage = None
            discount_amount = None
            discount_element = soup.find('span', class_='pdp-discount') or \
                              soup.find('div', class_='product-discount')
            if discount_element:
                discount_text = self.extract_text_safe(discount_element)
                discount_match = re.search(r'(\d+)%', discount_text)
                if discount_match:
                    discount_percentage = float(discount_match.group(1))
            
            if original_price and original_price > current_price:
                if not discount_amount:
                    discount_amount = original_price - current_price
                if not discount_percentage:
                    discount_percentage = (discount_amount / original_price) * 100
            
            # Offers
            offers = []
            offer_elements = soup.find_all('div', class_='pdp-offers-content') + \
                           soup.find_all('span', class_='offer-text')
            for element in offer_elements:
                text = self.extract_text_safe(element)
                if text and len(text) > 10:  # Filter short text
                    offers.append(text)
            
            price_id = self.generate_price_id(product_id)
            
            return PricingModel(
                price_id=price_id,
                product_id=product_id,
                site=SiteEnum.MYNTRA,
                current_price=current_price,
                original_price=original_price,
                discount_percentage=discount_percentage,
                discount_amount=discount_amount,
                offers=offers[:3]  # Limit to 3 offers
            )
            
        except Exception as e:
            self.logger.error(f"Error scraping Myntra pricing: {e}")
            return None