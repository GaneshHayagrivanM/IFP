"""
Amazon.in scraper implementation.
"""
import re
from typing import Dict, List, Optional, Generator
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
from datetime import datetime

from .base_scraper import BaseScraper
from ..data.models import ProductModel, ReviewModel, PricingModel, SiteEnum, ProductCategory
from ..config.logging_config import loggers


class AmazonScraper(BaseScraper):
    """Amazon.in specific scraper implementation."""
    
    def __init__(self):
        super().__init__(SiteEnum.AMAZON)
        self.base_url = "https://www.amazon.in"
        self.search_url = "https://www.amazon.in/s"
    
    def search_products(self, query: str, category: str = None, max_pages: int = 5) -> Generator[Dict, None, None]:
        """Search for products on Amazon.in."""
        try:
            # Build search parameters
            params = {
                'k': query,
                'ref': 'sr_pg_1'
            }
            
            # Add category filter if specified
            if category:
                category_mapping = {
                    'electronics': 'electronics',
                    'clothing': 'fashion',
                    'home-kitchen': 'home-garden',
                    'books': 'stripbooks',
                    'sports': 'sports'
                }
                if category in category_mapping:
                    params['i'] = category_mapping[category]
            
            for page in range(1, max_pages + 1):
                if page > 1:
                    params['page'] = page
                
                response = self.make_request(self.search_url, params=params)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find product containers
                product_containers = soup.find_all('div', {'data-component-type': 's-search-result'})
                
                if not product_containers:
                    self.logger.warning(f"No products found on page {page}")
                    break
                
                for container in product_containers:
                    product_data = self._extract_search_result(container)
                    if product_data:
                        yield product_data
                
        except Exception as e:
            self.logger.error(f"Error searching Amazon products: {e}")
    
    def _extract_search_result(self, container) -> Optional[Dict]:
        """Extract product data from search result container."""
        try:
            # Product URL
            link_element = container.find('a', class_='a-link-normal')
            if not link_element:
                return None
            
            product_url = urljoin(self.base_url, link_element.get('href', ''))
            
            # Product name
            title_element = container.find('span', class_='a-size-medium') or \
                           container.find('span', class_='a-size-base-plus')
            if not title_element:
                return None
            
            name = self.extract_text_safe(title_element)
            
            # Price
            price_element = container.find('span', class_='a-price-whole') or \
                           container.find('span', class_='a-offscreen')
            price = self.clean_price(self.extract_text_safe(price_element)) if price_element else None
            
            # Rating
            rating_element = container.find('span', class_='a-icon-alt')
            rating_text = self.extract_text_safe(rating_element)
            rating = None
            if rating_text:
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Image
            img_element = container.find('img', class_='s-image')
            image_url = self.extract_attribute_safe(img_element, 'src')
            
            return {
                'url': product_url,
                'name': name,
                'price': price,
                'rating': rating,
                'image': image_url,
                'site': 'amazon'
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting search result: {e}")
            return None
    
    def scrape_product_details(self, product_url: str) -> Optional[ProductModel]:
        """Scrape detailed product information from Amazon."""
        try:
            response = self.make_request(product_url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Product name
            name_element = soup.find('span', {'id': 'productTitle'})
            if not name_element:
                return None
            name = self.extract_text_safe(name_element)
            
            # Product ID from URL
            product_id = self.generate_product_id(product_url, name)
            
            # Brand
            brand_element = soup.find('a', {'id': 'bylineInfo'}) or \
                           soup.find('span', class_='a-size-base')
            brand = self.extract_text_safe(brand_element).replace('Visit the ', '').replace(' Store', '')
            
            # Category - try to determine from breadcrumbs
            category = ProductCategory.ELECTRONICS  # Default
            breadcrumb = soup.find('div', {'id': 'wayfinding-breadcrumbs_feature_div'})
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
            
            # Description
            description_element = soup.find('div', {'id': 'feature-bullets'}) or \
                                 soup.find('div', {'id': 'productDescription'})
            description = self.extract_text_safe(description_element)
            
            # Specifications
            specifications = {}
            spec_table = soup.find('table', {'id': 'productDetails_techSpec_section_1'})
            if spec_table:
                rows = spec_table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) == 2:
                        key = self.extract_text_safe(cols[0])
                        value = self.extract_text_safe(cols[1])
                        if key and value:
                            specifications[key] = value
            
            # Images
            images = []
            image_elements = soup.find_all('img', class_='a-dynamic-image')
            for img in image_elements[:5]:  # Limit to 5 images
                img_url = self.extract_attribute_safe(img, 'src')
                if img_url and img_url not in images:
                    images.append(img_url)
            
            # Stock status
            in_stock = True
            stock_element = soup.find('div', {'id': 'availability'})
            if stock_element:
                stock_text = self.extract_text_safe(stock_element).lower()
                if 'out of stock' in stock_text or 'unavailable' in stock_text:
                    in_stock = False
            
            return ProductModel(
                product_id=product_id,
                site=SiteEnum.AMAZON,
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
            self.logger.error(f"Error scraping Amazon product details: {e}")
            return None
    
    def scrape_product_reviews(self, product_url: str, max_reviews: int = 100) -> List[ReviewModel]:
        """Scrape product reviews from Amazon."""
        reviews = []
        try:
            # Extract ASIN from product URL
            asin_match = re.search(r'/dp/([A-Z0-9]{10})', product_url)
            if not asin_match:
                return reviews
            
            asin = asin_match.group(1)
            
            # Build reviews URL
            reviews_url = f"{self.base_url}/product-reviews/{asin}/ref=cm_cr_dp_d_show_all_btm"
            
            page = 1
            scraped_count = 0
            
            while scraped_count < max_reviews and page <= 10:  # Limit to 10 pages
                params = {'pageNumber': page}
                response = self.make_request(reviews_url, params=params)
                if not response:
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find review containers
                review_containers = soup.find_all('div', {'data-hook': 'review'})
                
                if not review_containers:
                    break
                
                for container in review_containers:
                    if scraped_count >= max_reviews:
                        break
                    
                    review = self._extract_review(container, asin)
                    if review:
                        reviews.append(review)
                        scraped_count += 1
                
                page += 1
            
        except Exception as e:
            self.logger.error(f"Error scraping Amazon reviews: {e}")
        
        return reviews
    
    def _extract_review(self, container, product_id: str) -> Optional[ReviewModel]:
        """Extract review data from review container."""
        try:
            # Review title
            title_element = container.find('a', {'data-hook': 'review-title'})
            title = self.extract_text_safe(title_element)
            
            # Review content
            content_element = container.find('span', {'data-hook': 'review-body'})
            content = self.extract_text_safe(content_element)
            if not content:
                return None
            
            # Rating
            rating_element = container.find('i', {'data-hook': 'review-star-rating'})
            rating_text = self.extract_attribute_safe(rating_element, 'class')
            rating = 5.0  # Default
            if rating_text:
                rating_match = re.search(r'a-star-(\d)', ' '.join(rating_text))
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Reviewer name
            reviewer_element = container.find('span', class_='a-profile-name')
            reviewer_name = self.extract_text_safe(reviewer_element)
            
            # Verified purchase
            verified_element = container.find('span', {'data-hook': 'avp-badge'})
            verified_purchase = verified_element is not None
            
            # Review date
            date_element = container.find('span', {'data-hook': 'review-date'})
            review_date = None
            if date_element:
                date_text = self.extract_text_safe(date_element)
                try:
                    # Parse date from text like "Reviewed in India on 5 January 2024"
                    date_match = re.search(r'on (\d{1,2} \w+ \d{4})', date_text)
                    if date_match:
                        review_date = datetime.strptime(date_match.group(1), '%d %B %Y')
                except Exception:
                    pass
            
            review_id = self.generate_review_id(product_id, content, reviewer_name)
            
            return ReviewModel(
                review_id=review_id,
                product_id=product_id,
                site=SiteEnum.AMAZON,
                title=title,
                content=content,
                rating=rating,
                reviewer_name=reviewer_name,
                verified_purchase=verified_purchase,
                review_date=review_date
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting Amazon review: {e}")
            return None
    
    def scrape_product_pricing(self, product_url: str) -> Optional[PricingModel]:
        """Scrape current pricing information from Amazon."""
        try:
            response = self.make_request(product_url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Product ID
            name_element = soup.find('span', {'id': 'productTitle'})
            name = self.extract_text_safe(name_element)
            product_id = self.generate_product_id(product_url, name)
            
            # Current price
            current_price = None
            price_elements = [
                soup.find('span', class_='a-price-whole'),
                soup.find('span', class_='a-offscreen'),
                soup.find('span', {'id': 'priceblock_dealprice'}),
                soup.find('span', {'id': 'priceblock_ourprice'})
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
            mrp_element = soup.find('span', class_='a-text-strike') or \
                         soup.find('span', {'id': 'listPrice'})
            if mrp_element:
                original_price = self.clean_price(self.extract_text_safe(mrp_element))
            
            # Discount calculation
            discount_percentage = None
            discount_amount = None
            if original_price and original_price > current_price:
                discount_amount = original_price - current_price
                discount_percentage = (discount_amount / original_price) * 100
            
            # Offers
            offers = []
            offer_elements = soup.find_all('span', class_='a-size-base')
            for element in offer_elements:
                text = self.extract_text_safe(element)
                if any(keyword in text.lower() for keyword in ['offer', 'discount', 'save', 'deal']):
                    offers.append(text)
            
            price_id = self.generate_price_id(product_id)
            
            return PricingModel(
                price_id=price_id,
                product_id=product_id,
                site=SiteEnum.AMAZON,
                current_price=current_price,
                original_price=original_price,
                discount_percentage=discount_percentage,
                discount_amount=discount_amount,
                offers=offers[:3]  # Limit to 3 offers
            )
            
        except Exception as e:
            self.logger.error(f"Error scraping Amazon pricing: {e}")
            return None