"""
Flipkart.com scraper implementation.
"""
import re
from typing import Dict, List, Optional, Generator
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from datetime import datetime

from .base_scraper import BaseScraper
from ..data.models import ProductModel, ReviewModel, PricingModel, SiteEnum, ProductCategory
from ..config.logging_config import loggers


class FlipkartScraper(BaseScraper):
    """Flipkart.com specific scraper implementation."""
    
    def __init__(self):
        super().__init__(SiteEnum.FLIPKART)
        self.base_url = "https://www.flipkart.com"
        self.search_url = "https://www.flipkart.com/search"
    
    def search_products(self, query: str, category: str = None, max_pages: int = 5) -> Generator[Dict, None, None]:
        """Search for products on Flipkart."""
        try:
            # Build search parameters
            params = {
                'q': query,
                'page': 1
            }
            
            for page in range(1, max_pages + 1):
                if page > 1:
                    params['page'] = page
                
                response = self.make_request(self.search_url, params=params)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find product containers
                product_containers = soup.find_all('div', class_='_1AtVbE') or \
                                   soup.find_all('div', class_='_13oc-S')
                
                if not product_containers:
                    self.logger.warning(f"No products found on page {page}")
                    break
                
                for container in product_containers:
                    product_data = self._extract_search_result(container)
                    if product_data:
                        yield product_data
                
        except Exception as e:
            self.logger.error(f"Error searching Flipkart products: {e}")
    
    def _extract_search_result(self, container) -> Optional[Dict]:
        """Extract product data from search result container."""
        try:
            # Product URL
            link_element = container.find('a', class_='IRpwTa') or \
                          container.find('a', class_='_1fQZEK')
            if not link_element:
                return None
            
            product_url = urljoin(self.base_url, link_element.get('href', ''))
            
            # Product name
            title_element = container.find('div', class_='_4rR01T') or \
                           container.find('a', class_='IRpwTa')
            if not title_element:
                return None
            
            name = self.extract_text_safe(title_element)
            
            # Price
            price_element = container.find('div', class_='_30jeq3') or \
                           container.find('div', class_='_1_WHN1')
            price = self.clean_price(self.extract_text_safe(price_element)) if price_element else None
            
            # Rating
            rating_element = container.find('div', class_='_3LWZlK')
            rating = None
            if rating_element:
                rating_text = self.extract_text_safe(rating_element)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Image
            img_element = container.find('img', class_='_396cs4')
            image_url = self.extract_attribute_safe(img_element, 'src')
            
            return {
                'url': product_url,
                'name': name,
                'price': price,
                'rating': rating,
                'image': image_url,
                'site': 'flipkart'
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting Flipkart search result: {e}")
            return None
    
    def scrape_product_details(self, product_url: str) -> Optional[ProductModel]:
        """Scrape detailed product information from Flipkart."""
        try:
            response = self.make_request(product_url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Product name
            name_element = soup.find('span', class_='B_NuCI') or \
                          soup.find('h1', class_='yhB1nd')
            if not name_element:
                return None
            name = self.extract_text_safe(name_element)
            
            # Product ID from URL and name
            product_id = self.generate_product_id(product_url, name)
            
            # Brand
            brand_element = soup.find('span', class_='G6XhRU') or \
                           soup.find('a', class_='_2bc4-')
            brand = self.extract_text_safe(brand_element)
            
            # Category - try to determine from breadcrumbs
            category = ProductCategory.ELECTRONICS  # Default
            breadcrumb = soup.find('div', class_='_1MR4o5')
            if breadcrumb:
                breadcrumb_text = self.extract_text_safe(breadcrumb).lower()
                if 'clothing' in breadcrumb_text or 'fashion' in breadcrumb_text:
                    category = ProductCategory.CLOTHING
                elif 'home' in breadcrumb_text or 'kitchen' in breadcrumb_text:
                    category = ProductCategory.HOME_KITCHEN
                elif 'book' in breadcrumb_text:
                    category = ProductCategory.BOOKS
                elif 'sport' in breadcrumb_text:
                    category = ProductCategory.SPORTS
            
            # Description/Highlights
            description_parts = []
            highlight_elements = soup.find_all('li', class_='_21Ahn-')
            for element in highlight_elements:
                text = self.extract_text_safe(element)
                if text:
                    description_parts.append(text)
            description = '. '.join(description_parts[:5])  # Limit to 5 highlights
            
            # Specifications
            specifications = {}
            spec_tables = soup.find_all('table', class_='_14cfVK')
            for table in spec_tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) == 2:
                        key = self.extract_text_safe(cols[0])
                        value = self.extract_text_safe(cols[1])
                        if key and value:
                            specifications[key] = value
            
            # Images
            images = []
            image_containers = soup.find_all('div', class_='_396cs4') or \
                             soup.find_all('img', class_='_396cs4')
            for container in image_containers[:5]:  # Limit to 5 images
                if container.name == 'img':
                    img_url = self.extract_attribute_safe(container, 'src')
                else:
                    img_element = container.find('img')
                    img_url = self.extract_attribute_safe(img_element, 'src') if img_element else None
                
                if img_url and img_url not in images:
                    images.append(img_url)
            
            # Stock status
            in_stock = True
            stock_elements = soup.find_all('div', class_='_16FRp0') + \
                           soup.find_all('button', class_='_2KpZ6l')
            for element in stock_elements:
                stock_text = self.extract_text_safe(element).lower()
                if 'out of stock' in stock_text or 'sold out' in stock_text:
                    in_stock = False
                    break
            
            return ProductModel(
                product_id=product_id,
                site=SiteEnum.FLIPKART,
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
            self.logger.error(f"Error scraping Flipkart product details: {e}")
            return None
    
    def scrape_product_reviews(self, product_url: str, max_reviews: int = 100) -> List[ReviewModel]:
        """Scrape product reviews from Flipkart."""
        reviews = []
        try:
            # Get product ID for reviews
            product_name = self._get_product_name(product_url)
            if not product_name:
                return reviews
            
            product_id = self.generate_product_id(product_url, product_name)
            
            # Navigate to reviews section
            response = self.make_request(product_url)
            if not response:
                return reviews
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find review containers
            review_containers = soup.find_all('div', class_='_16PBlm') or \
                              soup.find_all('div', class_='_27M-vq')
            
            scraped_count = 0
            for container in review_containers:
                if scraped_count >= max_reviews:
                    break
                
                review = self._extract_review(container, product_id)
                if review:
                    reviews.append(review)
                    scraped_count += 1
            
        except Exception as e:
            self.logger.error(f"Error scraping Flipkart reviews: {e}")
        
        return reviews
    
    def _get_product_name(self, product_url: str) -> Optional[str]:
        """Get product name from URL for ID generation."""
        try:
            response = self.make_request(product_url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            name_element = soup.find('span', class_='B_NuCI') or \
                          soup.find('h1', class_='yhB1nd')
            return self.extract_text_safe(name_element) if name_element else None
        except Exception:
            return None
    
    def _extract_review(self, container, product_id: str) -> Optional[ReviewModel]:
        """Extract review data from review container."""
        try:
            # Review title
            title_element = container.find('p', class_='_2-N8zT')
            title = self.extract_text_safe(title_element)
            
            # Review content
            content_element = container.find('div', class_='t-ZTKy') or \
                             container.find('div', class_='_1AtVbE')
            content = self.extract_text_safe(content_element)
            if not content:
                return None
            
            # Rating
            rating_element = container.find('div', class_='_3LWZlK') or \
                           container.find('div', class_='_1BLPMq')
            rating = 5.0  # Default
            if rating_element:
                rating_text = self.extract_text_safe(rating_element)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Reviewer name
            reviewer_element = container.find('p', class_='_2sc7ZR') or \
                              container.find('span', class_='_2V5EHH')
            reviewer_name = self.extract_text_safe(reviewer_element)
            
            # Verified purchase - look for certified buyer badge
            verified_element = container.find('span', class_='_2V5EHH')
            verified_purchase = False
            if verified_element:
                verified_text = self.extract_text_safe(verified_element).lower()
                verified_purchase = 'certified buyer' in verified_text
            
            # Review date
            date_element = container.find('span', class_='_3PlgRk') or \
                          container.find('p', class_='_2sc7ZR')
            review_date = None
            if date_element:
                date_text = self.extract_text_safe(date_element)
                try:
                    # Parse date patterns common in Flipkart
                    date_patterns = [
                        r'(\d{1,2} \w+ \d{4})',
                        r'(\w+ \d{1,2}, \d{4})'
                    ]
                    for pattern in date_patterns:
                        date_match = re.search(pattern, date_text)
                        if date_match:
                            try:
                                review_date = datetime.strptime(date_match.group(1), '%d %b %Y')
                            except ValueError:
                                review_date = datetime.strptime(date_match.group(1), '%b %d, %Y')
                            break
                except Exception:
                    pass
            
            review_id = self.generate_review_id(product_id, content, reviewer_name)
            
            return ReviewModel(
                review_id=review_id,
                product_id=product_id,
                site=SiteEnum.FLIPKART,
                title=title,
                content=content,
                rating=rating,
                reviewer_name=reviewer_name,
                verified_purchase=verified_purchase,
                review_date=review_date
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting Flipkart review: {e}")
            return None
    
    def scrape_product_pricing(self, product_url: str) -> Optional[PricingModel]:
        """Scrape current pricing information from Flipkart."""
        try:
            response = self.make_request(product_url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Product ID
            name_element = soup.find('span', class_='B_NuCI') or \
                          soup.find('h1', class_='yhB1nd')
            name = self.extract_text_safe(name_element)
            product_id = self.generate_product_id(product_url, name)
            
            # Current price
            current_price = None
            price_elements = [
                soup.find('div', class_='_30jeq3'),
                soup.find('div', class_='_1_WHN1'),
                soup.find('div', class_='_16Jk6d')
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
            mrp_element = soup.find('div', class_='_3I9_wc') or \
                         soup.find('div', class_='_14Jd01')
            if mrp_element:
                original_price = self.clean_price(self.extract_text_safe(mrp_element))
            
            # Discount calculation
            discount_percentage = None
            discount_amount = None
            discount_element = soup.find('div', class_='_3Ay6Sb')
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
            offer_elements = soup.find_all('li', class_='_16_mp8') + \
                           soup.find_all('span', class_='_2Janr0')
            for element in offer_elements:
                text = self.extract_text_safe(element)
                if text and len(text) > 10:  # Filter short text
                    offers.append(text)
            
            price_id = self.generate_price_id(product_id)
            
            return PricingModel(
                price_id=price_id,
                product_id=product_id,
                site=SiteEnum.FLIPKART,
                current_price=current_price,
                original_price=original_price,
                discount_percentage=discount_percentage,
                discount_amount=discount_amount,
                offers=offers[:3]  # Limit to 3 offers
            )
            
        except Exception as e:
            self.logger.error(f"Error scraping Flipkart pricing: {e}")
            return None