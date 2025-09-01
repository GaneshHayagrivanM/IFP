# Indian E-commerce Focused Pipeline (IFP)

A comprehensive web scraping system for collecting product data, reviews, and pricing information from Indian e-commerce platforms (Amazon.in, Flipkart, Myntra) while respecting ethical guidelines, budget constraints, and performance targets.

## 🚀 Features

### Core Functionality
- **Multi-site Scraping**: Amazon.in, Flipkart, and Myntra support
- **Comprehensive Data Extraction**: Products, reviews, pricing, and specifications
- **Ethical Compliance**: Robots.txt compliance, rate limiting, privacy protection
- **Quality Assurance**: Data validation, deduplication, quality scoring
- **Performance Optimization**: Memory management for e2-micro VM constraints

### Technical Highlights
- **Rate Limiting**: Max 1 request per 2 seconds per domain
- **Data Validation**: 95%+ completeness targets with quality scoring
- **Storage Architecture**: Cloud Storage + SQLite + BigQuery
- **Monitoring**: Comprehensive metrics and alerting
- **Scalable Design**: Batch processing with job scheduling

## 📁 Project Structure

```
src/
├── scrapers/           # Scraping engine
│   ├── base_scraper.py    # Common scraper interface
│   ├── amazon_scraper.py  # Amazon.in implementation
│   ├── flipkart_scraper.py # Flipkart implementation
│   ├── myntra_scraper.py   # Myntra implementation
│   └── utils/             # Scraper utilities
├── data/               # Data management
│   ├── models.py          # Pydantic data models
│   ├── validation.py      # Quality validation
│   ├── storage.py         # Storage management
│   └── bigquery_schemas.sql # BigQuery table schemas
├── pipeline/           # Processing pipeline
│   ├── scheduler.py       # Job scheduling
│   ├── processor.py       # Data processing
│   └── quality_check.py   # Quality monitoring
├── monitoring/         # Observability
│   ├── metrics.py         # Metrics collection
│   └── reporting.py       # Report generation
├── config/            # Configuration
│   ├── settings.py        # Application settings
│   └── logging_config.py  # Logging setup
├── tests/             # Test suite
├── docker/            # Container configuration
└── main.py           # Application entry point
```

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- Google Cloud Platform account
- Docker (optional)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd IFP
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Google Cloud Setup**
   ```bash
   # Set up authentication
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
   export GCP_PROJECT_ID="your-project-id"
   export GCP_STORAGE_BUCKET="your-bucket-name"
   ```

## 🚀 Usage

### Command Line Interface

```bash
# Start the full scraping system
python -m src.main start

# Run a single scraping job
python -m src.main job --site amazon --job-type discovery --category electronics

# Generate reports
python -m src.main report --report-type daily

# Run quality checks
python -m src.main quality-check

# Test the system
python -m src.main test
```

### Docker Deployment

```bash
# Build and run with Docker Compose
cd src/docker
docker-compose up -d

# View logs
docker-compose logs -f scraper

# Stop the system
docker-compose down
```

## 📊 Data Models

### Product Data
```python
{
    "product_id": "unique_identifier",
    "site": "amazon|flipkart|myntra",
    "name": "Product Name",
    "category": "electronics|clothing|home-kitchen|books|sports",
    "brand": "Brand Name",
    "url": "product_url",
    "description": "Product description",
    "specifications": {"key": "value"},
    "images": ["image_urls"],
    "in_stock": true,
    "scraped_at": "2024-01-01T00:00:00Z"
}
```

### Review Data
```python
{
    "review_id": "unique_identifier",
    "product_id": "associated_product_id",
    "site": "amazon|flipkart|myntra",
    "title": "Review title",
    "content": "Review content",
    "rating": 4.5,
    "reviewer_name": "A***r", # Anonymized
    "verified_purchase": true,
    "review_date": "2024-01-01T00:00:00Z"
}
```

### Pricing Data
```python
{
    "price_id": "unique_identifier",
    "product_id": "associated_product_id", 
    "site": "amazon|flipkart|myntra",
    "current_price": 1000.0,
    "original_price": 1200.0,
    "currency": "INR",
    "discount_percentage": 16.67,
    "offers": ["offer_descriptions"],
    "price_date": "2024-01-01T00:00:00Z"
}
```

## 🎯 Quality Assurance

### Data Validation Framework
- **Completeness**: >95% of required fields populated
- **Accuracy**: Format validation, range checks
- **Consistency**: Cross-field validation, temporal checks
- **Deduplication**: <5% duplicate rate target

### Quality Scoring
Each record receives scores for:
- Completeness (0-1)
- Accuracy (0-1) 
- Consistency (0-1)
- Overall Score (average)

## 📈 Monitoring & Reporting

### Key Metrics
- **Scraping Success Rate**: >99% target
- **Data Quality Score**: >0.8 target
- **Processing Time**: <5 minutes per batch
- **Memory Usage**: <800MB on e2-micro
- **Cost Tracking**: ₹1,515/month budget

### Reports Available
- **Daily Summary**: Scraping stats, quality metrics
- **Weekly Report**: Trends, performance analysis
- **Cost Report**: Budget utilization, optimization suggestions
- **Quality Dashboard**: Real-time quality monitoring

## 💰 Cost Management

### Budget Allocation (₹1,515/month)
- **Cloud Storage**: ₹324/month
- **BigQuery**: ₹415/month  
- **Compute (e2-micro)**: ₹150/month
- **Buffer**: ₹626/month

### Optimization Features
- Partitioned BigQuery tables
- Data lifecycle policies
- Batch processing
- Query cost monitoring

## 🔒 Ethical Compliance

### Privacy Protection
- **No Personal Data**: Only public product information
- **Reviewer Anonymization**: Names masked (A***r format)
- **No Account Creation**: Public data access only

### Respectful Scraping
- **Robots.txt Compliance**: Automatic checking
- **Rate Limiting**: 1 request per 2 seconds maximum
- **Error Handling**: Graceful failure recovery
- **Resource Management**: Memory-efficient processing

## 🧪 Testing

```bash
# Run basic tests
python src/tests/test_basic.py

# Run with pytest (if available)
pytest src/tests/

# Test specific components
python -c "from src.scrapers import AmazonScraper; print('Scrapers OK')"
python -c "from src.data.validation import DataValidator; print('Validation OK')"
```

## 📝 Configuration

### Environment Variables
```bash
# Google Cloud
GCP_PROJECT_ID=your-project-id
GCP_STORAGE_BUCKET=your-bucket-name
BIGQUERY_DATASET=ecommerce_data

# Application Settings
MAX_REQUESTS_PER_SECOND=0.5
BATCH_SIZE=100
LOCAL_DB_PATH=data/local.db
```

### Logging Configuration
- **Levels**: DEBUG, INFO, WARNING, ERROR
- **Output**: Console + File (optional)
- **Format**: Timestamp, Logger, Level, Message

## 🚨 Troubleshooting

### Common Issues

1. **Memory Issues on e2-micro**
   ```bash
   # Reduce batch size
   export BATCH_SIZE=50
   ```

2. **Rate Limiting Errors**
   ```bash
   # Increase delay between requests
   export MAX_REQUESTS_PER_SECOND=0.3
   ```

3. **BigQuery Quota Exceeded**
   ```bash
   # Check query costs in monitoring
   python -m src.main report --report-type cost
   ```

### Monitoring Health
```bash
# Check system status
curl http://localhost:8080/health

# View recent alerts
python -c "
from src.monitoring.metrics import alert_manager
print(alert_manager.get_active_alerts())
"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built for ethical data collection from Indian e-commerce platforms
- Designed with budget constraints and performance optimization in mind
- Implements best practices for web scraping and data quality

---

**Note**: This system is designed for educational and research purposes. Always respect website terms of service and robots.txt files when scraping data.
