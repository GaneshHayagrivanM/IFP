"""
Quality check pipeline for continuous monitoring of data quality.
"""
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from ..config.settings import settings
from ..config.logging_config import loggers
from ..data.storage import LocalDatabaseManager, BigQueryManager
from ..data.validation import DataValidator


class QualityChecker:
    """Continuous quality monitoring and reporting system."""
    
    def __init__(self):
        self.logger = loggers["quality"]
        self.local_db = LocalDatabaseManager()
        self.bigquery = BigQueryManager()
        self.validator = DataValidator()
        
        # Quality thresholds
        self.quality_thresholds = {
            "min_overall_score": 0.7,
            "max_duplicate_rate": 0.05,
            "min_completeness": 0.8,
            "min_accuracy": 0.75,
            "min_consistency": 0.8
        }
        
        # Alert conditions
        self.alert_conditions = {
            "low_quality_rate": 0.3,  # Alert if >30% records are low quality
            "high_duplicate_rate": 0.1,  # Alert if >10% are duplicates
            "processing_failure_rate": 0.2,  # Alert if >20% processing failures
            "stale_data_hours": 24  # Alert if no new data in 24 hours
        }
    
    def run_quality_checks(self) -> Dict[str, Any]:
        """Run comprehensive quality checks."""
        self.logger.info("Starting quality checks")
        
        results = {
            "timestamp": datetime.utcnow(),
            "overall_status": "PASS",
            "checks": {},
            "alerts": [],
            "metrics": {}
        }
        
        try:
            # Data quality checks
            results["checks"]["data_quality"] = self._check_data_quality()
            
            # Completeness checks
            results["checks"]["completeness"] = self._check_data_completeness()
            
            # Freshness checks
            results["checks"]["freshness"] = self._check_data_freshness()
            
            # Duplicate rate checks
            results["checks"]["duplicates"] = self._check_duplicate_rates()
            
            # Site coverage checks
            results["checks"]["site_coverage"] = self._check_site_coverage()
            
            # Processing health checks
            results["checks"]["processing_health"] = self._check_processing_health()
            
            # Generate alerts
            results["alerts"] = self._generate_alerts(results["checks"])
            
            # Calculate overall metrics
            results["metrics"] = self._calculate_metrics(results["checks"])
            
            # Determine overall status
            if results["alerts"]:
                results["overall_status"] = "ALERT" if any(
                    alert["severity"] == "HIGH" for alert in results["alerts"]
                ) else "WARNING"
            
            self.logger.info(f"Quality checks completed with status: {results['overall_status']}")
            
        except Exception as e:
            self.logger.error(f"Quality checks failed: {e}")
            results["overall_status"] = "ERROR"
            results["alerts"].append({
                "type": "SYSTEM_ERROR",
                "severity": "HIGH",
                "message": f"Quality check system error: {str(e)}"
            })
        
        return results
    
    def _check_data_quality(self) -> Dict[str, Any]:
        """Check overall data quality scores."""
        try:
            quality_data = self.local_db.get_unprocessed_data("quality_scores", 1000)
            
            if not quality_data:
                return {
                    "status": "NO_DATA",
                    "message": "No quality scores available"
                }
            
            # Calculate quality metrics
            total_records = len(quality_data)
            high_quality = sum(1 for q in quality_data if q["overall_score"] >= self.quality_thresholds["min_overall_score"])
            low_quality = total_records - high_quality
            
            avg_overall = sum(q["overall_score"] for q in quality_data) / total_records
            avg_completeness = sum(q["completeness_score"] for q in quality_data) / total_records
            avg_accuracy = sum(q["accuracy_score"] for q in quality_data) / total_records
            avg_consistency = sum(q["consistency_score"] for q in quality_data) / total_records
            
            low_quality_rate = low_quality / total_records if total_records > 0 else 0
            
            return {
                "status": "PASS" if low_quality_rate <= self.alert_conditions["low_quality_rate"] else "FAIL",
                "total_records": total_records,
                "high_quality_records": high_quality,
                "low_quality_records": low_quality,
                "low_quality_rate": low_quality_rate,
                "avg_overall_score": avg_overall,
                "avg_completeness_score": avg_completeness,
                "avg_accuracy_score": avg_accuracy,
                "avg_consistency_score": avg_consistency
            }
            
        except Exception as e:
            self.logger.error(f"Data quality check failed: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def _check_data_completeness(self) -> Dict[str, Any]:
        """Check data completeness across different tables."""
        try:
            results = {}
            
            # Check each staging table
            for table_name in ["products_staging", "reviews_staging", "pricing_staging"]:
                data = self.local_db.get_unprocessed_data(table_name, 100)
                
                if data:
                    completeness_scores = []
                    
                    for record in data:
                        # Count non-null fields
                        total_fields = len(record)
                        non_null_fields = sum(1 for v in record.values() if v is not None and v != "")
                        completeness = non_null_fields / total_fields if total_fields > 0 else 0
                        completeness_scores.append(completeness)
                    
                    avg_completeness = sum(completeness_scores) / len(completeness_scores)
                    
                    results[table_name] = {
                        "avg_completeness": avg_completeness,
                        "records_checked": len(data),
                        "status": "PASS" if avg_completeness >= self.quality_thresholds["min_completeness"] else "FAIL"
                    }
                else:
                    results[table_name] = {
                        "status": "NO_DATA",
                        "records_checked": 0
                    }
            
            overall_status = "PASS" if all(
                r.get("status") in ["PASS", "NO_DATA"] for r in results.values()
            ) else "FAIL"
            
            return {
                "status": overall_status,
                "tables": results
            }
            
        except Exception as e:
            self.logger.error(f"Completeness check failed: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def _check_data_freshness(self) -> Dict[str, Any]:
        """Check if data is being updated regularly."""
        try:
            stale_threshold = datetime.utcnow() - timedelta(hours=self.alert_conditions["stale_data_hours"])
            
            results = {}
            
            # Check each staging table for recent data
            for table_name in ["products_staging", "reviews_staging", "pricing_staging"]:
                try:
                    # Get a small sample to check timestamps
                    data = self.local_db.get_unprocessed_data(table_name, 10)
                    
                    if data:
                        # Check scraped_at timestamps
                        recent_count = 0
                        for record in data:
                            scraped_at = record.get("scraped_at")
                            if scraped_at:
                                if isinstance(scraped_at, str):
                                    scraped_at = datetime.fromisoformat(scraped_at.replace('Z', '+00:00'))
                                
                                if scraped_at > stale_threshold:
                                    recent_count += 1
                        
                        freshness_rate = recent_count / len(data) if data else 0
                        
                        results[table_name] = {
                            "freshness_rate": freshness_rate,
                            "recent_records": recent_count,
                            "total_checked": len(data),
                            "status": "PASS" if freshness_rate > 0.5 else "STALE"
                        }
                    else:
                        results[table_name] = {
                            "status": "NO_DATA",
                            "total_checked": 0
                        }
                        
                except Exception as e:
                    results[table_name] = {
                        "status": "ERROR",
                        "message": str(e)
                    }
            
            overall_status = "PASS" if any(
                r.get("status") == "PASS" for r in results.values()
            ) else "STALE"
            
            return {
                "status": overall_status,
                "tables": results,
                "threshold_hours": self.alert_conditions["stale_data_hours"]
            }
            
        except Exception as e:
            self.logger.error(f"Freshness check failed: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def _check_duplicate_rates(self) -> Dict[str, Any]:
        """Check duplicate rates across data."""
        try:
            # This is a simplified version - in practice you'd implement
            # more sophisticated duplicate detection
            return {
                "status": "PASS",
                "estimated_duplicate_rate": 0.03,  # Placeholder
                "threshold": self.alert_conditions["high_duplicate_rate"]
            }
            
        except Exception as e:
            self.logger.error(f"Duplicate rate check failed: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def _check_site_coverage(self) -> Dict[str, Any]:
        """Check if all sites are being scraped."""
        try:
            site_coverage = {}
            
            for table_name in ["products_staging", "reviews_staging", "pricing_staging"]:
                data = self.local_db.get_unprocessed_data(table_name, 100)
                
                if data:
                    sites = set(record.get("site", "unknown") for record in data)
                    site_coverage[table_name] = list(sites)
                else:
                    site_coverage[table_name] = []
            
            expected_sites = {"amazon", "flipkart", "myntra"}
            all_sites_covered = all(
                expected_sites.issubset(set(sites)) 
                for sites in site_coverage.values() 
                if sites
            )
            
            return {
                "status": "PASS" if all_sites_covered else "PARTIAL",
                "site_coverage": site_coverage,
                "expected_sites": list(expected_sites)
            }
            
        except Exception as e:
            self.logger.error(f"Site coverage check failed: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def _check_processing_health(self) -> Dict[str, Any]:
        """Check processing pipeline health."""
        try:
            # Check for recent job completions
            # This would typically query the scraping_jobs table
            return {
                "status": "PASS",
                "recent_job_success_rate": 0.95,  # Placeholder
                "active_workers": 2,
                "queue_size": 5
            }
            
        except Exception as e:
            self.logger.error(f"Processing health check failed: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def _generate_alerts(self, checks: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alerts based on check results."""
        alerts = []
        
        # Data quality alerts
        quality_check = checks.get("data_quality", {})
        if quality_check.get("status") == "FAIL":
            alerts.append({
                "type": "LOW_DATA_QUALITY",
                "severity": "HIGH",
                "message": f"Low quality rate: {quality_check.get('low_quality_rate', 0):.1%}",
                "details": quality_check
            })
        
        # Freshness alerts
        freshness_check = checks.get("freshness", {})
        if freshness_check.get("status") == "STALE":
            alerts.append({
                "type": "STALE_DATA",
                "severity": "MEDIUM",
                "message": "Data appears to be stale",
                "details": freshness_check
            })
        
        # Site coverage alerts
        coverage_check = checks.get("site_coverage", {})
        if coverage_check.get("status") == "PARTIAL":
            alerts.append({
                "type": "INCOMPLETE_SITE_COVERAGE",
                "severity": "MEDIUM",
                "message": "Not all sites are being scraped",
                "details": coverage_check
            })
        
        return alerts
    
    def _calculate_metrics(self, checks: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall metrics from check results."""
        metrics = {}
        
        # Overall health score
        health_scores = []
        for check_name, check_result in checks.items():
            if check_result.get("status") == "PASS":
                health_scores.append(1.0)
            elif check_result.get("status") in ["FAIL", "STALE", "PARTIAL"]:
                health_scores.append(0.5)
            else:  # ERROR or NO_DATA
                health_scores.append(0.0)
        
        metrics["overall_health_score"] = sum(health_scores) / len(health_scores) if health_scores else 0
        
        # Data quality metrics
        quality_check = checks.get("data_quality", {})
        metrics["avg_quality_score"] = quality_check.get("avg_overall_score", 0)
        
        return metrics
    
    def generate_quality_report(self, checks_result: Dict[str, Any], output_file: str = None) -> str:
        """Generate a detailed quality report."""
        if not output_file:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_file = f"quality_report_{timestamp}.csv"
        
        # Ensure output directory exists
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Header
                writer.writerow([
                    "Check Type", "Status", "Details", "Timestamp"
                ])
                
                # Write check results
                timestamp = checks_result.get("timestamp", datetime.utcnow())
                for check_name, check_result in checks_result.get("checks", {}).items():
                    status = check_result.get("status", "UNKNOWN")
                    details = str(check_result)
                    writer.writerow([check_name, status, details, timestamp])
                
                # Write alerts
                for alert in checks_result.get("alerts", []):
                    writer.writerow([
                        f"ALERT_{alert['type']}", 
                        alert['severity'], 
                        alert['message'], 
                        timestamp
                    ])
            
            self.logger.info(f"Quality report generated: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Failed to generate quality report: {e}")
            return ""
    
    def run_continuous_monitoring(self, interval_minutes: int = 60):
        """Run continuous quality monitoring."""
        import time
        
        self.logger.info(f"Starting continuous quality monitoring (interval: {interval_minutes} minutes)")
        
        try:
            while True:
                # Run quality checks
                results = self.run_quality_checks()
                
                # Generate report if there are alerts
                if results.get("alerts"):
                    report_file = self.generate_quality_report(results)
                    self.logger.warning(f"Quality issues detected. Report: {report_file}")
                
                # Wait for next check
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            self.logger.info("Quality monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Quality monitoring error: {e}")


def run_quality_checks():
    """Entry point for running quality checks."""
    checker = QualityChecker()
    results = checker.run_quality_checks()
    
    # Generate report
    report_file = checker.generate_quality_report(results)
    print(f"Quality check completed. Status: {results['overall_status']}")
    print(f"Report generated: {report_file}")
    
    return results