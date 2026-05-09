# Snowflake Warehouse Layer

This optional layer loads the final Spark analytics outputs from S3 into Snowflake tables.

The recommended design is:

```text
Spark writes Parquet analytics to S3
  -> Snowflake COPY INTO loads Parquet from S3
  -> analysts query DAILY_METRICS and PRODUCT_METRICS in Snowflake
```

S3 remains the data lake. Snowflake is the analytics warehouse.

## 1. Snowflake Objects

Create a small warehouse, database, and schema:

```sql
CREATE DATABASE IF NOT EXISTS ECOMMERCE_DB;
CREATE SCHEMA IF NOT EXISTS ECOMMERCE_DB.ANALYTICS;

CREATE WAREHOUSE IF NOT EXISTS ECOMMERCE_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;
```

Use an `XSMALL` warehouse for the project demo and keep auto-suspend enabled.

## 2. EC2 Environment Variables

Set Snowflake connection variables on EC2:

```bash
export SF_ACCOUNT="<account_identifier>"
export SF_USER="<snowflake_user>"
export SF_PASSWORD="<snowflake_password>"
export SF_DATABASE="ECOMMERCE_DB"
export SF_SCHEMA="ANALYTICS"
export SF_WAREHOUSE="ECOMMERCE_WH"
export SF_ROLE="<snowflake_role>"
```

For a production-style setup, create a Snowflake storage integration for S3 and set:

```bash
export SF_STORAGE_INTEGRATION="<storage_integration_name>"
```

For a short demo only, you can use temporary AWS credentials:

```bash
export AWS_ACCESS_KEY_ID="<aws_access_key_id>"
export AWS_SECRET_ACCESS_KEY="<aws_secret_access_key>"
export AWS_SESSION_TOKEN="<aws_session_token_if_present>"
```

Do not commit Snowflake or AWS credentials.

## 3. Manual Load

After the S3 Spark pipeline succeeds, run:

```bash
PYTHONPATH=. .venv/bin/python scripts/load_snowflake_from_s3.py \
  --s3-prefix s3://<bucket>/ecommerce-event-pipeline
```

This creates or refreshes:

```text
DAILY_METRICS
PRODUCT_METRICS
```

## 4. Airflow Load

The S3 DAG includes an optional task:

```text
load_snowflake_tables
```

It is disabled by default. To enable it in the Airflow website:

```text
Admin -> Variables -> Add
Key: ENABLE_SNOWFLAKE_LOAD
Value: true
```

Also set:

```text
Admin -> Variables -> Add
Key: S3_PREFIX
Value: s3://<bucket>/ecommerce-event-pipeline
```

Then trigger:

```text
ecommerce_event_pipeline_s3
```

The Airflow order becomes:

```text
check_s3_input
  -> run_s3_pipeline
  -> load_snowflake_tables
  -> show_verification_report
```

## 5. Validate In Snowflake

Run:

```sql
USE DATABASE ECOMMERCE_DB;
USE SCHEMA ANALYTICS;

SELECT COUNT(*) FROM DAILY_METRICS;
SELECT COUNT(*) FROM PRODUCT_METRICS;

SELECT *
FROM DAILY_METRICS
ORDER BY EVENT_DATE;
```

## 6. Interview Explanation

Use this explanation:

> I kept S3 as the data lake and added Snowflake as the analytics warehouse. Spark writes cleaned and aggregated Parquet outputs to S3, then Airflow can trigger a Snowflake COPY INTO step to load daily and product metrics into Snowflake tables. This separates low-cost storage from SQL-friendly analytics serving.
