"""
Data processor for handling scraped data pipeline.
"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ..config.settings import settings
from ..config.logging_config import loggers
from ..data.models import ProductModel, ReviewModel, PricingModel
from ..data.validation import DataValidator, DeduplicationManager
from ..data.storage import LocalDatabaseManager, CloudStorageManager, BigQueryManager


class DataProcessor:
    """Processes scraped data through validation, deduplication, and storage."""
    
    def __init__(self):
        self.logger = loggers["pipeline"]
        self.validator = DataValidator()
        self.dedup_manager = DeduplicationManager()
        self.local_db = LocalDatabaseManager()
        self.cloud_storage = CloudStorageManager()
        self.bigquery = BigQueryManager()
        
        # Processing statistics
        self.stats = {
            "products_processed": 0,
            "reviews_processed": 0,
            "pricing_processed": 0,
            "duplicates_filtered": 0,
            "validation_failures": 0,
            "last_processed": None
        }
    
    def process_products(self, products: List[ProductModel]) -> Dict[str, int]:
        """Process product data through the full pipeline."""
        if not products:
            return {"processed": 0, "duplicates": 0, "failures": 0}
        
        self.logger.info(f"Processing {len(products)} products")
        
        processed = 0
        duplicates = 0
        failures = 0
        valid_products = []
        
        for product in products:
            try:
                # Check for duplicates
                if self.dedup_manager.is_duplicate_product(product):
                    duplicates += 1
                    continue
                
                # Validate data quality
                quality_score = self.validator.validate_product(product)
                
                # Only process high-quality data
                if quality_score.overall_score >= settings.MIN_DATA_COMPLETENESS * 0.8:
                    valid_products.append(product)
                    
                    # Save quality score
                    self.local_db.save_quality_score(quality_score)
                    processed += 1
                else:
                    failures += 1
                    self.logger.warning(
                        f"Product {product.product_id} failed quality check: "
                        f"score={quality_score.overall_score:.2f}"
                    )
                
            except Exception as e:
                failures += 1
                self.logger.error(f"Failed to process product {product.product_id}: {e}")
        
        # Batch save to staging
        if valid_products:
            self.local_db.save_products(valid_products)
            
            # Upload raw data to cloud storage
            self._upload_raw_data(valid_products, "products")
        
        # Update statistics
        self.stats["products_processed"] += processed
        self.stats["duplicates_filtered"] += duplicates
        self.stats["validation_failures"] += failures
        self.stats["last_processed"] = datetime.utcnow()
        
        self.logger.info(
            f"Product processing complete: {processed} processed, "
            f"{duplicates} duplicates, {failures} failures"
        )
        
        return {"processed": processed, "duplicates": duplicates, "failures": failures}
    
    def process_reviews(self, reviews: List[ReviewModel]) -> Dict[str, int]:
        """Process review data through the full pipeline."""
        if not reviews:
            return {"processed": 0, "duplicates": 0, "failures": 0}
        
        self.logger.info(f"Processing {len(reviews)} reviews")
        
        processed = 0
        duplicates = 0
        failures = 0
        valid_reviews = []
        
        for review in reviews:
            try:
                # Check for duplicates
                if self.dedup_manager.is_duplicate_review(review):
                    duplicates += 1
                    continue
                
                # Validate data quality
                quality_score = self.validator.validate_review(review)
                
                # Only process high-quality data
                if quality_score.overall_score >= settings.MIN_DATA_COMPLETENESS * 0.7:
                    valid_reviews.append(review)
                    
                    # Save quality score
                    self.local_db.save_quality_score(quality_score)
                    processed += 1
                else:
                    failures += 1
                    self.logger.warning(
                        f"Review {review.review_id} failed quality check: "
                        f"score={quality_score.overall_score:.2f}"
                    )
                
            except Exception as e:
                failures += 1
                self.logger.error(f"Failed to process review {review.review_id}: {e}")
        
        # Batch save to staging
        if valid_reviews:
            self.local_db.save_reviews(valid_reviews)
            
            # Upload raw data to cloud storage
            self._upload_raw_data(valid_reviews, "reviews")
        
        # Update statistics
        self.stats["reviews_processed"] += processed
        self.stats["duplicates_filtered"] += duplicates
        self.stats["validation_failures"] += failures
        self.stats["last_processed"] = datetime.utcnow()
        
        self.logger.info(
            f"Review processing complete: {processed} processed, "
            f"{duplicates} duplicates, {failures} failures"
        )
        
        return {"processed": processed, "duplicates": duplicates, "failures": failures}
    
    def process_pricing(self, pricing_data: List[PricingModel]) -> Dict[str, int]:
        """Process pricing data through the full pipeline."""
        if not pricing_data:
            return {"processed": 0, "duplicates": 0, "failures": 0}
        
        self.logger.info(f"Processing {len(pricing_data)} pricing records")
        
        processed = 0
        duplicates = 0
        failures = 0
        valid_pricing = []
        
        for pricing in pricing_data:
            try:
                # Check for duplicates
                if self.dedup_manager.is_duplicate_pricing(pricing):
                    duplicates += 1
                    continue
                
                # Validate data quality
                quality_score = self.validator.validate_pricing(pricing)
                
                # Only process high-quality data
                if quality_score.overall_score >= settings.MIN_DATA_COMPLETENESS * 0.8:
                    valid_pricing.append(pricing)
                    
                    # Save quality score
                    self.local_db.save_quality_score(quality_score)
                    processed += 1
                else:
                    failures += 1
                    self.logger.warning(
                        f"Pricing {pricing.price_id} failed quality check: "
                        f"score={quality_score.overall_score:.2f}"
                    )
                
            except Exception as e:
                failures += 1
                self.logger.error(f"Failed to process pricing {pricing.price_id}: {e}")
        
        # Batch save to staging
        if valid_pricing:
            self.local_db.save_pricing(valid_pricing)
            
            # Upload raw data to cloud storage
            self._upload_raw_data(valid_pricing, "pricing")
        
        # Update statistics
        self.stats["pricing_processed"] += processed
        self.stats["duplicates_filtered"] += duplicates
        self.stats["validation_failures"] += failures
        self.stats["last_processed"] = datetime.utcnow()
        
        self.logger.info(
            f"Pricing processing complete: {processed} processed, "
            f"{duplicates} duplicates, {failures} failures"
        )
        
        return {"processed": processed, "duplicates": duplicates, "failures": failures}
    
    def process_all_pending(self) -> Dict[str, int]:
        """Process all pending data in staging tables."""
        self.logger.info("Processing all pending data")
        
        total_processed = 0
        
        # Process products
        products_data = self.local_db.get_unprocessed_data("products_staging", 1000)
        if products_data:
            processed_ids = self._load_to_bigquery(products_data, "products")
            if processed_ids:
                self.local_db.mark_as_processed("products_staging", processed_ids)
                total_processed += len(processed_ids)
        
        # Process reviews
        reviews_data = self.local_db.get_unprocessed_data("reviews_staging", 1000)
        if reviews_data:
            processed_ids = self._load_to_bigquery(reviews_data, "reviews")
            if processed_ids:
                self.local_db.mark_as_processed("reviews_staging", processed_ids)
                total_processed += len(processed_ids)
        
        # Process pricing
        pricing_data = self.local_db.get_unprocessed_data("pricing_staging", 1000)
        if pricing_data:
            processed_ids = self._load_to_bigquery(pricing_data, "pricing")
            if processed_ids:
                self.local_db.mark_as_processed("pricing_staging", processed_ids)
                total_processed += len(processed_ids)
        
        self.logger.info(f"Processed {total_processed} records to BigQuery")
        
        return {"total_processed": total_processed}
    
    def _upload_raw_data(self, data: List[Any], data_type: str):
        """Upload raw data to cloud storage."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_path = f"raw_data/{data_type}/{timestamp}.json"
            
            # Convert to serializable format
            serializable_data = []
            for item in data:
                if hasattr(item, 'dict'):
                    serializable_data.append(item.dict())
                else:
                    serializable_data.append(item)
            
            self.cloud_storage.upload_raw_data(serializable_data, file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to upload raw data: {e}")
    
    def _load_to_bigquery(self, data: List[Dict], table_name: str) -> List[str]:
        """Load data to BigQuery and return processed record IDs."""
        try:
            if not data:
                return []
            
            # Clean and prepare data for BigQuery
            cleaned_data = []
            processed_ids = []
            
            for record in data:
                try:
                    cleaned_record = self._clean_record_for_bigquery(record, table_name)
                    if cleaned_record:
                        cleaned_data.append(cleaned_record)
                        
                        # Get the primary key
                        if table_name == "products":
                            processed_ids.append(record["product_id"])
                        elif table_name == "reviews":
                            processed_ids.append(record["review_id"])
                        elif table_name == "pricing":
                            processed_ids.append(record["price_id"])
                
                except Exception as e:
                    self.logger.error(f"Failed to clean record for BigQuery: {e}")
            
            # Load to BigQuery
            if cleaned_data and self.bigquery.load_data(table_name, cleaned_data):
                return processed_ids
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to load data to BigQuery: {e}")
            return []
    
    def _clean_record_for_bigquery(self, record: Dict, table_name: str) -> Optional[Dict]:
        """Clean record for BigQuery compatibility."""
        try:
            cleaned = record.copy()
            
            # Parse JSON fields
            json_fields = {
                "products": ["specifications", "images"],
                "reviews": [],
                "pricing": ["offers"]
            }
            
            for field in json_fields.get(table_name, []):
                if field in cleaned and isinstance(cleaned[field], str):
                    try:
                        cleaned[field] = json.loads(cleaned[field])
                    except json.JSONDecodeError:
                        cleaned[field] = []
            
            # Convert timestamps
            timestamp_fields = ["scraped_at", "last_updated", "review_date", "price_date"]
            for field in timestamp_fields:
                if field in cleaned and cleaned[field]:
                    if isinstance(cleaned[field], str):
                        try:
                            cleaned[field] = datetime.fromisoformat(cleaned[field].replace('Z', '+00:00'))
                        except:
                            cleaned[field] = None
            
            # Remove processed flag
            cleaned.pop("processed", None)
            
            return cleaned
            
        except Exception as e:
            self.logger.error(f"Failed to clean record: {e}")
            return None
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset processing statistics."""
        self.stats = {
            "products_processed": 0,
            "reviews_processed": 0,
            "pricing_processed": 0,
            "duplicates_filtered": 0,
            "validation_failures": 0,
            "last_processed": None
        }
        
        # Clear deduplication cache
        self.dedup_manager.clear_cache()
        
        self.logger.info("Processing statistics reset")
    
    def cleanup_old_data(self, days_old: int = 30):
        """Clean up old processed data from staging tables."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # This would implement cleanup logic for old data
            # For now, just log the intent
            self.logger.info(f"Would clean up data older than {cutoff_date}")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")