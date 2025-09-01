"""
Data models for e-commerce scraping system.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class SiteEnum(str, Enum):
    """Supported e-commerce sites."""
    AMAZON = "amazon"
    FLIPKART = "flipkart"
    MYNTRA = "myntra"


class ProductCategory(str, Enum):
    """Product categories."""
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    HOME_KITCHEN = "home-kitchen"
    BOOKS = "books"
    SPORTS = "sports"


class ProductModel(BaseModel):
    """Product data model."""
    product_id: str = Field(..., description="Unique product identifier")
    site: SiteEnum = Field(..., description="Source e-commerce site")
    name: str = Field(..., description="Product name")
    category: ProductCategory = Field(..., description="Product category")
    brand: Optional[str] = Field(None, description="Product brand")
    url: str = Field(..., description="Product URL")
    
    # Product details
    description: Optional[str] = Field(None, description="Product description")
    specifications: Dict[str, Any] = Field(default_factory=dict, description="Technical specifications")
    images: List[str] = Field(default_factory=list, description="Product image URLs")
    
    # Availability
    in_stock: bool = Field(True, description="Product availability")
    stock_quantity: Optional[int] = Field(None, description="Available quantity")
    
    # Metadata
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('product_id')
    def validate_product_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Product ID cannot be empty')
        return v.strip()
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Product name cannot be empty')
        return v.strip()


class ReviewModel(BaseModel):
    """Review data model."""
    review_id: str = Field(..., description="Unique review identifier")
    product_id: str = Field(..., description="Associated product ID")
    site: SiteEnum = Field(..., description="Source e-commerce site")
    
    # Review content
    title: Optional[str] = Field(None, description="Review title")
    content: str = Field(..., description="Review content")
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating (1-5 stars)")
    
    # Reviewer info (anonymized)
    reviewer_name: Optional[str] = Field(None, description="Anonymized reviewer name")
    verified_purchase: bool = Field(False, description="Whether purchase is verified")
    
    # Metadata
    review_date: Optional[datetime] = Field(None, description="Original review date")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('content')
    def validate_content(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Review content cannot be empty')
        return v.strip()
    
    @validator('reviewer_name')
    def anonymize_reviewer(cls, v):
        """Anonymize reviewer name for privacy."""
        if v and len(v) > 2:
            return v[0] + "*" * (len(v) - 2) + v[-1]
        return v


class PricingModel(BaseModel):
    """Pricing data model."""
    price_id: str = Field(..., description="Unique pricing record identifier")
    product_id: str = Field(..., description="Associated product ID")
    site: SiteEnum = Field(..., description="Source e-commerce site")
    
    # Pricing information
    current_price: float = Field(..., ge=0, description="Current price")
    original_price: Optional[float] = Field(None, ge=0, description="Original/MRP price")
    currency: str = Field(default="INR", description="Currency code")
    
    # Discount information
    discount_percentage: Optional[float] = Field(None, ge=0, le=100, description="Discount percentage")
    discount_amount: Optional[float] = Field(None, ge=0, description="Absolute discount amount")
    
    # Offers and deals
    offers: List[str] = Field(default_factory=list, description="Available offers")
    deal_type: Optional[str] = Field(None, description="Type of deal")
    
    # Timestamp
    price_date: datetime = Field(default_factory=datetime.utcnow)
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('original_price')
    def validate_price_relationship(cls, v, values):
        """Ensure original price is >= current price."""
        if v is not None and 'current_price' in values:
            if v < values['current_price']:
                raise ValueError('Original price cannot be less than current price')
        return v


class ScrapingJobModel(BaseModel):
    """Scraping job tracking model."""
    job_id: str = Field(..., description="Unique job identifier")
    site: SiteEnum = Field(..., description="Target site")
    job_type: str = Field(..., description="Type of scraping job")
    
    # Job configuration
    category: Optional[ProductCategory] = Field(None, description="Target category")
    search_terms: List[str] = Field(default_factory=list, description="Search terms")
    max_pages: int = Field(default=10, description="Maximum pages to scrape")
    
    # Job status
    status: str = Field(default="pending", description="Job status")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    
    # Results
    products_scraped: int = Field(default=0, description="Number of products scraped")
    reviews_scraped: int = Field(default=0, description="Number of reviews scraped")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QualityScoreModel(BaseModel):
    """Data quality scoring model."""
    record_id: str = Field(..., description="Record identifier")
    record_type: str = Field(..., description="Type of record (product/review/pricing)")
    
    # Quality metrics
    completeness_score: float = Field(..., ge=0, le=1, description="Data completeness (0-1)")
    accuracy_score: float = Field(..., ge=0, le=1, description="Data accuracy (0-1)")
    consistency_score: float = Field(..., ge=0, le=1, description="Data consistency (0-1)")
    
    # Overall score
    overall_score: float = Field(..., ge=0, le=1, description="Overall quality score")
    
    # Issues identified
    issues: List[str] = Field(default_factory=list, description="Quality issues")
    
    # Metadata
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('overall_score')
    def calculate_overall_score(cls, v, values):
        """Calculate overall score from component scores."""
        if all(key in values for key in ['completeness_score', 'accuracy_score', 'consistency_score']):
            return (values['completeness_score'] + values['accuracy_score'] + values['consistency_score']) / 3
        return v