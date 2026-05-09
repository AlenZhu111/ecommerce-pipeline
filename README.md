# E-Commerce Event Data Pipeline

This project is an e-commerce event data pipeline using Airflow for orchestration, PySpark for distributed processing, and S3-ready folder conventions for raw, curated, and analytics data.

## Architecture

```text
Kaggle or generated event data
  -> raw CSV
  -> synthetic bad records
  -> Airflow DAG
  -> PySpark data quality checks
  -> PySpark cleaning
  -> curated Parquet
  -> analytics Parquet tables
```

## Local Quick Start

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you installed Java with Homebrew on macOS, use this environment when running Spark or Airflow:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export SPARK_HOME="$(python -c 'import pathlib, pyspark; print(pathlib.Path(pyspark.__file__).parent)')"
export PYTHONPATH="$(pwd)"
```

Generate a local sample and inject data quality issues:

```bash
PYTHONPATH=. python scripts/generate_sample_data.py --rows 100000
PYTHONPATH=. python scripts/inject_bad_records.py
```

Run the Spark jobs:

```bash
PYTHONPATH=. spark-submit spark_jobs/data_quality_checks.py \
  --input data/corrupted/ecommerce_events_with_bad_records.csv \
  --report reports/data_quality_report.json

PYTHONPATH=. spark-submit spark_jobs/clean_events.py \
  --input data/corrupted/ecommerce_events_with_bad_records.csv \
  --output data/curated/events

PYTHONPATH=. spark-submit spark_jobs/aggregate_events.py \
  --input data/curated/events \
  --output data/analytics

PYTHONPATH=. spark-submit spark_jobs/verify_outputs.py \
  --curated data/curated/events \
  --analytics data/analytics \
  --report reports/output_verification_report.json
```

## Kaggle Dataset

Recommended dataset:

```text
mkechinov/ecommerce-behavior-data-from-multi-category-store
```

Install and configure Kaggle with the access-token method:

```bash
pip install kaggle==2.1.2
mkdir -p ~/.kaggle
echo "<your-kaggle-access-token>" > ~/.kaggle/access_token
chmod 600 ~/.kaggle/access_token
export KAGGLE_API_TOKEN="$HOME/.kaggle/access_token"
```

Do not commit or share the real token. If a token appears in a screenshot, repository, or public note, revoke it and create a new one.

Then run:

```bash
PYTHONPATH=. python scripts/download_kaggle_dataset.py --unzip
```

For the first version of the project, use a sample of one CSV file rather than the full dataset.

If you download `2019-Oct.csv`, create the pipeline input sample from the project root:

```bash
cd /path/to/ecommerce-event-pipeline
PYTHONPATH=. python scripts/prepare_input_data.py --source kaggle --rows 100000
PYTHONPATH=. python scripts/inject_bad_records.py
```

You can also run the Airflow DAG with Kaggle input:

```bash
export PIPELINE_SOURCE=kaggle
export PIPELINE_ROWS=100000
airflow dags test ecommerce_event_pipeline 2026-05-08
```

## Smoke Test Without Spark

If Spark is not installed yet, validate the generated input and quality logic with:

```bash
python scripts/generate_sample_data.py --rows 10000
python scripts/inject_bad_records.py
python scripts/local_smoke_test.py
```

## Airflow Local Test

Initialize a project-local Airflow metadata database:

```bash
export AIRFLOW_HOME="$(pwd)/airflow_home"
export AIRFLOW__CORE__DAGS_FOLDER="$(pwd)/dags"
export AIRFLOW__CORE__LOAD_EXAMPLES=False
airflow db migrate
```

Run the DAG end to end:

```bash
export PROJECT_ROOT="$(pwd)"
export PYTHON_BIN="$(pwd)/.venv/bin/python"
export SPARK_SUBMIT="$(pwd)/.venv/bin/spark-submit"
airflow dags test ecommerce_event_pipeline 2026-05-08
```

If using the Airflow web UI, verify the webserver first:

```bash
curl -I http://localhost:8080
```

`HTTP 302` with `Location: /home` is healthy. If the UI opens but shows zero DAGs, confirm `AIRFLOW__CORE__DAGS_FOLDER` points to the project `dags/` folder.

## AWS EC2 + S3 Version

For detailed EC2/S3 instructions, see [docs/EC2_S3_RUNBOOK.md](docs/EC2_S3_RUNBOOK.md).

For the optional Snowflake warehouse layer, see [docs/SNOWFLAKE_LAYER.md](docs/SNOWFLAKE_LAYER.md).

On EC2, install Java, Python, Spark, Airflow, and AWS CLI. Store data in S3 using this layout:

```text
s3://<bucket>/raw/events/
s3://<bucket>/corrupted/events/
s3://<bucket>/curated/events/
s3://<bucket>/analytics/
s3://<bucket>/reports/
```

Then replace local paths in the Spark commands with S3 paths.

## GenAI Usage Story

Use GenAI tools to help with architecture planning, initial PySpark and Airflow drafts, data quality rule brainstorming, debugging, and documentation. Always validate generated code by running the pipeline and checking the outputs.
