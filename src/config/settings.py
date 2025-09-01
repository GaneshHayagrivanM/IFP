"""
Configuration settings for the web scraping system.
"""
import os
from typing import Dict, List
from pydantic import BaseSettings, Field


class ScrapingSettings(BaseSettings):
    """Main configuration for the scraping system."""
    
    # Rate limiting
    MAX_REQUESTS_PER_SECOND: float = 0.5  # 1 request per 2 seconds
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5
    
    # Batch processing
    BATCH_SIZE: int = 100
    MAX_CONCURRENT_WORKERS: int = 2  # Limited for e2-micro VM
    
    # Storage
    STORAGE_BUCKET: str = Field(default="", env="GCP_STORAGE_BUCKET")
    BIGQUERY_PROJECT: str = Field(default="", env="GCP_PROJECT_ID")
    BIGQUERY_DATASET: str = Field(default="ecommerce_data", env="BIGQUERY_DATASET")
    LOCAL_DB_PATH: str = "data/local.db"
    
    # Data quality
    MIN_DATA_COMPLETENESS: float = 0.95
    MAX_DUPLICATE_RATE: float = 0.05
    
    # User agents for different sites
    USER_AGENTS: Dict[str, str] = {
        "amazon": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "flipkart": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "myntra": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Site-specific settings
    SITES: Dict[str, Dict] = {
        "amazon": {
            "base_url": "https://www.amazon.in",
            "robots_url": "https://www.amazon.in/robots.txt",
            "search_url": "https://www.amazon.in/s",
            "max_pages": 50
        },
        "flipkart": {
            "base_url": "https://www.flipkart.com",
            "robots_url": "https://www.flipkart.com/robots.txt",
            "search_url": "https://www.flipkart.com/search",
            "max_pages": 50
        },
        "myntra": {
            "base_url": "https://www.myntra.com",
            "robots_url": "https://www.myntra.com/robots.txt",
            "search_url": "https://www.myntra.com/shop",
            "max_pages": 50
        }
    }
    
    # Categories to scrape
    CATEGORIES: List[str] = [
        "electronics",
        "clothing",
        "home-kitchen",
        "books",
        "sports"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = ScrapingSettings()