"""
Main entry point for the web scraping system.
"""
import sys
import argparse
import signal
import time
from datetime import datetime
from typing import Optional

from .config.settings import settings
from .config.logging_config import setup_logging, loggers
from .pipeline.scheduler import JobScheduler, run_scheduler
from .pipeline.quality_check import run_quality_checks
from .data.storage import LocalDatabaseManager
from .monitoring.metrics import metrics_collector
from .monitoring.reporting import ReportGenerator


class ScrapingSystemManager:
    """Main system manager for the web scraping application."""
    
    def __init__(self):
        self.logger = loggers["scraper"]
        self.scheduler: Optional[JobScheduler] = None
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()
    
    def start_scheduler(self):
        """Start the job scheduler."""
        self.logger.info("Starting web scraping system...")
        
        try:
            # Initialize database
            db_manager = LocalDatabaseManager()
            
            # Start metrics collection
            metrics_collector.collect_all_metrics()
            
            # Start scheduler
            self.scheduler = JobScheduler()
            self.scheduler.setup_schedule()
            
            self.running = True
            self.logger.info("Web scraping system started successfully")
            
            # Start the scheduler (this will block)
            self.scheduler.start()
            
        except Exception as e:
            self.logger.error(f"Failed to start system: {e}")
            sys.exit(1)
    
    def run_single_job(self, site: str, job_type: str, category: str = None, search_terms: list = None):
        """Run a single scraping job."""
        self.logger.info(f"Running single job: {site} - {job_type}")
        
        try:
            from .data.models import ScrapingJobModel, SiteEnum, ProductCategory
            import uuid
            
            # Create job
            job = ScrapingJobModel(
                job_id=str(uuid.uuid4()),
                site=SiteEnum(site),
                job_type=job_type,
                category=ProductCategory(category) if category else None,
                search_terms=search_terms or ["electronics"],
                max_pages=5
            )
            
            # Execute job
            scheduler = JobScheduler()
            result = scheduler._execute_job(job)
            
            self.logger.info(f"Job completed successfully: {result}")
            
        except Exception as e:
            self.logger.error(f"Failed to run single job: {e}")
            sys.exit(1)
    
    def generate_reports(self, report_type: str = "daily"):
        """Generate reports."""
        self.logger.info(f"Generating {report_type} report...")
        
        try:
            report_generator = ReportGenerator()
            
            if report_type == "daily":
                report = report_generator.generate_daily_summary()
            elif report_type == "weekly":
                report = report_generator.generate_weekly_report()
            elif report_type == "cost":
                report = report_generator.generate_cost_report()
            else:
                raise ValueError(f"Unknown report type: {report_type}")
            
            # Save report
            output_file = report_generator.save_report(report, report_type)
            csv_file = report_generator.generate_csv_summary(report)
            
            self.logger.info(f"Report generated: {output_file}")
            self.logger.info(f"CSV summary: {csv_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate report: {e}")
            sys.exit(1)
    
    def run_quality_check(self):
        """Run quality checks."""
        self.logger.info("Running quality checks...")
        
        try:
            results = run_quality_checks()
            
            if results["overall_status"] == "PASS":
                self.logger.info("Quality checks passed")
            else:
                self.logger.warning(f"Quality checks failed: {results['overall_status']}")
                
        except Exception as e:
            self.logger.error(f"Quality check failed: {e}")
            sys.exit(1)
    
    def stop(self):
        """Stop the system gracefully."""
        self.running = False
        
        if self.scheduler:
            self.scheduler.stop()
        
        self.logger.info("System stopped gracefully")


def main():
    """Main entry point with command-line interface."""
    parser = argparse.ArgumentParser(description="E-commerce Web Scraping System")
    parser.add_argument(
        "command",
        choices=["start", "job", "report", "quality-check", "test"],
        help="Command to execute"
    )
    
    # Job-specific arguments
    parser.add_argument("--site", choices=["amazon", "flipkart", "myntra"], help="Site to scrape")
    parser.add_argument("--job-type", choices=["discovery", "pricing_update", "review_collection", "comprehensive"], help="Type of job")
    parser.add_argument("--category", choices=["electronics", "clothing", "home-kitchen", "books", "sports"], help="Product category")
    parser.add_argument("--search-terms", nargs="+", help="Search terms for discovery jobs")
    
    # Report-specific arguments
    parser.add_argument("--report-type", choices=["daily", "weekly", "cost"], default="daily", help="Type of report to generate")
    
    # Logging arguments
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO", help="Logging level")
    parser.add_argument("--log-file", help="Log file path")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(
        level=args.log_level,
        log_file=args.log_file
    )
    
    # Create system manager
    system = ScrapingSystemManager()
    
    try:
        if args.command == "start":
            system.start_scheduler()
            
        elif args.command == "job":
            if not args.site or not args.job_type:
                parser.error("--site and --job-type are required for job command")
            
            system.run_single_job(
                site=args.site,
                job_type=args.job_type,
                category=args.category,
                search_terms=args.search_terms
            )
            
        elif args.command == "report":
            system.generate_reports(args.report_type)
            
        elif args.command == "quality-check":
            system.run_quality_check()
            
        elif args.command == "test":
            print("System test passed!")
            print(f"Settings loaded: {len(settings.SITES)} sites configured")
            print(f"Categories: {settings.CATEGORIES}")
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        system.stop()
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()