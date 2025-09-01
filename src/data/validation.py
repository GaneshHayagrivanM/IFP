"""
Data validation framework for quality assurance.
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..data.models import ProductModel, ReviewModel, PricingModel, QualityScoreModel
from ..config.logging_config import loggers


class DataValidator:
    """Data validation and quality scoring framework."""
    
    def __init__(self):
        self.logger = loggers["quality"]
        
        # Validation rules
        self.required_product_fields = ['product_id', 'name', 'site', 'category', 'url']
        self.required_review_fields = ['review_id', 'product_id', 'site', 'content', 'rating']
        self.required_pricing_fields = ['price_id', 'product_id', 'site', 'current_price']
        
        # Quality thresholds
        self.min_name_length = 3
        self.max_name_length = 500
        self.min_content_length = 10
        self.max_content_length = 5000
        self.min_price = 0.01
        self.max_price = 1000000
    
    def validate_product(self, product: ProductModel) -> QualityScoreModel:
        """Validate product data and generate quality score."""
        issues = []
        
        # Completeness check
        completeness_score = self._check_product_completeness(product, issues)
        
        # Accuracy check
        accuracy_score = self._check_product_accuracy(product, issues)
        
        # Consistency check
        consistency_score = self._check_product_consistency(product, issues)
        
        # Calculate overall score
        overall_score = (completeness_score + accuracy_score + consistency_score) / 3
        
        return QualityScoreModel(
            record_id=product.product_id,
            record_type="product",
            completeness_score=completeness_score,
            accuracy_score=accuracy_score,
            consistency_score=consistency_score,
            overall_score=overall_score,
            issues=issues
        )
    
    def validate_review(self, review: ReviewModel) -> QualityScoreModel:
        """Validate review data and generate quality score."""
        issues = []
        
        # Completeness check
        completeness_score = self._check_review_completeness(review, issues)
        
        # Accuracy check
        accuracy_score = self._check_review_accuracy(review, issues)
        
        # Consistency check
        consistency_score = self._check_review_consistency(review, issues)
        
        # Calculate overall score
        overall_score = (completeness_score + accuracy_score + consistency_score) / 3
        
        return QualityScoreModel(
            record_id=review.review_id,
            record_type="review",
            completeness_score=completeness_score,
            accuracy_score=accuracy_score,
            consistency_score=consistency_score,
            overall_score=overall_score,
            issues=issues
        )
    
    def validate_pricing(self, pricing: PricingModel) -> QualityScoreModel:
        """Validate pricing data and generate quality score."""
        issues = []
        
        # Completeness check
        completeness_score = self._check_pricing_completeness(pricing, issues)
        
        # Accuracy check
        accuracy_score = self._check_pricing_accuracy(pricing, issues)
        
        # Consistency check
        consistency_score = self._check_pricing_consistency(pricing, issues)
        
        # Calculate overall score
        overall_score = (completeness_score + accuracy_score + consistency_score) / 3
        
        return QualityScoreModel(
            record_id=pricing.price_id,
            record_type="pricing",
            completeness_score=completeness_score,
            accuracy_score=accuracy_score,
            consistency_score=consistency_score,
            overall_score=overall_score,
            issues=issues
        )
    
    def _check_product_completeness(self, product: ProductModel, issues: List[str]) -> float:
        """Check product data completeness."""
        total_fields = len(self.required_product_fields) + 4  # Additional optional fields
        present_fields = 0
        
        # Check required fields
        for field in self.required_product_fields:
            if hasattr(product, field) and getattr(product, field):
                present_fields += 1
            else:
                issues.append(f"Missing required field: {field}")
        
        # Check optional but important fields
        optional_fields = ['brand', 'description', 'images', 'specifications']
        for field in optional_fields:
            if hasattr(product, field):
                value = getattr(product, field)
                if value:
                    if isinstance(value, list) and len(value) > 0:
                        present_fields += 1
                    elif isinstance(value, dict) and len(value) > 0:
                        present_fields += 1
                    elif isinstance(value, str) and len(value.strip()) > 0:
                        present_fields += 1
        
        return present_fields / total_fields
    
    def _check_product_accuracy(self, product: ProductModel, issues: List[str]) -> float:
        """Check product data accuracy."""
        accuracy_points = 0
        total_checks = 5
        
        # Name validation
        if self.min_name_length <= len(product.name) <= self.max_name_length:
            accuracy_points += 1
        else:
            issues.append(f"Invalid name length: {len(product.name)}")
        
        # URL validation
        if self._is_valid_url(product.url):
            accuracy_points += 1
        else:
            issues.append("Invalid URL format")
        
        # Brand validation (if present)
        if product.brand and len(product.brand.strip()) > 0:
            accuracy_points += 1
        elif not product.brand:
            accuracy_points += 0.5  # Partial credit if missing
        
        # Description validation (if present)
        if product.description and len(product.description.strip()) >= 10:
            accuracy_points += 1
        elif not product.description:
            accuracy_points += 0.5  # Partial credit if missing
        
        # Images validation (if present)
        if product.images and len(product.images) > 0:
            valid_images = sum(1 for img in product.images if self._is_valid_url(img))
            if valid_images == len(product.images):
                accuracy_points += 1
            else:
                accuracy_points += valid_images / len(product.images)
                issues.append(f"Invalid image URLs: {len(product.images) - valid_images}")
        else:
            accuracy_points += 0.5  # Partial credit if missing
        
        return accuracy_points / total_checks
    
    def _check_product_consistency(self, product: ProductModel, issues: List[str]) -> float:
        """Check product data consistency."""
        consistency_points = 0
        total_checks = 3
        
        # Check if URL matches site
        site_domains = {
            'amazon': 'amazon.in',
            'flipkart': 'flipkart.com',
            'myntra': 'myntra.com'
        }
        
        expected_domain = site_domains.get(product.site.value)
        if expected_domain and expected_domain in product.url:
            consistency_points += 1
        else:
            issues.append(f"URL domain doesn't match site: {product.site.value}")
        
        # Check product name and brand consistency
        if product.brand and product.brand.lower() in product.name.lower():
            consistency_points += 1
        elif not product.brand:
            consistency_points += 0.5  # Partial credit if brand missing
        else:
            issues.append("Brand not found in product name")
        
        # Check timestamp consistency
        if product.scraped_at <= datetime.utcnow():
            consistency_points += 1
        else:
            issues.append("Invalid scraped timestamp")
        
        return consistency_points / total_checks
    
    def _check_review_completeness(self, review: ReviewModel, issues: List[str]) -> float:
        """Check review data completeness."""
        total_fields = len(self.required_review_fields) + 3  # Additional optional fields
        present_fields = 0
        
        # Check required fields
        for field in self.required_review_fields:
            if hasattr(review, field) and getattr(review, field):
                present_fields += 1
            else:
                issues.append(f"Missing required field: {field}")
        
        # Check optional fields
        optional_fields = ['title', 'reviewer_name', 'review_date']
        for field in optional_fields:
            if hasattr(review, field) and getattr(review, field):
                present_fields += 1
        
        return present_fields / total_fields
    
    def _check_review_accuracy(self, review: ReviewModel, issues: List[str]) -> float:
        """Check review data accuracy."""
        accuracy_points = 0
        total_checks = 4
        
        # Content length validation
        if self.min_content_length <= len(review.content) <= self.max_content_length:
            accuracy_points += 1
        else:
            issues.append(f"Invalid content length: {len(review.content)}")
        
        # Rating validation
        if 1.0 <= review.rating <= 5.0:
            accuracy_points += 1
        else:
            issues.append(f"Invalid rating: {review.rating}")
        
        # Content quality check (basic spam detection)
        if self._is_meaningful_content(review.content):
            accuracy_points += 1
        else:
            issues.append("Low quality or spam content detected")
        
        # Reviewer name validation (if present)
        if review.reviewer_name and len(review.reviewer_name.strip()) > 0:
            accuracy_points += 1
        elif not review.reviewer_name:
            accuracy_points += 0.5  # Partial credit if missing
        
        return accuracy_points / total_checks
    
    def _check_review_consistency(self, review: ReviewModel, issues: List[str]) -> float:
        """Check review data consistency."""
        consistency_points = 0
        total_checks = 2
        
        # Check timestamp consistency
        if review.scraped_at <= datetime.utcnow():
            consistency_points += 1
        else:
            issues.append("Invalid scraped timestamp")
        
        # Check review date consistency (if present)
        if review.review_date:
            if review.review_date <= datetime.utcnow():
                consistency_points += 1
            else:
                issues.append("Invalid review date")
        else:
            consistency_points += 0.5  # Partial credit if missing
        
        return consistency_points / total_checks
    
    def _check_pricing_completeness(self, pricing: PricingModel, issues: List[str]) -> float:
        """Check pricing data completeness."""
        total_fields = len(self.required_pricing_fields) + 3  # Additional optional fields
        present_fields = 0
        
        # Check required fields
        for field in self.required_pricing_fields:
            if hasattr(pricing, field) and getattr(pricing, field) is not None:
                present_fields += 1
            else:
                issues.append(f"Missing required field: {field}")
        
        # Check optional fields
        optional_fields = ['original_price', 'discount_percentage', 'offers']
        for field in optional_fields:
            if hasattr(pricing, field):
                value = getattr(pricing, field)
                if value is not None:
                    if isinstance(value, list) and len(value) > 0:
                        present_fields += 1
                    elif not isinstance(value, list):
                        present_fields += 1
        
        return present_fields / total_fields
    
    def _check_pricing_accuracy(self, pricing: PricingModel, issues: List[str]) -> float:
        """Check pricing data accuracy."""
        accuracy_points = 0
        total_checks = 3
        
        # Current price validation
        if self.min_price <= pricing.current_price <= self.max_price:
            accuracy_points += 1
        else:
            issues.append(f"Invalid current price: {pricing.current_price}")
        
        # Original price validation (if present)
        if pricing.original_price is not None:
            if self.min_price <= pricing.original_price <= self.max_price:
                accuracy_points += 1
            else:
                issues.append(f"Invalid original price: {pricing.original_price}")
        else:
            accuracy_points += 0.5  # Partial credit if missing
        
        # Discount validation (if present)
        if pricing.discount_percentage is not None:
            if 0 <= pricing.discount_percentage <= 100:
                accuracy_points += 1
            else:
                issues.append(f"Invalid discount percentage: {pricing.discount_percentage}")
        else:
            accuracy_points += 0.5  # Partial credit if missing
        
        return accuracy_points / total_checks
    
    def _check_pricing_consistency(self, pricing: PricingModel, issues: List[str]) -> float:
        """Check pricing data consistency."""
        consistency_points = 0
        total_checks = 2
        
        # Check price relationship
        if pricing.original_price is not None:
            if pricing.original_price >= pricing.current_price:
                consistency_points += 1
            else:
                issues.append("Original price less than current price")
        else:
            consistency_points += 0.5  # Partial credit if missing
        
        # Check timestamp consistency
        if pricing.scraped_at <= datetime.utcnow():
            consistency_points += 1
        else:
            issues.append("Invalid scraped timestamp")
        
        return consistency_points / total_checks
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        if not url:
            return False
        
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return url_pattern.match(url) is not None
    
    def _is_meaningful_content(self, content: str) -> bool:
        """Basic check for meaningful content (spam detection)."""
        if not content or len(content.strip()) < 10:
            return False
        
        # Check for excessive repetition
        words = content.lower().split()
        if len(set(words)) < len(words) * 0.3:  # Less than 30% unique words
            return False
        
        # Check for suspicious patterns
        spam_patterns = [
            r'(.)\1{10,}',  # Repeated characters
            r'buy now|click here|visit|website',  # Common spam phrases
            r'\b\d{10,}\b'  # Long numbers (phone numbers)
        ]
        
        for pattern in spam_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False
        
        return True


class DeduplicationManager:
    """Handles data deduplication across products, reviews, and pricing."""
    
    def __init__(self):
        self.logger = loggers["quality"]
        self.seen_products = set()
        self.seen_reviews = set()
        self.seen_prices = set()
    
    def is_duplicate_product(self, product: ProductModel) -> bool:
        """Check if product is duplicate based on name and URL."""
        # Create a signature for the product
        signature = f"{product.site.value}:{product.name.lower().strip()}:{product.url}"
        
        if signature in self.seen_products:
            return True
        
        self.seen_products.add(signature)
        return False
    
    def is_duplicate_review(self, review: ReviewModel) -> bool:
        """Check if review is duplicate based on content and product."""
        # Create a signature for the review
        content_hash = hash(review.content.lower().strip())
        signature = f"{review.product_id}:{content_hash}"
        
        if signature in self.seen_reviews:
            return True
        
        self.seen_reviews.add(signature)
        return False
    
    def is_duplicate_pricing(self, pricing: PricingModel) -> bool:
        """Check if pricing is duplicate based on product and date."""
        # For pricing, we consider it duplicate if same product on same day
        price_date = pricing.price_date.date() if pricing.price_date else datetime.utcnow().date()
        signature = f"{pricing.product_id}:{price_date}"
        
        if signature in self.seen_prices:
            return True
        
        self.seen_prices.add(signature)
        return False
    
    def clear_cache(self):
        """Clear deduplication cache."""
        self.seen_products.clear()
        self.seen_reviews.clear()
        self.seen_prices.clear()