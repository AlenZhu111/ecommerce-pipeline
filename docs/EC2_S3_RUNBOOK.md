# EC2 and S3 Runbook

This runbook moves the local Airflow + PySpark pipeline to AWS using EC2 as the compute environment and S3 as the data lake.

## 1. AWS Resources

Create an S3 bucket or choose an existing bucket:

```text
s3://<bucket>/ecommerce-event-pipeline
```

Recommended S3 layout:

```text
s3://<bucket>/ecommerce-event-pipeline/raw/
s3://<bucket>/ecommerce-event-pipeline/corrupted/
s3://<bucket>/ecommerce-event-pipeline/curated/events/
s3://<bucket>/ecommerce-event-pipeline/analytics/daily_metrics/
s3://<bucket>/ecommerce-event-pipeline/analytics/product_metrics/
s3://<bucket>/ecommerce-event-pipeline/reports/
```

Attach an IAM role to EC2 with read/write permission to this prefix.

## 2. EC2 Setup

Launch an Ubuntu EC2 instance. For a small development run, `t3.medium` is enough for 100k rows. Use a larger instance for the full Kaggle dataset.

Clone or copy this project onto EC2, then run:

```bash
chmod +x scripts/setup_ec2_ubuntu.sh scripts/*.sh
scripts/setup_ec2_ubuntu.sh
```

## 3. Prepare Kaggle Data

On EC2, configure Kaggle:

```bash
mkdir -p .kaggle
# Upload kaggle.json to .kaggle/kaggle.json
chmod 600 .kaggle/kaggle.json
export KAGGLE_CONFIG_DIR="$(pwd)/.kaggle"
```

For the newer Kaggle access-token method:

```bash
mkdir -p .kaggle
# Upload the token text to .kaggle/access_token
chmod 600 .kaggle/access_token
export KAGGLE_API_TOKEN="$(pwd)/.kaggle/access_token"
```

Prepare a real Kaggle sample:

```bash
source .venv/bin/activate
PYTHONPATH=. python scripts/prepare_input_data.py --source kaggle --rows 100000
PYTHONPATH=. python scripts/inject_bad_records.py
```

If Kaggle access is not ready, use generated data:

```bash
PYTHONPATH=. python scripts/prepare_input_data.py --source generated --rows 100000
PYTHONPATH=. python scripts/inject_bad_records.py
```

## 4. Upload Raw Data To S3

```bash
aws sts get-caller-identity
scripts/sync_raw_to_s3.sh s3://<bucket>/ecommerce-event-pipeline
```

## 5. Run Spark Against S3

```bash
scripts/run_pipeline_s3.sh s3://<bucket>/ecommerce-event-pipeline
```

This writes curated Parquet and analytics Parquet directly to S3.

## 6. Validate Results

```bash
aws s3 ls s3://<bucket>/ecommerce-event-pipeline/curated/events/ --recursive
aws s3 ls s3://<bucket>/ecommerce-event-pipeline/analytics/ --recursive
aws s3 cp s3://<bucket>/ecommerce-event-pipeline/reports/output_verification_report.json -
```

Expected shape for 100k prepared input rows:

```json
{
  "curated_event_rows": 100000,
  "daily_metric_rows": 31,
  "product_metric_rows": 6
}
```

For Kaggle data, row counts may differ slightly depending on the sampled file and data-quality filters.

## 7. Project Explanation

Use this explanation:

> I validated the pipeline locally first, then moved the same Spark jobs to EC2 and S3. EC2 runs the orchestration and Spark jobs, S3 stores raw, corrupted, curated, analytics, and report layers. I used generated data for controlled testing and Kaggle e-commerce data for realistic event volume.
