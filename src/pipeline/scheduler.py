"""
Job scheduler for automated scraping operations.
"""
import schedule
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..config.settings import settings
from ..config.logging_config import loggers
from ..data.models import ScrapingJobModel, SiteEnum, ProductCategory
from ..data.storage import LocalDatabaseManager
from ..scrapers import AmazonScraper, FlipkartScraper, MyntraScraper
from .processor import DataProcessor


class JobScheduler:
    """Manages scheduling and execution of scraping jobs."""
    
    def __init__(self):
        self.logger = loggers["pipeline"]
        self.db_manager = LocalDatabaseManager()
        self.data_processor = DataProcessor()
        self.running = False
        
        # Site scrapers mapping
        self.scrapers = {
            SiteEnum.AMAZON: AmazonScraper,
            SiteEnum.FLIPKART: FlipkartScraper,
            SiteEnum.MYNTRA: MyntraScraper
        }
        
        # Default search terms for different categories
        self.category_search_terms = {
            ProductCategory.ELECTRONICS: [
                "smartphone", "laptop", "headphones", "tablet", "camera"
            ],
            ProductCategory.CLOTHING: [
                "shirt", "jeans", "dress", "shoes", "jacket"
            ],
            ProductCategory.HOME_KITCHEN: [
                "cookware", "bedding", "furniture", "appliances", "decor"
            ],
            ProductCategory.BOOKS: [
                "fiction", "textbook", "biography", "thriller", "romance"
            ],
            ProductCategory.SPORTS: [
                "fitness", "cricket", "football", "running", "gym"
            ]
        }
    
    def setup_schedule(self):
        """Set up the default scraping schedule."""
        # Daily product discovery (spread across different times)
        schedule.every().day.at("02:00").do(
            self.schedule_discovery_jobs
        )
        
        # Hourly pricing updates for active products
        schedule.every().hour.do(
            self.schedule_pricing_jobs
        )
        
        # Daily review collection
        schedule.every().day.at("14:00").do(
            self.schedule_review_jobs
        )
        
        # Weekly comprehensive scraping
        schedule.every().sunday.at("01:00").do(
            self.schedule_comprehensive_jobs
        )
        
        # Daily data processing and quality checks
        schedule.every().day.at("06:00").do(
            self.process_pending_data
        )
        
        self.logger.info("Scraping schedule configured")
    
    def schedule_discovery_jobs(self):
        """Schedule product discovery jobs for all sites and categories."""
        jobs = []
        
        for site in [SiteEnum.AMAZON, SiteEnum.FLIPKART, SiteEnum.MYNTRA]:
            for category in settings.CATEGORIES:
                if category in self.category_search_terms:
                    search_terms = self.category_search_terms[ProductCategory(category)]
                    
                    job = ScrapingJobModel(
                        job_id=str(uuid.uuid4()),
                        site=site,
                        job_type="discovery",
                        category=ProductCategory(category),
                        search_terms=search_terms[:2],  # Limit to 2 terms per job
                        max_pages=5  # Conservative for daily discovery
                    )
                    
                    jobs.append(job)
                    self.db_manager.save_job(job)
        
        self.logger.info(f"Scheduled {len(jobs)} discovery jobs")
        return jobs
    
    def schedule_pricing_jobs(self):
        """Schedule pricing update jobs for existing products."""
        # Get products that need pricing updates (older than 6 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=6)
        
        # This would typically query the database for products needing updates
        # For now, we'll create a placeholder job
        job = ScrapingJobModel(
            job_id=str(uuid.uuid4()),
            site=SiteEnum.AMAZON,  # Can be rotated
            job_type="pricing_update",
            max_pages=1
        )
        
        self.db_manager.save_job(job)
        self.logger.info("Scheduled pricing update job")
        return [job]
    
    def schedule_review_jobs(self):
        """Schedule review collection jobs for products with few reviews."""
        jobs = []
        
        # Create sample review collection jobs
        for site in [SiteEnum.AMAZON, SiteEnum.FLIPKART]:
            job = ScrapingJobModel(
                job_id=str(uuid.uuid4()),
                site=site,
                job_type="review_collection",
                max_pages=3
            )
            
            jobs.append(job)
            self.db_manager.save_job(job)
        
        self.logger.info(f"Scheduled {len(jobs)} review collection jobs")
        return jobs
    
    def schedule_comprehensive_jobs(self):
        """Schedule comprehensive scraping jobs (weekly)."""
        jobs = []
        
        for site in [SiteEnum.AMAZON, SiteEnum.FLIPKART, SiteEnum.MYNTRA]:
            for category in settings.CATEGORIES[:2]:  # Limit to 2 categories per week
                if category in self.category_search_terms:
                    search_terms = self.category_search_terms[ProductCategory(category)]
                    
                    job = ScrapingJobModel(
                        job_id=str(uuid.uuid4()),
                        site=site,
                        job_type="comprehensive",
                        category=ProductCategory(category),
                        search_terms=search_terms,
                        max_pages=20  # More comprehensive
                    )
                    
                    jobs.append(job)
                    self.db_manager.save_job(job)
        
        self.logger.info(f"Scheduled {len(jobs)} comprehensive scraping jobs")
        return jobs
    
    def execute_pending_jobs(self, max_concurrent: int = 2):
        """Execute pending scraping jobs."""
        # Get pending jobs from database
        pending_jobs = self._get_pending_jobs()
        
        if not pending_jobs:
            self.logger.info("No pending jobs to execute")
            return
        
        self.logger.info(f"Executing {len(pending_jobs)} pending jobs")
        
        # Execute jobs with limited concurrency for resource management
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            future_to_job = {
                executor.submit(self._execute_job, job): job 
                for job in pending_jobs[:max_concurrent * 2]  # Limit total jobs
            }
            
            for future in as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    result = future.result()
                    self.logger.info(f"Job {job.job_id} completed: {result}")
                except Exception as e:
                    self.logger.error(f"Job {job.job_id} failed: {e}")
                    self._mark_job_failed(job, str(e))
    
    def _get_pending_jobs(self) -> List[ScrapingJobModel]:
        """Get pending jobs from database."""
        try:
            # This is a simplified version - in practice you'd query the database
            # For now, return empty list as we'd need to implement the query logic
            return []
        except Exception as e:
            self.logger.error(f"Failed to get pending jobs: {e}")
            return []
    
    def _execute_job(self, job: ScrapingJobModel) -> Dict[str, Any]:
        """Execute a single scraping job."""
        try:
            # Mark job as started
            job.status = "running"
            job.started_at = datetime.utcnow()
            self.db_manager.save_job(job)
            
            # Get appropriate scraper
            scraper_class = self.scrapers.get(job.site)
            if not scraper_class:
                raise ValueError(f"No scraper available for site: {job.site}")
            
            scraper = scraper_class()
            
            results = {
                "products": [],
                "reviews": [],
                "pricing": []
            }
            
            try:
                if job.job_type == "discovery":
                    results = self._execute_discovery_job(scraper, job)
                elif job.job_type == "pricing_update":
                    results = self._execute_pricing_job(scraper, job)
                elif job.job_type == "review_collection":
                    results = self._execute_review_job(scraper, job)
                elif job.job_type == "comprehensive":
                    results = self._execute_comprehensive_job(scraper, job)
                
                # Update job status
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.products_scraped = len(results.get("products", []))
                job.reviews_scraped = len(results.get("reviews", []))
                
            finally:
                scraper.close()
            
            self.db_manager.save_job(job)
            return results
            
        except Exception as e:
            self.logger.error(f"Job execution failed: {e}")
            self._mark_job_failed(job, str(e))
            raise
    
    def _execute_discovery_job(self, scraper, job: ScrapingJobModel) -> Dict[str, Any]:
        """Execute product discovery job."""
        products = []
        
        for search_term in job.search_terms:
            try:
                category = job.category.value if job.category else None
                for product_data in scraper.search_products(
                    search_term, category, job.max_pages
                ):
                    # Extract product details
                    product = scraper.scrape_product_details(product_data['url'])
                    if product:
                        products.append(product)
                        
                        # Also collect pricing
                        pricing = scraper.scrape_product_pricing(product_data['url'])
                        if pricing:
                            self.data_processor.process_pricing([pricing])
                    
                    # Respect rate limits
                    time.sleep(2)
                    
            except Exception as e:
                job.errors.append(f"Discovery error for '{search_term}': {str(e)}")
        
        # Process collected products
        if products:
            self.data_processor.process_products(products)
        
        return {"products": products, "reviews": [], "pricing": []}
    
    def _execute_pricing_job(self, scraper, job: ScrapingJobModel) -> Dict[str, Any]:
        """Execute pricing update job."""
        # This would typically get products needing price updates from database
        # For now, return empty results
        return {"products": [], "reviews": [], "pricing": []}
    
    def _execute_review_job(self, scraper, job: ScrapingJobModel) -> Dict[str, Any]:
        """Execute review collection job."""
        # This would typically get products needing review updates from database
        # For now, return empty results
        return {"products": [], "reviews": [], "pricing": []}
    
    def _execute_comprehensive_job(self, scraper, job: ScrapingJobModel) -> Dict[str, Any]:
        """Execute comprehensive scraping job."""
        results = self._execute_discovery_job(scraper, job)
        
        # For comprehensive jobs, also collect reviews for products
        reviews = []
        for product in results["products"][:10]:  # Limit to 10 products for reviews
            try:
                product_reviews = scraper.scrape_product_reviews(product.url, max_reviews=20)
                reviews.extend(product_reviews)
                time.sleep(3)  # Extra delay for review scraping
            except Exception as e:
                job.errors.append(f"Review collection error for {product.product_id}: {str(e)}")
        
        if reviews:
            self.data_processor.process_reviews(reviews)
        
        results["reviews"] = reviews
        return results
    
    def _mark_job_failed(self, job: ScrapingJobModel, error: str):
        """Mark job as failed with error message."""
        job.status = "failed"
        job.completed_at = datetime.utcnow()
        job.errors.append(error)
        self.db_manager.save_job(job)
    
    def process_pending_data(self):
        """Process pending data in staging tables."""
        self.data_processor.process_all_pending()
        self.logger.info("Processed pending data")
    
    def start(self):
        """Start the scheduler."""
        self.running = True
        self.logger.info("Job scheduler started")
        
        while self.running:
            try:
                schedule.run_pending()
                
                # Execute pending jobs every 30 minutes
                if datetime.utcnow().minute % 30 == 0:
                    self.execute_pending_jobs()
                
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                self.logger.info("Scheduler interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                time.sleep(60)  # Wait before retrying
        
        self.stop()
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        self.logger.info("Job scheduler stopped")


def run_scheduler():
    """Entry point for running the scheduler."""
    scheduler = JobScheduler()
    scheduler.setup_schedule()
    scheduler.start()