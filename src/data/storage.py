"""
Storage management for raw data, local database, and BigQuery.
"""
import json
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from google.cloud import storage, bigquery
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ..config.settings import settings
from ..config.logging_config import loggers
from ..data.models import ProductModel, ReviewModel, PricingModel, ScrapingJobModel, QualityScoreModel


class CloudStorageManager:
    """Manages Cloud Storage operations for raw data."""
    
    def __init__(self):
        self.logger = loggers["data"]
        self.bucket_name = settings.STORAGE_BUCKET
        self.client = None
        self.bucket = None
        
        if self.bucket_name:
            try:
                self.client = storage.Client()
                self.bucket = self.client.bucket(self.bucket_name)
            except Exception as e:
                self.logger.warning(f"Could not initialize Cloud Storage: {e}")
    
    def upload_raw_data(self, data: Any, file_path: str) -> bool:
        """Upload raw scraped data to Cloud Storage."""
        if not self.client:
            self.logger.warning("Cloud Storage not available")
            return False
        
        try:
            blob = self.bucket.blob(file_path)
            
            if isinstance(data, dict) or isinstance(data, list):
                blob.upload_from_string(json.dumps(data, default=str), content_type='application/json')
            elif isinstance(data, pd.DataFrame):
                blob.upload_from_string(data.to_csv(index=False), content_type='text/csv')
            else:
                blob.upload_from_string(str(data), content_type='text/plain')
            
            self.logger.info(f"Uploaded data to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload data to {file_path}: {e}")
            return False
    
    def download_raw_data(self, file_path: str) -> Optional[str]:
        """Download raw data from Cloud Storage."""
        if not self.client:
            return None
        
        try:
            blob = self.bucket.blob(file_path)
            return blob.download_as_text()
        except Exception as e:
            self.logger.error(f"Failed to download data from {file_path}: {e}")
            return None
    
    def list_files(self, prefix: str = "") -> List[str]:
        """List files in Cloud Storage with optional prefix."""
        if not self.client:
            return []
        
        try:
            blobs = self.client.list_blobs(self.bucket, prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            self.logger.error(f"Failed to list files with prefix {prefix}: {e}")
            return []


class LocalDatabaseManager:
    """Manages local SQLite database for job tracking and staging."""
    
    def __init__(self):
        self.logger = loggers["data"]
        self.db_path = settings.LOCAL_DB_PATH
        
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Scraping jobs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS scraping_jobs (
                        job_id TEXT PRIMARY KEY,
                        site TEXT NOT NULL,
                        job_type TEXT NOT NULL,
                        category TEXT,
                        search_terms TEXT,
                        max_pages INTEGER,
                        status TEXT DEFAULT 'pending',
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        products_scraped INTEGER DEFAULT 0,
                        reviews_scraped INTEGER DEFAULT 0,
                        errors TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Products staging table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS products_staging (
                        product_id TEXT PRIMARY KEY,
                        site TEXT NOT NULL,
                        name TEXT NOT NULL,
                        category TEXT,
                        brand TEXT,
                        url TEXT NOT NULL,
                        description TEXT,
                        specifications TEXT,
                        images TEXT,
                        in_stock BOOLEAN,
                        scraped_at TIMESTAMP,
                        processed BOOLEAN DEFAULT FALSE
                    )
                """)
                
                # Reviews staging table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reviews_staging (
                        review_id TEXT PRIMARY KEY,
                        product_id TEXT NOT NULL,
                        site TEXT NOT NULL,
                        title TEXT,
                        content TEXT NOT NULL,
                        rating REAL NOT NULL,
                        reviewer_name TEXT,
                        verified_purchase BOOLEAN,
                        review_date TIMESTAMP,
                        scraped_at TIMESTAMP,
                        processed BOOLEAN DEFAULT FALSE
                    )
                """)
                
                # Pricing staging table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pricing_staging (
                        price_id TEXT PRIMARY KEY,
                        product_id TEXT NOT NULL,
                        site TEXT NOT NULL,
                        current_price REAL NOT NULL,
                        original_price REAL,
                        currency TEXT DEFAULT 'INR',
                        discount_percentage REAL,
                        discount_amount REAL,
                        offers TEXT,
                        price_date TIMESTAMP,
                        scraped_at TIMESTAMP,
                        processed BOOLEAN DEFAULT FALSE
                    )
                """)
                
                # Quality scores table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS quality_scores (
                        record_id TEXT PRIMARY KEY,
                        record_type TEXT NOT NULL,
                        completeness_score REAL NOT NULL,
                        accuracy_score REAL NOT NULL,
                        consistency_score REAL NOT NULL,
                        overall_score REAL NOT NULL,
                        issues TEXT,
                        evaluated_at TIMESTAMP
                    )
                """)
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
    
    def save_job(self, job: ScrapingJobModel) -> bool:
        """Save scraping job to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO scraping_jobs 
                    (job_id, site, job_type, category, search_terms, max_pages, 
                     status, started_at, completed_at, products_scraped, reviews_scraped, errors, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.job_id, job.site.value, job.job_type, 
                    job.category.value if job.category else None,
                    json.dumps(job.search_terms), job.max_pages,
                    job.status, job.started_at, job.completed_at,
                    job.products_scraped, job.reviews_scraped,
                    json.dumps(job.errors), job.created_at
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save job {job.job_id}: {e}")
            return False
    
    def save_products(self, products: List[ProductModel]) -> bool:
        """Save products to staging table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for product in products:
                    cursor.execute("""
                        INSERT OR REPLACE INTO products_staging 
                        (product_id, site, name, category, brand, url, description, 
                         specifications, images, in_stock, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        product.product_id, product.site.value, product.name,
                        product.category.value, product.brand, product.url,
                        product.description, json.dumps(product.specifications),
                        json.dumps(product.images), product.in_stock, product.scraped_at
                    ))
                
                conn.commit()
                self.logger.info(f"Saved {len(products)} products to staging")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save products: {e}")
            return False
    
    def save_reviews(self, reviews: List[ReviewModel]) -> bool:
        """Save reviews to staging table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for review in reviews:
                    cursor.execute("""
                        INSERT OR REPLACE INTO reviews_staging 
                        (review_id, product_id, site, title, content, rating, 
                         reviewer_name, verified_purchase, review_date, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        review.review_id, review.product_id, review.site.value,
                        review.title, review.content, review.rating,
                        review.reviewer_name, review.verified_purchase,
                        review.review_date, review.scraped_at
                    ))
                
                conn.commit()
                self.logger.info(f"Saved {len(reviews)} reviews to staging")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save reviews: {e}")
            return False
    
    def save_pricing(self, pricing_data: List[PricingModel]) -> bool:
        """Save pricing data to staging table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for pricing in pricing_data:
                    cursor.execute("""
                        INSERT OR REPLACE INTO pricing_staging 
                        (price_id, product_id, site, current_price, original_price, 
                         currency, discount_percentage, discount_amount, offers, 
                         price_date, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        pricing.price_id, pricing.product_id, pricing.site.value,
                        pricing.current_price, pricing.original_price,
                        pricing.currency, pricing.discount_percentage,
                        pricing.discount_amount, json.dumps(pricing.offers),
                        pricing.price_date, pricing.scraped_at
                    ))
                
                conn.commit()
                self.logger.info(f"Saved {len(pricing_data)} pricing records to staging")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save pricing data: {e}")
            return False
    
    def save_quality_score(self, score: QualityScoreModel) -> bool:
        """Save quality score to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO quality_scores 
                    (record_id, record_type, completeness_score, accuracy_score, 
                     consistency_score, overall_score, issues, evaluated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    score.record_id, score.record_type,
                    score.completeness_score, score.accuracy_score,
                    score.consistency_score, score.overall_score,
                    json.dumps(score.issues), score.evaluated_at
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save quality score: {e}")
            return False
    
    def get_unprocessed_data(self, table_name: str, limit: int = 1000) -> List[Dict]:
        """Get unprocessed data from staging table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(f"""
                    SELECT * FROM {table_name} 
                    WHERE processed = FALSE 
                    LIMIT ?
                """, (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to get unprocessed data from {table_name}: {e}")
            return []
    
    def mark_as_processed(self, table_name: str, record_ids: List[str]) -> bool:
        """Mark records as processed."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get the primary key column name
                pk_column = 'product_id' if 'products' in table_name else \
                           'review_id' if 'reviews' in table_name else 'price_id'
                
                placeholders = ','.join(['?' for _ in record_ids])
                cursor.execute(f"""
                    UPDATE {table_name} 
                    SET processed = TRUE 
                    WHERE {pk_column} IN ({placeholders})
                """, record_ids)
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to mark records as processed: {e}")
            return False


class BigQueryManager:
    """Manages BigQuery operations for analytics data."""
    
    def __init__(self):
        self.logger = loggers["data"]
        self.project_id = settings.BIGQUERY_PROJECT
        self.dataset_id = settings.BIGQUERY_DATASET
        self.client = None
        
        if self.project_id:
            try:
                self.client = bigquery.Client(project=self.project_id)
                self._ensure_dataset_exists()
                self._ensure_tables_exist()
            except Exception as e:
                self.logger.warning(f"Could not initialize BigQuery: {e}")
    
    def _ensure_dataset_exists(self):
        """Ensure BigQuery dataset exists."""
        if not self.client:
            return
        
        try:
            dataset_ref = self.client.dataset(self.dataset_id)
            try:
                self.client.get_dataset(dataset_ref)
            except Exception:
                # Dataset doesn't exist, create it
                dataset = bigquery.Dataset(dataset_ref)
                dataset.location = "US"
                self.client.create_dataset(dataset)
                self.logger.info(f"Created BigQuery dataset: {self.dataset_id}")
        except Exception as e:
            self.logger.error(f"Failed to ensure dataset exists: {e}")
    
    def _ensure_tables_exist(self):
        """Ensure BigQuery tables exist."""
        if not self.client:
            return
        
        tables_schema = {
            'products': [
                bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("site", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("category", "STRING"),
                bigquery.SchemaField("brand", "STRING"),
                bigquery.SchemaField("url", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("description", "STRING"),
                bigquery.SchemaField("specifications", "STRING"),
                bigquery.SchemaField("images", "STRING"),
                bigquery.SchemaField("in_stock", "BOOLEAN"),
                bigquery.SchemaField("scraped_at", "TIMESTAMP"),
                bigquery.SchemaField("last_updated", "TIMESTAMP")
            ],
            'reviews': [
                bigquery.SchemaField("review_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("site", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("title", "STRING"),
                bigquery.SchemaField("content", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("rating", "FLOAT", mode="REQUIRED"),
                bigquery.SchemaField("reviewer_name", "STRING"),
                bigquery.SchemaField("verified_purchase", "BOOLEAN"),
                bigquery.SchemaField("review_date", "TIMESTAMP"),
                bigquery.SchemaField("scraped_at", "TIMESTAMP")
            ],
            'pricing': [
                bigquery.SchemaField("price_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("site", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("current_price", "FLOAT", mode="REQUIRED"),
                bigquery.SchemaField("original_price", "FLOAT"),
                bigquery.SchemaField("currency", "STRING"),
                bigquery.SchemaField("discount_percentage", "FLOAT"),
                bigquery.SchemaField("discount_amount", "FLOAT"),
                bigquery.SchemaField("offers", "STRING"),
                bigquery.SchemaField("price_date", "TIMESTAMP"),
                bigquery.SchemaField("scraped_at", "TIMESTAMP")
            ]
        }
        
        for table_name, schema in tables_schema.items():
            try:
                table_ref = self.client.dataset(self.dataset_id).table(table_name)
                
                try:
                    self.client.get_table(table_ref)
                except Exception:
                    # Table doesn't exist, create it
                    table = bigquery.Table(table_ref, schema=schema)
                    
                    # Add partitioning for better performance
                    if table_name in ['pricing']:
                        table.time_partitioning = bigquery.TimePartitioning(
                            type_=bigquery.TimePartitioningType.DAY,
                            field="price_date"
                        )
                    else:
                        table.time_partitioning = bigquery.TimePartitioning(
                            type_=bigquery.TimePartitioningType.DAY,
                            field="scraped_at"
                        )
                    
                    self.client.create_table(table)
                    self.logger.info(f"Created BigQuery table: {table_name}")
                    
            except Exception as e:
                self.logger.error(f"Failed to ensure table {table_name} exists: {e}")
    
    def load_data(self, table_name: str, data: List[Dict]) -> bool:
        """Load data into BigQuery table."""
        if not self.client or not data:
            return False
        
        try:
            table_ref = self.client.dataset(self.dataset_id).table(table_name)
            
            # Convert data to DataFrame for easier handling
            df = pd.DataFrame(data)
            
            # Load data
            job_config = bigquery.LoadJobConfig(
                write_disposition="WRITE_APPEND",
                autodetect=False
            )
            
            job = self.client.load_table_from_dataframe(
                df, table_ref, job_config=job_config
            )
            
            job.result()  # Wait for job to complete
            
            self.logger.info(f"Loaded {len(data)} records into {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load data into {table_name}: {e}")
            return False
    
    def query_data(self, query: str) -> Optional[pd.DataFrame]:
        """Execute query and return results."""
        if not self.client:
            return None
        
        try:
            return self.client.query(query).to_dataframe()
        except Exception as e:
            self.logger.error(f"Failed to execute query: {e}")
            return None