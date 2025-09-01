"""
Basic tests for the web scraping system.
"""
import pytest
import tempfile
import os
from datetime import datetime

from src.config.settings import settings
from src.data.models import ProductModel, ReviewModel, PricingModel, SiteEnum, ProductCategory
from src.data.validation import DataValidator, DeduplicationManager
from src.scrapers.base_scraper import RateLimiter, RobotsChecker
from src.monitoring.metrics import MetricsCollector


class TestModels:
    """Test data models."""
    
    def test_product_model_validation(self):
        """Test product model validation."""
        product = ProductModel(
            product_id="test_123",
            site=SiteEnum.AMAZON,
            name="Test Product",
            category=ProductCategory.ELECTRONICS,
            url="https://amazon.in/test"
        )
        
        assert product.product_id == "test_123"
        assert product.site == SiteEnum.AMAZON
        assert product.name == "Test Product"
    
    def test_review_model_validation(self):
        """Test review model validation."""
        review = ReviewModel(
            review_id="review_123",
            product_id="product_123",
            site=SiteEnum.AMAZON,
            content="Great product!",
            rating=4.5
        )
        
        assert review.review_id == "review_123"
        assert review.rating == 4.5
        assert review.content == "Great product!"
    
    def test_pricing_model_validation(self):
        """Test pricing model validation."""
        pricing = PricingModel(
            price_id="price_123",
            product_id="product_123",
            site=SiteEnum.AMAZON,
            current_price=1000.0
        )
        
        assert pricing.current_price == 1000.0
        assert pricing.currency == "INR"


class TestValidation:
    """Test data validation."""
    
    def test_data_validator(self):
        """Test data validator functionality."""
        validator = DataValidator()
        
        # Create a test product
        product = ProductModel(
            product_id="test_123",
            site=SiteEnum.AMAZON,
            name="Test Product",
            category=ProductCategory.ELECTRONICS,
            url="https://amazon.in/test",
            brand="TestBrand",
            description="A test product description"
        )
        
        # Validate the product
        quality_score = validator.validate_product(product)
        
        assert quality_score.overall_score > 0
        assert quality_score.record_type == "product"
    
    def test_deduplication_manager(self):
        """Test deduplication functionality."""
        dedup_manager = DeduplicationManager()
        
        product1 = ProductModel(
            product_id="test_123",
            site=SiteEnum.AMAZON,
            name="Test Product",
            category=ProductCategory.ELECTRONICS,
            url="https://amazon.in/test"
        )
        
        product2 = ProductModel(
            product_id="test_456",
            site=SiteEnum.AMAZON,
            name="Test Product",  # Same name
            category=ProductCategory.ELECTRONICS,
            url="https://amazon.in/test"  # Same URL
        )
        
        # First product should not be duplicate
        assert not dedup_manager.is_duplicate_product(product1)
        
        # Second product should be duplicate
        assert dedup_manager.is_duplicate_product(product2)


class TestScrapers:
    """Test scraper functionality."""
    
    def test_rate_limiter(self):
        """Test rate limiting functionality."""
        rate_limiter = RateLimiter(max_requests_per_second=2.0)
        
        # Test that rate limiter tracks domains
        start_time = datetime.utcnow()
        rate_limiter.wait_if_needed("example.com")
        rate_limiter.wait_if_needed("example.com")
        end_time = datetime.utcnow()
        
        # Should have added delay
        duration = (end_time - start_time).total_seconds()
        assert duration >= 0.5  # At least 0.5 seconds delay
    
    def test_robots_checker(self):
        """Test robots.txt checker."""
        robots_checker = RobotsChecker()
        
        # Test with a common URL (should return True for most cases)
        can_fetch = robots_checker.can_fetch("https://example.com/page")
        assert isinstance(can_fetch, bool)


class TestMonitoring:
    """Test monitoring functionality."""
    
    def test_metrics_collector(self):
        """Test metrics collection."""
        metrics = MetricsCollector()
        
        # Test counter
        metrics.increment_counter("test_counter", 5)
        assert metrics.get_counter_value("test_counter") == 5
        
        # Test gauge
        metrics.set_gauge("test_gauge", 42.5)
        assert metrics.get_gauge_value("test_gauge") == 42.5
        
        # Test timer
        metrics.record_timer("test_timer", 1.23)
        stats = metrics.get_timer_stats("test_timer")
        assert stats["count"] == 1
        assert stats["avg"] == 1.23


class TestConfiguration:
    """Test configuration."""
    
    def test_settings_loaded(self):
        """Test that settings are loaded correctly."""
        assert settings.MAX_REQUESTS_PER_SECOND == 0.5
        assert settings.BATCH_SIZE == 100
        assert len(settings.SITES) == 3
        assert len(settings.CATEGORIES) > 0
    
    def test_site_configuration(self):
        """Test site-specific configuration."""
        amazon_config = settings.SITES.get("amazon")
        assert amazon_config is not None
        assert "base_url" in amazon_config
        assert "robots_url" in amazon_config


if __name__ == "__main__":
    # Simple test runner without pytest
    import sys
    
    print("Running basic tests...")
    
    try:
        # Test models
        test_models = TestModels()
        test_models.test_product_model_validation()
        test_models.test_review_model_validation()
        test_models.test_pricing_model_validation()
        print("✓ Model tests passed")
        
        # Test validation
        test_validation = TestValidation()
        test_validation.test_data_validator()
        test_validation.test_deduplication_manager()
        print("✓ Validation tests passed")
        
        # Test scrapers
        test_scrapers = TestScrapers()
        test_scrapers.test_rate_limiter()
        test_scrapers.test_robots_checker()
        print("✓ Scraper tests passed")
        
        # Test monitoring
        test_monitoring = TestMonitoring()
        test_monitoring.test_metrics_collector()
        print("✓ Monitoring tests passed")
        
        # Test configuration
        test_config = TestConfiguration()
        test_config.test_settings_loaded()
        test_config.test_site_configuration()
        print("✓ Configuration tests passed")
        
        print("\nAll tests passed! ✓")
        
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)