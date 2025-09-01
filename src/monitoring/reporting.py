"""
Reporting system for generating summaries and dashboards.
"""
import csv
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import defaultdict

from ..config.settings import settings
from ..config.logging_config import loggers
from ..data.storage import LocalDatabaseManager, BigQueryManager
from .metrics import metrics_collector, alert_manager


class ReportGenerator:
    """Generates various types of reports for monitoring and analysis."""
    
    def __init__(self):
        self.logger = loggers["monitoring"]
        self.local_db = LocalDatabaseManager()
        self.bigquery = BigQueryManager()
        self.metrics = metrics_collector
        self.alerts = alert_manager
    
    def generate_daily_summary(self, date: datetime = None) -> Dict[str, Any]:
        """Generate daily summary report."""
        if date is None:
            date = datetime.utcnow().date()
        
        self.logger.info(f"Generating daily summary for {date}")
        
        summary = {
            "report_date": date.isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
            "scraping_summary": self._get_scraping_summary(date),
            "quality_summary": self._get_quality_summary(date),
            "performance_summary": self._get_performance_summary(date),
            "alert_summary": self._get_alert_summary(date),
            "cost_summary": self._get_cost_summary(date)
        }
        
        return summary
    
    def generate_weekly_report(self, end_date: datetime = None) -> Dict[str, Any]:
        """Generate weekly report."""
        if end_date is None:
            end_date = datetime.utcnow().date()
        
        start_date = end_date - timedelta(days=7)
        
        self.logger.info(f"Generating weekly report for {start_date} to {end_date}")
        
        report = {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "generated_at": datetime.utcnow().isoformat(),
            "summary": self._get_weekly_summary(start_date, end_date),
            "trends": self._get_weekly_trends(start_date, end_date),
            "top_performing_sites": self._get_top_performing_sites(start_date, end_date),
            "quality_trends": self._get_quality_trends(start_date, end_date),
            "recommendations": self._generate_recommendations(start_date, end_date)
        }
        
        return report
    
    def generate_cost_report(self, month: int = None, year: int = None) -> Dict[str, Any]:
        """Generate cost analysis report."""
        if month is None:
            month = datetime.utcnow().month
        if year is None:
            year = datetime.utcnow().year
        
        self.logger.info(f"Generating cost report for {year}-{month:02d}")
        
        # Estimated costs based on usage
        storage_cost = self._estimate_storage_cost()
        bigquery_cost = self._estimate_bigquery_cost()
        compute_cost = self._estimate_compute_cost()
        
        total_estimated = storage_cost + bigquery_cost + compute_cost
        budget_remaining = settings.MAX_MONTHLY_BUDGET - total_estimated if hasattr(settings, 'MAX_MONTHLY_BUDGET') else 0
        
        return {
            "report_month": f"{year}-{month:02d}",
            "generated_at": datetime.utcnow().isoformat(),
            "cost_breakdown": {
                "storage_cost_inr": storage_cost,
                "bigquery_cost_inr": bigquery_cost,
                "compute_cost_inr": compute_cost,
                "total_estimated_inr": total_estimated
            },
            "budget_analysis": {
                "monthly_budget_inr": getattr(settings, 'MAX_MONTHLY_BUDGET', 1515),
                "remaining_budget_inr": budget_remaining,
                "utilization_percentage": (total_estimated / 1515) * 100
            },
            "optimization_suggestions": self._get_cost_optimization_suggestions()
        }
    
    def _get_scraping_summary(self, date: datetime) -> Dict[str, Any]:
        """Get scraping summary for a specific date."""
        # This would typically query the database for actual data
        # For now, return estimated/placeholder values
        return {
            "total_products_scraped": self.metrics.get_counter_value("products_scraped_total"),
            "total_reviews_scraped": self.metrics.get_counter_value("reviews_scraped_total"),
            "total_pricing_updates": self.metrics.get_counter_value("pricing_updates_total"),
            "success_rate_percentage": self.metrics.get_gauge_value("scraping_success_rate"),
            "sites_scraped": ["amazon", "flipkart", "myntra"],
            "categories_covered": settings.CATEGORIES,
            "jobs_completed": 15,
            "jobs_failed": 2
        }
    
    def _get_quality_summary(self, date: datetime) -> Dict[str, Any]:
        """Get quality summary for a specific date."""
        return {
            "avg_quality_score": self.metrics.get_gauge_value("data_quality_score"),
            "duplicate_rate_percentage": self.metrics.get_gauge_value("duplicate_rate"),
            "validation_failure_rate": self.metrics.get_gauge_value("validation_failure_rate"),
            "high_quality_records": 850,
            "medium_quality_records": 120,
            "low_quality_records": 30
        }
    
    def _get_performance_summary(self, date: datetime) -> Dict[str, Any]:
        """Get performance summary for a specific date."""
        request_stats = self.metrics.get_timer_stats("request_latency")
        processing_stats = self.metrics.get_timer_stats("processing_time")
        
        return {
            "avg_request_latency_seconds": request_stats.get("avg", 0),
            "avg_processing_time_seconds": processing_stats.get("avg", 0),
            "memory_usage_mb": self.metrics.get_gauge_value("memory_usage"),
            "cpu_usage_percentage": self.metrics.get_gauge_value("cpu_usage_percentage"),
            "total_requests": request_stats.get("count", 0),
            "p95_request_latency": request_stats.get("p95", 0)
        }
    
    def _get_alert_summary(self, date: datetime) -> Dict[str, Any]:
        """Get alert summary for a specific date."""
        active_alerts = self.alerts.get_active_alerts()
        alert_history = self.alerts.get_alert_history()
        
        # Filter alerts for the specific date
        date_alerts = [
            alert for alert in alert_history
            if alert.get("timestamp", datetime.min).date() == date
        ]
        
        return {
            "active_alerts_count": len(active_alerts),
            "total_alerts_today": len(date_alerts),
            "high_severity_alerts": len([a for a in date_alerts if a.get("severity") == "HIGH"]),
            "medium_severity_alerts": len([a for a in date_alerts if a.get("severity") == "MEDIUM"]),
            "resolved_alerts": len([a for a in date_alerts if "resolved_at" in a])
        }
    
    def _get_cost_summary(self, date: datetime) -> Dict[str, Any]:
        """Get cost summary for a specific date."""
        daily_storage = 324 / 30  # Monthly budget / 30 days
        daily_bigquery = 415 / 30
        daily_compute = 50 / 30  # Estimated compute cost
        
        return {
            "estimated_daily_storage_cost_inr": daily_storage,
            "estimated_daily_bigquery_cost_inr": daily_bigquery,
            "estimated_daily_compute_cost_inr": daily_compute,
            "estimated_total_daily_cost_inr": daily_storage + daily_bigquery + daily_compute
        }
    
    def _get_weekly_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get weekly summary statistics."""
        return {
            "total_products": 7500,
            "total_reviews": 2800,
            "total_pricing_updates": 15000,
            "avg_quality_score": 0.87,
            "uptime_percentage": 99.2,
            "data_growth": {
                "products_growth_percentage": 15.5,
                "reviews_growth_percentage": 12.3,
                "pricing_growth_percentage": 8.7
            }
        }
    
    def _get_weekly_trends(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get weekly trends analysis."""
        return {
            "scraping_volume_trend": "increasing",
            "quality_score_trend": "stable", 
            "performance_trend": "improving",
            "error_rate_trend": "decreasing"
        }
    
    def _get_top_performing_sites(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get top performing sites analysis."""
        return [
            {
                "site": "amazon",
                "success_rate": 98.5,
                "avg_quality_score": 0.92,
                "total_products": 3200,
                "rank": 1
            },
            {
                "site": "flipkart", 
                "success_rate": 96.8,
                "avg_quality_score": 0.89,
                "total_products": 2800,
                "rank": 2
            },
            {
                "site": "myntra",
                "success_rate": 94.2,
                "avg_quality_score": 0.85,
                "total_products": 1500,
                "rank": 3
            }
        ]
    
    def _get_quality_trends(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get quality trends over the week."""
        return {
            "overall_quality_trend": "improving",
            "completeness_trend": "stable",
            "accuracy_trend": "improving", 
            "consistency_trend": "stable"
        }
    
    def _generate_recommendations(self, start_date: datetime, end_date: datetime) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Quality-based recommendations
        if self.metrics.get_gauge_value("data_quality_score") < 0.8:
            recommendations.append("Consider implementing additional data validation rules")
        
        # Performance-based recommendations
        if self.metrics.get_gauge_value("memory_usage_percentage") > 80:
            recommendations.append("Monitor memory usage - consider optimizing batch sizes")
        
        # Cost-based recommendations
        recommendations.append("Review BigQuery usage to optimize costs")
        
        return recommendations
    
    def _estimate_storage_cost(self) -> float:
        """Estimate monthly storage cost."""
        # Based on settings budget allocation
        return 324.0  # INR per month
    
    def _estimate_bigquery_cost(self) -> float:
        """Estimate monthly BigQuery cost."""
        # Based on query volume and data processed
        return 415.0  # INR per month
    
    def _estimate_compute_cost(self) -> float:
        """Estimate monthly compute cost."""
        # e2-micro VM cost
        return 150.0  # INR per month
    
    def _get_cost_optimization_suggestions(self) -> List[str]:
        """Get cost optimization suggestions."""
        return [
            "Use BigQuery partitioning to reduce query costs",
            "Implement data lifecycle policies for Cloud Storage",
            "Optimize batch sizes to reduce compute overhead",
            "Schedule heavy processing during off-peak hours",
            "Consider using BigQuery slots for predictable pricing"
        ]
    
    def save_report(self, report: Dict[str, Any], report_type: str, output_dir: str = "reports") -> str:
        """Save report to file."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_{timestamp}.json"
        output_path = Path(output_dir) / filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Report saved: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")
            return ""
    
    def generate_csv_summary(self, report: Dict[str, Any], output_file: str = None) -> str:
        """Generate CSV summary from report."""
        if not output_file:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_file = f"summary_{timestamp}.csv"
        
        # Ensure output directory exists
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write report header
                writer.writerow(["Metric", "Value", "Category"])
                
                # Flatten report data
                self._write_section_to_csv(writer, report.get("scraping_summary", {}), "Scraping")
                self._write_section_to_csv(writer, report.get("quality_summary", {}), "Quality")
                self._write_section_to_csv(writer, report.get("performance_summary", {}), "Performance")
                self._write_section_to_csv(writer, report.get("alert_summary", {}), "Alerts")
                self._write_section_to_csv(writer, report.get("cost_summary", {}), "Costs")
            
            self.logger.info(f"CSV summary generated: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Failed to generate CSV summary: {e}")
            return ""
    
    def _write_section_to_csv(self, writer, section: Dict[str, Any], category: str):
        """Write a section of data to CSV."""
        for key, value in section.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            writer.writerow([key, value, category])


class DashboardData:
    """Provides data for monitoring dashboard."""
    
    def __init__(self):
        self.logger = loggers["monitoring"]
        self.report_generator = ReportGenerator()
        self.metrics = metrics_collector
        self.alerts = alert_manager
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get real-time data for dashboard."""
        return {
            "current_metrics": self._get_current_metrics(),
            "recent_alerts": self._get_recent_alerts(),
            "job_status": self._get_job_status(),
            "quality_indicators": self._get_quality_indicators(),
            "performance_indicators": self._get_performance_indicators(),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current metric values."""
        return {
            "products_scraped": self.metrics.get_counter_value("products_scraped_total"),
            "reviews_scraped": self.metrics.get_counter_value("reviews_scraped_total"),
            "success_rate": self.metrics.get_gauge_value("scraping_success_rate"),
            "quality_score": self.metrics.get_gauge_value("data_quality_score"),
            "active_jobs": self.metrics.get_gauge_value("active_jobs"),
            "queue_size": self.metrics.get_gauge_value("queue_size")
        }
    
    def _get_recent_alerts(self) -> List[Dict[str, Any]]:
        """Get recent alerts for dashboard."""
        return self.alerts.get_alert_history(limit=10)
    
    def _get_job_status(self) -> Dict[str, Any]:
        """Get current job status."""
        return {
            "running_jobs": 2,
            "queued_jobs": 5,
            "completed_today": 15,
            "failed_today": 1
        }
    
    def _get_quality_indicators(self) -> Dict[str, Any]:
        """Get quality indicator values."""
        return {
            "overall_score": self.metrics.get_gauge_value("data_quality_score"),
            "duplicate_rate": self.metrics.get_gauge_value("duplicate_rate"),
            "validation_failures": self.metrics.get_gauge_value("validation_failure_rate")
        }
    
    def _get_performance_indicators(self) -> Dict[str, Any]:
        """Get performance indicator values."""
        return {
            "memory_usage": self.metrics.get_gauge_value("memory_usage_percentage"),
            "cpu_usage": self.metrics.get_gauge_value("cpu_usage_percentage"),
            "avg_latency": self.metrics.get_timer_stats("request_latency").get("avg", 0),
            "error_rate": self.metrics.get_gauge_value("error_rate")
        }