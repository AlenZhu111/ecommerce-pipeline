#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: scripts/run_pipeline_s3.sh s3://your-bucket/prefix" >&2
  exit 1
fi

S3_PREFIX="${1%/}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${PROJECT_ROOT}"
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
export SPARK_HOME="${SPARK_HOME:-${PROJECT_ROOT}/.venv/lib/python3.12/site-packages/pyspark}"

SPARK_SUBMIT="${SPARK_SUBMIT:-${PROJECT_ROOT}/.venv/bin/spark-submit}"
S3A_PACKAGES="${S3A_PACKAGES:-org.apache.hadoop:hadoop-aws:3.3.4}"
SPARK_S3_CONF=(
  --packages "${S3A_PACKAGES}"
  --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem
  --conf spark.hadoop.fs.s3a.aws.credentials.provider=com.amazonaws.auth.DefaultAWSCredentialsProviderChain
)

"${SPARK_SUBMIT}" "${SPARK_S3_CONF[@]}" "${PROJECT_ROOT}/spark_jobs/data_quality_checks.py" \
  --input "${S3_PREFIX}/corrupted/ecommerce_events_with_bad_records.csv" \
  --report "${PROJECT_ROOT}/reports/data_quality_report.json"

aws s3 cp "${PROJECT_ROOT}/reports/data_quality_report.json" "${S3_PREFIX}/reports/data_quality_report.json"

"${SPARK_SUBMIT}" "${SPARK_S3_CONF[@]}" "${PROJECT_ROOT}/spark_jobs/clean_events.py" \
  --input "${S3_PREFIX}/corrupted/ecommerce_events_with_bad_records.csv" \
  --output "${S3_PREFIX}/curated/events"

"${SPARK_SUBMIT}" "${SPARK_S3_CONF[@]}" "${PROJECT_ROOT}/spark_jobs/aggregate_events.py" \
  --input "${S3_PREFIX}/curated/events" \
  --output "${S3_PREFIX}/analytics"

"${SPARK_SUBMIT}" "${SPARK_S3_CONF[@]}" "${PROJECT_ROOT}/spark_jobs/verify_outputs.py" \
  --curated "${S3_PREFIX}/curated/events" \
  --analytics "${S3_PREFIX}/analytics" \
  --report "${PROJECT_ROOT}/reports/output_verification_report.json"

aws s3 cp "${PROJECT_ROOT}/reports/output_verification_report.json" "${S3_PREFIX}/reports/output_verification_report.json"
