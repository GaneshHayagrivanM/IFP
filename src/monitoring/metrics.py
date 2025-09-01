"""
Metrics collection and monitoring system.
"""
import csv
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import defaultdict, deque

from ..config.settings import settings
from ..config.logging_config import loggers
from ..data.storage import LocalDatabaseManager


class MetricsCollector:
    """Collects and tracks system metrics."""
    
    def __init__(self):
        self.logger = loggers["monitoring"]
        self.local_db = LocalDatabaseManager()
        
        # In-memory metrics storage (for recent data)
        self.metrics_buffer = deque(maxlen=1000)
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.timers = defaultdict(list)
        
        # Metric definitions
        self.metric_definitions = {
            # Scraping metrics
            "scraping_success_rate": {
                "type": "gauge",
                "description": "Percentage of successful scraping attempts",
                "unit": "percentage"
            },
            "products_scraped_total": {
                "type": "counter", 
                "description": "Total number of products scraped",
                "unit": "count"
            },
            "reviews_scraped_total": {
                "type": "counter",
                "description": "Total number of reviews scraped", 
                "unit": "count"
            },
            "pricing_updates_total": {
                "type": "counter",
                "description": "Total number of pricing updates",
                "unit": "count"
            },
            
            # Quality metrics
            "data_quality_score": {
                "type": "gauge",
                "description": "Average data quality score",
                "unit": "score"
            },
            "duplicate_rate": {
                "type": "gauge", 
                "description": "Percentage of duplicate records",
                "unit": "percentage"
            },
            "validation_failure_rate": {
                "type": "gauge",
                "description": "Percentage of validation failures",
                "unit": "percentage"
            },
            
            # Performance metrics
            "request_latency": {
                "type": "histogram",
                "description": "HTTP request latency",
                "unit": "seconds"
            },
            "processing_time": {
                "type": "histogram",
                "description": "Data processing time",
                "unit": "seconds"
            },
            "memory_usage": {
                "type": "gauge",
                "description": "Memory usage",
                "unit": "MB"
            },
            
            # System metrics
            "active_jobs": {
                "type": "gauge",
                "description": "Number of active scraping jobs",
                "unit": "count"
            },
            "queue_size": {
                "type": "gauge",
                "description": "Number of jobs in queue",
                "unit": "count"
            },
            "error_rate": {
                "type": "gauge",
                "description": "System error rate",
                "unit": "percentage"
            }
        }
    
    def increment_counter(self, metric_name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric."""
        key = self._make_metric_key(metric_name, labels)
        self.counters[key] += value
        
        self._record_metric(metric_name, value, "counter", labels)
    
    def set_gauge(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value."""
        key = self._make_metric_key(metric_name, labels)
        self.gauges[key] = value
        
        self._record_metric(metric_name, value, "gauge", labels)
    
    def record_timer(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Record a timer metric value."""
        key = self._make_metric_key(metric_name, labels)
        self.timers[key].append(value)
        
        # Keep only recent values
        if len(self.timers[key]) > 100:
            self.timers[key] = self.timers[key][-100:]
        
        self._record_metric(metric_name, value, "timer", labels)
    
    def _make_metric_key(self, metric_name: str, labels: Dict[str, str] = None) -> str:
        """Create a unique key for the metric."""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{metric_name}{{label_str}}"
        return metric_name
    
    def _record_metric(self, name: str, value: Any, metric_type: str, labels: Dict[str, str] = None):
        """Record metric to buffer."""
        metric_record = {
            "timestamp": datetime.utcnow(),
            "name": name,
            "value": value,
            "type": metric_type,
            "labels": labels or {}
        }
        
        self.metrics_buffer.append(metric_record)
    
    def get_counter_value(self, metric_name: str, labels: Dict[str, str] = None) -> int:
        """Get current counter value."""
        key = self._make_metric_key(metric_name, labels)
        return self.counters.get(key, 0)
    
    def get_gauge_value(self, metric_name: str, labels: Dict[str, str] = None) -> float:
        """Get current gauge value."""
        key = self._make_metric_key(metric_name, labels)
        return self.gauges.get(key, 0.0)
    
    def get_timer_stats(self, metric_name: str, labels: Dict[str, str] = None) -> Dict[str, float]:
        """Get timer statistics."""
        key = self._make_metric_key(metric_name, labels)
        values = self.timers.get(key, [])
        
        if not values:
            return {"count": 0, "avg": 0, "min": 0, "max": 0}
        
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "p95": sorted(values)[int(len(values) * 0.95)] if len(values) > 20 else max(values)
        }
    
    def collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            import psutil
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.set_gauge("memory_usage", memory.used / 1024 / 1024)  # MB
            self.set_gauge("memory_usage_percentage", memory.percent)
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.set_gauge("cpu_usage_percentage", cpu_percent)
            
        except ImportError:
            # psutil not available, skip system metrics
            pass
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    def collect_scraping_metrics(self):
        """Collect scraping-specific metrics from database."""
        try:
            # Get recent jobs from database
            # This would typically query the scraping_jobs table
            # For now, set placeholder values
            
            self.set_gauge("active_jobs", 3)
            self.set_gauge("queue_size", 5)
            self.set_gauge("scraping_success_rate", 95.5)
            
        except Exception as e:
            self.logger.error(f"Failed to collect scraping metrics: {e}")
    
    def collect_quality_metrics(self):
        """Collect data quality metrics."""
        try:
            # Get recent quality scores
            quality_data = self.local_db.get_unprocessed_data("quality_scores", 100)
            
            if quality_data:
                avg_quality = sum(q["overall_score"] for q in quality_data) / len(quality_data)
                self.set_gauge("data_quality_score", avg_quality)
                
                # Calculate validation failure rate
                low_quality_count = sum(1 for q in quality_data if q["overall_score"] < 0.7)
                failure_rate = (low_quality_count / len(quality_data)) * 100
                self.set_gauge("validation_failure_rate", failure_rate)
            
        except Exception as e:
            self.logger.error(f"Failed to collect quality metrics: {e}")
    
    def collect_all_metrics(self):
        """Collect all available metrics."""
        self.collect_system_metrics()
        self.collect_scraping_metrics()
        self.collect_quality_metrics()
        
        self.logger.debug("Metrics collection completed")
    
    def export_metrics(self, format: str = "csv", output_file: str = None) -> str:
        """Export metrics to file."""
        if not output_file:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_file = f"metrics_{timestamp}.{format}"
        
        # Ensure output directory exists
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if format.lower() == "csv":
                return self._export_csv(output_file)
            elif format.lower() == "json":
                return self._export_json(output_file)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            self.logger.error(f"Failed to export metrics: {e}")
            return ""
    
    def _export_csv(self, output_file: str) -> str:
        """Export metrics to CSV format."""
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow(["Timestamp", "Metric", "Value", "Type", "Labels"])
            
            # Write metrics from buffer
            for metric in self.metrics_buffer:
                labels_str = json.dumps(metric["labels"]) if metric["labels"] else ""
                writer.writerow([
                    metric["timestamp"].isoformat(),
                    metric["name"],
                    metric["value"],
                    metric["type"],
                    labels_str
                ])
        
        self.logger.info(f"Metrics exported to CSV: {output_file}")
        return output_file
    
    def _export_json(self, output_file: str) -> str:
        """Export metrics to JSON format."""
        metrics_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "metrics": [
                {
                    "timestamp": m["timestamp"].isoformat(),
                    "name": m["name"],
                    "value": m["value"],
                    "type": m["type"],
                    "labels": m["labels"]
                }
                for m in self.metrics_buffer
            ],
            "current_counters": dict(self.counters),
            "current_gauges": dict(self.gauges),
            "timer_stats": {
                k: self.get_timer_stats(k.split("{")[0]) 
                for k in self.timers.keys()
            }
        }
        
        with open(output_file, 'w') as jsonfile:
            json.dump(metrics_data, jsonfile, indent=2, default=str)
        
        self.logger.info(f"Metrics exported to JSON: {output_file}")
        return output_file
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics."""
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "timer_stats": {
                name: self.get_timer_stats(name.split("{")[0])
                for name in self.timers.keys()
            },
            "buffer_size": len(self.metrics_buffer),
            "last_updated": datetime.utcnow().isoformat()
        }


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self):
        self.logger = loggers["monitoring"]
        self.metrics_collector = MetricsCollector()
        
        # Alert rules
        self.alert_rules = {
            "high_error_rate": {
                "metric": "error_rate",
                "threshold": 10.0,
                "operator": ">",
                "severity": "HIGH",
                "message": "Error rate is above threshold"
            },
            "low_success_rate": {
                "metric": "scraping_success_rate", 
                "threshold": 90.0,
                "operator": "<",
                "severity": "MEDIUM",
                "message": "Scraping success rate is low"
            },
            "high_memory_usage": {
                "metric": "memory_usage_percentage",
                "threshold": 80.0,
                "operator": ">",
                "severity": "MEDIUM",
                "message": "Memory usage is high"
            },
            "low_data_quality": {
                "metric": "data_quality_score",
                "threshold": 0.7,
                "operator": "<",
                "severity": "HIGH", 
                "message": "Data quality score is below threshold"
            }
        }
        
        # Active alerts tracking
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check all alert rules and return active alerts."""
        current_alerts = []
        
        for rule_name, rule in self.alert_rules.items():
            try:
                # Get current metric value
                metric_value = self.metrics_collector.get_gauge_value(rule["metric"])
                
                # Check condition
                is_alerting = self._evaluate_condition(
                    metric_value, rule["threshold"], rule["operator"]
                )
                
                if is_alerting:
                    alert = {
                        "rule_name": rule_name,
                        "metric": rule["metric"],
                        "current_value": metric_value,
                        "threshold": rule["threshold"],
                        "severity": rule["severity"],
                        "message": rule["message"],
                        "timestamp": datetime.utcnow()
                    }
                    
                    current_alerts.append(alert)
                    
                    # Track if this is a new alert
                    if rule_name not in self.active_alerts:
                        self.active_alerts[rule_name] = alert
                        self.alert_history.append(alert)
                        self.logger.warning(f"NEW ALERT: {rule_name} - {rule['message']}")
                
                else:
                    # Clear alert if it was active
                    if rule_name in self.active_alerts:
                        resolved_alert = self.active_alerts.pop(rule_name)
                        resolved_alert["resolved_at"] = datetime.utcnow()
                        self.alert_history.append(resolved_alert)
                        self.logger.info(f"RESOLVED: {rule_name}")
                        
            except Exception as e:
                self.logger.error(f"Failed to check alert rule {rule_name}: {e}")
        
        return current_alerts
    
    def _evaluate_condition(self, value: float, threshold: float, operator: str) -> bool:
        """Evaluate alert condition."""
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return value == threshold
        elif operator == "!=":
            return value != threshold
        else:
            return False
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts."""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alert history."""
        return list(self.alert_history)[-limit:]
    
    def add_custom_alert_rule(self, name: str, rule: Dict[str, Any]):
        """Add a custom alert rule."""
        required_fields = ["metric", "threshold", "operator", "severity", "message"]
        
        if all(field in rule for field in required_fields):
            self.alert_rules[name] = rule
            self.logger.info(f"Added custom alert rule: {name}")
        else:
            raise ValueError(f"Alert rule missing required fields: {required_fields}")


# Global instances
metrics_collector = MetricsCollector()
alert_manager = AlertManager()