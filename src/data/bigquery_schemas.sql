-- BigQuery table schemas for the e-commerce scraping system

-- Products table
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset_id}.products` (
  product_id STRING NOT NULL,
  site STRING NOT NULL,
  name STRING NOT NULL,
  category STRING,
  brand STRING,
  url STRING NOT NULL,
  description STRING,
  specifications JSON,
  images ARRAY<STRING>,
  in_stock BOOLEAN,
  scraped_at TIMESTAMP,
  last_updated TIMESTAMP
)
PARTITION BY DATE(scraped_at)
CLUSTER BY site, category;

-- Reviews table
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset_id}.reviews` (
  review_id STRING NOT NULL,
  product_id STRING NOT NULL,
  site STRING NOT NULL,
  title STRING,
  content STRING NOT NULL,
  rating FLOAT64 NOT NULL,
  reviewer_name STRING,
  verified_purchase BOOLEAN,
  review_date TIMESTAMP,
  scraped_at TIMESTAMP
)
PARTITION BY DATE(scraped_at)
CLUSTER BY site, product_id;

-- Pricing table
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset_id}.pricing` (
  price_id STRING NOT NULL,
  product_id STRING NOT NULL,
  site STRING NOT NULL,
  current_price FLOAT64 NOT NULL,
  original_price FLOAT64,
  currency STRING DEFAULT 'INR',
  discount_percentage FLOAT64,
  discount_amount FLOAT64,
  offers ARRAY<STRING>,
  price_date TIMESTAMP,
  scraped_at TIMESTAMP
)
PARTITION BY DATE(price_date)
CLUSTER BY site, product_id;

-- Quality scores table
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset_id}.quality_scores` (
  record_id STRING NOT NULL,
  record_type STRING NOT NULL,
  completeness_score FLOAT64 NOT NULL,
  accuracy_score FLOAT64 NOT NULL,
  consistency_score FLOAT64 NOT NULL,
  overall_score FLOAT64 NOT NULL,
  issues ARRAY<STRING>,
  evaluated_at TIMESTAMP
)
PARTITION BY DATE(evaluated_at)
CLUSTER BY record_type;

-- Scraping jobs table
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset_id}.scraping_jobs` (
  job_id STRING NOT NULL,
  site STRING NOT NULL,
  job_type STRING NOT NULL,
  category STRING,
  search_terms ARRAY<STRING>,
  max_pages INT64,
  status STRING DEFAULT 'pending',
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  products_scraped INT64 DEFAULT 0,
  reviews_scraped INT64 DEFAULT 0,
  errors ARRAY<STRING>,
  created_at TIMESTAMP
)
PARTITION BY DATE(created_at)
CLUSTER BY site, status;

-- Analytics views

-- Product price trends view
CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.product_price_trends` AS
SELECT 
  p.product_id,
  p.name,
  p.brand,
  p.category,
  p.site,
  pr.current_price,
  pr.original_price,
  pr.discount_percentage,
  pr.price_date,
  LAG(pr.current_price) OVER (
    PARTITION BY p.product_id 
    ORDER BY pr.price_date
  ) AS previous_price,
  pr.current_price - LAG(pr.current_price) OVER (
    PARTITION BY p.product_id 
    ORDER BY pr.price_date
  ) AS price_change
FROM `{project_id}.{dataset_id}.products` p
JOIN `{project_id}.{dataset_id}.pricing` pr ON p.product_id = pr.product_id
WHERE pr.price_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY);

-- Product review summary view
CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.product_review_summary` AS
SELECT 
  p.product_id,
  p.name,
  p.brand,
  p.category,
  p.site,
  COUNT(r.review_id) as total_reviews,
  AVG(r.rating) as avg_rating,
  COUNTIF(r.verified_purchase = TRUE) as verified_reviews,
  COUNTIF(r.rating >= 4.0) as positive_reviews,
  COUNTIF(r.rating <= 2.0) as negative_reviews,
  MAX(r.review_date) as latest_review_date
FROM `{project_id}.{dataset_id}.products` p
LEFT JOIN `{project_id}.{dataset_id}.reviews` r ON p.product_id = r.product_id
GROUP BY p.product_id, p.name, p.brand, p.category, p.site;

-- Daily scraping summary view
CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.daily_scraping_summary` AS
SELECT 
  DATE(scraped_at) as scrape_date,
  site,
  COUNT(DISTINCT product_id) as products_scraped,
  COUNT(DISTINCT CASE WHEN in_stock = TRUE THEN product_id END) as in_stock_products,
  AVG(CASE WHEN specifications IS NOT NULL THEN 1 ELSE 0 END) as spec_completeness,
  AVG(CASE WHEN description IS NOT NULL AND LENGTH(description) > 10 THEN 1 ELSE 0 END) as desc_completeness
FROM `{project_id}.{dataset_id}.products`
WHERE scraped_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY DATE(scraped_at), site
ORDER BY scrape_date DESC, site;

-- Quality score summary view
CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.quality_summary` AS
SELECT 
  record_type,
  DATE(evaluated_at) as evaluation_date,
  COUNT(*) as total_records,
  AVG(overall_score) as avg_overall_score,
  AVG(completeness_score) as avg_completeness,
  AVG(accuracy_score) as avg_accuracy,
  AVG(consistency_score) as avg_consistency,
  COUNTIF(overall_score >= 0.8) as high_quality_records,
  COUNTIF(overall_score < 0.5) as low_quality_records
FROM `{project_id}.{dataset_id}.quality_scores`
WHERE evaluated_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY record_type, DATE(evaluated_at)
ORDER BY evaluation_date DESC, record_type;

-- Site comparison view
CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.site_comparison` AS
SELECT 
  site,
  category,
  COUNT(DISTINCT product_id) as total_products,
  AVG(current_price) as avg_current_price,
  AVG(discount_percentage) as avg_discount,
  COUNT(DISTINCT r.review_id) as total_reviews,
  AVG(r.rating) as avg_rating
FROM `{project_id}.{dataset_id}.products` p
LEFT JOIN `{project_id}.{dataset_id}.pricing` pr ON p.product_id = pr.product_id
LEFT JOIN `{project_id}.{dataset_id}.reviews` r ON p.product_id = r.product_id
WHERE p.scraped_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND (pr.price_date IS NULL OR pr.price_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY))
GROUP BY site, category
ORDER BY site, category;