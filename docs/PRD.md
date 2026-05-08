# Product Requirements Document: E-Commerce Event Data Pipeline

## 1. Overview

This project is a personal data engineering project that builds a local-to-cloud e-commerce event analytics pipeline using Airflow, PySpark, Kaggle data, and an AWS-ready S3 architecture.

The pipeline ingests e-commerce user behavior events, injects controlled bad records for testing, validates data quality, cleans raw events, writes curated Parquet data, and creates analytics-ready tables for business reporting.

The project also demonstrates responsible use of GenAI tools during development: architecture planning, code scaffolding, debugging, data quality rule design, and documentation support, with all generated outputs manually validated through pipeline runs and row-count checks.

## 2. Problem Statement

E-commerce platforms generate large volumes of user behavior events such as product views, cart actions, and purchases. Raw event data often contains quality issues, including duplicates, missing identifiers, invalid event types, bad timestamps, and inconsistent values.

Analytics teams need a reliable pipeline that can:

- Ingest raw event data from a realistic source
- Detect and report data quality issues
- Clean and standardize event records
- Store analytics-ready data efficiently
- Produce business metrics such as revenue, conversion behavior, and product performance
- Run locally for development and move cleanly to AWS infrastructure

## 3. Goals

- Build an end-to-end data pipeline using Airflow and PySpark.
- Use real Kaggle e-commerce event data as the primary dataset.
- Support generated sample data for fast local testing.
- Inject controlled bad records to prove data quality checks work.
- Store cleaned data and analytics outputs in Parquet format.
- Make the pipeline portable from local development to EC2 and S3.
- Produce clear verification reports for development and operational validation.
- Document the project so the architecture, data flow, and trade-offs are easy to understand.

## 4. Non-Goals

- This project does not build a production-grade distributed Spark cluster.
- It does not use managed AWS services such as Glue, EMR, or MWAA in v1.
- It does not build a full BI dashboard in v1.
- It does not process the full Kaggle dataset by default; v1 uses a configurable sample size.
- It does not implement real-time streaming with Kafka in v1.

## 5. Target Users

- **Data Engineer / Developer:** runs and maintains the pipeline.
- **Data Analyst / Business User:** consumes analytics tables for reporting.
- **Project Reviewer:** evaluates data engineering design, implementation, testing, and trade-off reasoning.

## 6. Dataset

Primary dataset:

```text
Kaggle: mkechinov/ecommerce-behavior-data-from-multi-category-store
File: 2019-Oct.csv
```

Expected source columns:

```text
event_time
event_type
product_id
category_id
category_code
brand
price
user_id
user_session
```

Supported input modes:

- `generated`: creates synthetic e-commerce events for local testing.
- `kaggle`: samples rows from the real Kaggle CSV.

## 7. Functional Requirements

### FR1: Input Preparation

The system must support two input sources:

- Generated data using `scripts/prepare_input_data.py --source generated`
- Kaggle data using `scripts/prepare_input_data.py --source kaggle`

The prepared input must be written to:

```text
data/raw/ecommerce_events_sample.csv
```

### FR2: Controlled Bad Record Injection

The system must append known invalid records to the raw sample.

Bad record types must include:

- Missing `event_time`
- Missing `user_id`
- Missing or empty `user_session`
- Invalid `event_type`
- Negative `price`
- Future timestamp
- Duplicate records

Output:

```text
data/corrupted/ecommerce_events_with_bad_records.csv
```

### FR3: Data Quality Checks

The Spark quality job must calculate:

- Total rows
- Missing event time rows
- Missing user ID rows
- Missing session rows
- Invalid event type rows
- Negative price rows
- Future event timestamp rows
- Duplicate rows
- Estimated valid and invalid row counts

Output:

```text
reports/data_quality_report.json
```

### FR4: Event Cleaning

The Spark cleaning job must:

- Parse `event_time` into timestamp format
- Cast numeric fields to correct types
- Standardize missing `brand` and `category_code`
- Filter invalid event types
- Filter negative prices
- Filter missing user IDs
- Filter missing or empty sessions
- Remove duplicate events
- Add `event_date`
- Write curated Parquet output partitioned by `event_date`

Output:

```text
data/curated/events/
```

### FR5: Analytics Aggregation

The Spark aggregation job must create:

- Daily metrics
- Product/category/brand metrics

Daily metrics must include:

- Event count
- Active users
- Views
- Carts
- Purchases
- Revenue
- View-to-purchase rate

Product metrics must include:

- Category code
- Brand
- Event count
- Unique users
- Purchases
- Revenue

Outputs:

```text
data/analytics/daily_metrics/
data/analytics/product_metrics/
```

### FR6: Output Verification

The system must produce a verification report containing:

- Curated event row count
- Daily metric row count
- Product metric row count

Output:

```text
reports/output_verification_report.json
```

### FR7: Airflow Orchestration

Airflow must orchestrate the pipeline in this order:

```text
prepare_input_data
  -> inject_bad_records
  -> run_data_quality_checks
  -> clean_events
  -> aggregate_events
  -> verify_outputs
```

The DAG must support these environment variables:

```text
PIPELINE_SOURCE=generated|kaggle
PIPELINE_ROWS=100000
KAGGLE_API_TOKEN=.kaggle/access_token
PROJECT_ROOT=<project path>
JAVA_HOME=<jdk path>
SPARK_HOME=<pyspark path>
SPARK_SUBMIT=<spark-submit path>
PYTHON_BIN=<python path>
```

### FR8: AWS EC2/S3 Readiness

The project must include scripts and documentation to:

- Prepare EC2 with Java, Python, Spark dependencies, and AWS CLI
- Upload raw and corrupted CSV files to S3
- Run Spark jobs against S3 paths
- Write curated and analytics Parquet outputs to S3
- Copy reports back to S3

## 8. Non-Functional Requirements

- **Portability:** The same Spark jobs must run locally and on EC2.
- **Reproducibility:** Pipeline runs must produce JSON reports for validation.
- **Scalability:** The design must support larger Kaggle samples by changing row count.
- **Observability:** Airflow task status and JSON reports must make failures easy to diagnose.
- **Cost Control:** v1 should use sampled data and EC2/S3 rather than always-on managed services.
- **Security:** Kaggle access tokens must not be committed to Git.

## 9. System Architecture

```text
Kaggle 2019-Oct.csv or generated events
  -> data/raw/ecommerce_events_sample.csv
  -> data/corrupted/ecommerce_events_with_bad_records.csv
  -> Airflow DAG
  -> PySpark data quality checks
  -> PySpark cleaning
  -> curated Parquet events
  -> analytics Parquet tables
  -> JSON verification reports
```

AWS target architecture:

```text
EC2
  - Airflow
  - PySpark
  - project code

S3
  - raw/
  - corrupted/
  - curated/events/
  - analytics/daily_metrics/
  - analytics/product_metrics/
  - reports/
```

## 10. Success Metrics

The project is successful when:

- The local generated-data DAG run succeeds.
- The Kaggle-data DAG run succeeds.
- `data_quality_report.json` correctly identifies injected quality issues.
- `output_verification_report.json` confirms curated and analytics outputs exist.
- Curated data is stored in Parquet.
- The project can be explained clearly using data engineering trade-offs.

Current verified Kaggle sample result:

```json
{
  "curated_event_rows": 99983,
  "daily_metric_rows": 1,
  "product_metric_rows": 2661
}
```

## 11. Edge Cases

- Kaggle token is missing or expired.
- Kaggle CSV has not been extracted from ZIP.
- Input file does not exist.
- Spark cannot find Java.
- Airflow uses the wrong Python or Spark binary.
- Duplicate events already exist in Kaggle sample before injected duplicates.
- First N Kaggle rows may come from one day only, producing one daily metric row.
- S3 credentials are missing or EC2 role lacks permissions.

## 12. Testing Plan

### Local Tests

- Run generated data preparation.
- Run Kaggle data preparation.
- Run bad record injection.
- Run local smoke test.
- Run each Spark job manually.
- Run full Airflow DAG with `PIPELINE_SOURCE=generated`.
- Run full Airflow DAG with `PIPELINE_SOURCE=kaggle`.

### Data Quality Tests

Validate report includes expected issue categories:

- Missing timestamp
- Missing user ID
- Missing session
- Invalid event type
- Negative price
- Future timestamp
- Duplicates

### Output Tests

Validate:

- Curated Parquet path exists.
- Daily metrics Parquet path exists.
- Product metrics Parquet path exists.
- Verification report contains non-zero row counts.

### AWS Tests

On EC2:

- Verify `aws sts get-caller-identity`.
- Upload raw and corrupted data to S3.
- Run Spark jobs against S3.
- Confirm curated and analytics S3 prefixes contain Parquet files.
- Confirm reports are uploaded to S3.

## 13. Future Enhancements

- Sample Kaggle rows across multiple days instead of first N rows.
- Add Athena external table definitions.
- Add a Streamlit dashboard for daily and product metrics.
- Add Great Expectations or AWS Glue Data Quality.
- Add Kafka ingestion for streaming simulation.
- Add dbt models for analytics transformations.
- Add CI checks for Python scripts.
- Add AWS Glue, EMR, or MWAA comparison as production architecture.

## 14. Project Talking Points

- The pipeline was validated locally first, then designed to run on EC2 and S3.
- Generated data is used for controlled testing, while Kaggle data provides realistic event behavior.
- Bad records are injected deliberately to validate quality checks.
- Airflow handles orchestration and PySpark handles scalable transformation.
- Parquet is used because it is more efficient for analytics than CSV.
- GenAI tools can support design, debugging, and documentation, but outputs should be validated through tests and pipeline runs.
- A production version could use AWS Glue for serverless ETL, EMR for managed Spark clusters, and MWAA for managed Airflow.
