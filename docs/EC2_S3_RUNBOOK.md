# EC2 and S3 Runbook

This runbook moves the e-commerce event pipeline to AWS using EC2 as the compute environment and S3 as the data lake.

It reflects the practiced low-cost workflow:

```text
Kaggle zip on EC2
  -> 1000-row raw CSV
  -> injected bad-record CSV
  -> upload raw/corrupted CSVs to S3
  -> Spark reads S3 corrupted layer
  -> Spark writes curated/analytics/reports to S3
  -> optional Airflow DAG orchestrates the S3 pipeline
```

## 1. Recommended EC2 Choice

Use Ubuntu 24.04.

For manual Spark testing only, `t3.micro` can work with a 1000-row sample and swap enabled. For Airflow plus Spark, use `t3.small` at minimum.

```text
t3.micro:  2 vCPU, 1 GiB memory, okay for manual 1000-row Spark demo
t3.small:  2 vCPU, 2 GiB memory, better minimum for Airflow demo
t3.medium: 2 vCPU, 4 GiB memory, smoother for Airflow and larger samples
```

If using `t3.micro` or `t3.small`, add swap:

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
free -h
```

## 2. S3 Layout

Create an S3 bucket or choose an existing bucket:

```text
s3://<bucket>/ecommerce-event-pipeline
```

Recommended layout:

```text
s3://<bucket>/ecommerce-event-pipeline/raw/
s3://<bucket>/ecommerce-event-pipeline/corrupted/
s3://<bucket>/ecommerce-event-pipeline/curated/events/
s3://<bucket>/ecommerce-event-pipeline/analytics/daily_metrics/
s3://<bucket>/ecommerce-event-pipeline/analytics/product_metrics/
s3://<bucket>/ecommerce-event-pipeline/reports/
```

Attach an IAM role to EC2 with read/write permission to this prefix. If you do not use an IAM role, configure AWS CLI credentials:

```bash
aws configure
aws sts get-caller-identity
```

## 3. Project Setup On EC2

Set key permissions and connect to the instance:

```bash
chmod 400 ~/Downloads/<your-ec2-key>.pem
ssh -i ~/Downloads/<your-ec2-key>.pem ubuntu@<ec2-public-ip>
```

Replace `<your-ec2-key>.pem` with your key-pair file and `<ec2-public-ip>` with the EC2 public IPv4 address.

Clone or copy the project onto EC2, then enter the project folder:

```bash
cd /home/ubuntu/ecommerce-pipeline
```

If the instance is not set up yet, run the helper script once. It installs system packages, creates `.venv`, installs Python dependencies, and installs AWS CLI:

```bash
chmod +x scripts/*.sh
scripts/setup_ec2_ubuntu.sh
```

If you already installed dependencies manually, skip the setup script and only activate the environment:

```bash
source .venv/bin/activate
```

Set the core environment:

```bash
export PROJECT_ROOT="$(pwd)"
export PYTHONPATH="$(pwd)"
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export SPARK_HOME="$(python -c 'import pathlib, pyspark; print(pathlib.Path(pyspark.__file__).parent)')"
```

Check Spark home:

```bash
echo "$SPARK_HOME"
test -x "$SPARK_HOME/bin/spark-class"
```

The `SPARK_HOME` path must end with:

```text
site-packages/pyspark
```

Do not use a wildcard path such as `python3.*`.

## 4. Kaggle Authentication

Use the newer access-token method:

```bash
mkdir -p ~/.kaggle
echo "<your-kaggle-access-token>" > ~/.kaggle/access_token
chmod 600 ~/.kaggle/access_token
export KAGGLE_API_TOKEN="$HOME/.kaggle/access_token"
```

Do not commit or share the real token. If a token appears in a screenshot, repository, or public note, revoke it and create a new one.

Check the Kaggle CLI:

```bash
which kaggle
kaggle datasets list -s ecommerce
```

If `kaggle` is missing:

```bash
pip install kaggle==2.1.2
```

## 5. Create A 1000-Row Kaggle Sample

On small EC2 instances, do not extract the full Kaggle CSV. Download the zip and sample directly from it.

Download the Kaggle file:

```bash
mkdir -p data/raw

kaggle datasets download \
  --file 2019-Oct.csv \
  -d mkechinov/ecommerce-behavior-data-from-multi-category-store \
  -p data/raw
```

This creates:

```text
data/raw/2019-Oct.csv.zip
```

Sample 1000 rows into the project's default raw filename:

```bash
PYTHONPATH=. .venv/bin/python -c "import pandas as pd; pd.read_csv('data/raw/2019-Oct.csv.zip', compression='zip', nrows=1000).to_csv('data/raw/ecommerce_events_sample.csv', index=False)"
```

Inject controlled bad records:

```bash
PYTHONPATH=. .venv/bin/python scripts/inject_bad_records.py
```

Expected row counts:

```bash
wc -l data/raw/ecommerce_events_sample.csv
wc -l data/corrupted/ecommerce_events_with_bad_records.csv
```

Expected output:

```text
1001 data/raw/ecommerce_events_sample.csv
1031 data/corrupted/ecommerce_events_with_bad_records.csv
```

Why `1031` lines? It is:

```text
1000 data rows
+ 25 duplicate rows
+ 5 bad records
+ 1 header line
= 1031 lines
```

If you instead create `data/raw/ecommerce_events.csv`, pass it explicitly:

```bash
PYTHONPATH=. .venv/bin/python scripts/inject_bad_records.py \
  --input data/raw/ecommerce_events.csv \
  --output data/corrupted/ecommerce_events_with_bad_records.csv
```

## 6. Upload Raw And Corrupted Data To S3

Upload after the local row counts are correct:

```bash
scripts/sync_raw_to_s3.sh s3://<bucket>/ecommerce-event-pipeline
```

This uploads:

```text
data/raw/*.csv        -> s3://<bucket>/ecommerce-event-pipeline/raw/
data/corrupted/*.csv  -> s3://<bucket>/ecommerce-event-pipeline/corrupted/
```

Verify:

```bash
aws s3 ls s3://<bucket>/ecommerce-event-pipeline/raw/
aws s3 ls s3://<bucket>/ecommerce-event-pipeline/corrupted/
```

## 7. Run Spark Against S3 Manually

Once raw and corrupted data are already in S3, run:

```bash
scripts/run_pipeline_s3.sh s3://<bucket>/ecommerce-event-pipeline
```

This script does not upload raw data again. It reads:

```text
s3://<bucket>/ecommerce-event-pipeline/corrupted/ecommerce_events_with_bad_records.csv
```

Then it writes:

```text
s3://<bucket>/ecommerce-event-pipeline/curated/events/
s3://<bucket>/ecommerce-event-pipeline/analytics/daily_metrics/
s3://<bucket>/ecommerce-event-pipeline/analytics/product_metrics/
s3://<bucket>/ecommerce-event-pipeline/reports/data_quality_report.json
s3://<bucket>/ecommerce-event-pipeline/reports/output_verification_report.json
```

The script accepts an `s3://` path for convenience and converts Spark input/output paths to `s3a://` internally. AWS CLI commands still use `s3://`.

## 8. Run The S3 Pipeline With Airflow

Airflow should orchestrate the S3 flow in the cloud version. Use the DAG:

```text
ecommerce_event_pipeline_s3
```

Set environment variables:

```bash
export AIRFLOW_HOME="$(pwd)/airflow"
export PROJECT_ROOT="$(pwd)"
export AIRFLOW__CORE__DAGS_FOLDER="$(pwd)/dags"
export S3_PREFIX=s3://<bucket>/ecommerce-event-pipeline
export PYTHONPATH="$(pwd)"
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export SPARK_HOME="$(python -c 'import pathlib, pyspark; print(pathlib.Path(pyspark.__file__).parent)')"
export AIRFLOW__CORE__EXECUTOR=SequentialExecutor
export AIRFLOW__CORE__LOAD_EXAMPLES=False
```

Alternatively, set `S3_PREFIX` in the Airflow website:

```text
Admin -> Variables -> Add
Key: S3_PREFIX
Value: s3://<bucket>/ecommerce-event-pipeline
```

Initialize Airflow:

```bash
airflow db migrate
airflow users create \
  --username <admin-username> \
  --firstname <first-name> \
  --lastname <last-name> \
  --role Admin \
  --email <email@example.com> \
  --password '<admin-password>'
```

Start Airflow:

```bash
airflow standalone
```

Open:

```text
http://<ec2-public-ip>:8080
```

Make sure the EC2 security group allows inbound TCP `8080` from your IP.

Trigger:

```text
ecommerce_event_pipeline_s3
```

The S3 DAG:

```text
1. checks the corrupted CSV exists in S3
2. runs scripts/run_pipeline_s3.sh
3. optionally loads analytics outputs from S3 into Snowflake
4. prints the final verification report from S3
```

For the optional Snowflake warehouse layer, see [SNOWFLAKE_LAYER.md](SNOWFLAKE_LAYER.md).

## 9. Validate Results

Check S3 outputs:

```bash
aws s3 ls s3://<bucket>/ecommerce-event-pipeline/curated/events/ --recursive
aws s3 ls s3://<bucket>/ecommerce-event-pipeline/analytics/ --recursive
aws s3 cp s3://<bucket>/ecommerce-event-pipeline/reports/output_verification_report.json -
```

For a 1000-row Kaggle sample, exact curated counts can differ because invalid rows and duplicates are removed. The important checks are:

```text
reports exist
curated Parquet exists
analytics Parquet exists
verification report has non-zero curated and analytics counts
```

## 10. Troubleshooting Notes

### Kaggle CLI Looks For /usr/bin/kaggle

Activate the virtual environment and use the venv Python:

```bash
source .venv/bin/activate
which python
which kaggle
PYTHONPATH=. .venv/bin/python scripts/prepare_input_data.py --source kaggle --rows 1000
```

### SPARK_HOME Points To The Wrong Directory

Fix:

```bash
unset SPARK_HOME
export SPARK_HOME="$(python -c 'import pathlib, pyspark; print(pathlib.Path(pyspark.__file__).parent)')"
test -x "$SPARK_HOME/bin/spark-class"
```

### Spark Says No FileSystem For Scheme s3

Spark needs `s3a://`, not `s3://`. Use `scripts/run_pipeline_s3.sh`; it converts the path internally.

### Airflow UI Opens But Shows Zero DAGs

First confirm the webserver is healthy:

```bash
curl -I http://localhost:8080
```

`HTTP 302` with `Location: /home` is a healthy Airflow response. It means the webserver is running. If the DAG list is empty, Airflow is probably looking in the wrong DAG folder.

Set the project DAG folder before starting Airflow:

```bash
export AIRFLOW__CORE__DAGS_FOLDER="$(pwd)/dags"
```

Then restart Airflow and check:

```bash
airflow dags list | grep ecommerce
airflow dags list-import-errors
```

### Corrupted File Still Has 10030 Rows

The injector is probably reading the old default raw file. Use the default filename:

```text
data/raw/ecommerce_events_sample.csv
```

or pass the input explicitly:

```bash
PYTHONPATH=. .venv/bin/python scripts/inject_bad_records.py \
  --input data/raw/ecommerce_events.csv \
  --output data/corrupted/ecommerce_events_with_bad_records.csv
```

## 11. Project Explanation

Use this explanation:

> I validated the pipeline locally first, then ran the cloud version on EC2 and S3. In the cloud version, EC2 downloads and samples Kaggle data, S3 stores raw, corrupted, curated, analytics, and report layers, Spark processes the S3 data, and Airflow orchestrates the S3 pipeline. I used a 1000-row sample from real Kaggle data for a low-cost demo, injected controlled bad records to test data quality, and designed the workflow so it can scale later to larger EC2, EMR, Glue, MWAA, or Snowflake.
