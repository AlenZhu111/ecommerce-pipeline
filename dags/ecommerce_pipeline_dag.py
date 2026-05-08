from __future__ import annotations

import os
import pathlib
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


PROJECT_ROOT = os.environ.get("PROJECT_ROOT", "/opt/airflow/project")
PYTHON_BIN = os.environ.get("PYTHON_BIN", f"{PROJECT_ROOT}/.venv/bin/python")
SPARK_SUBMIT = os.environ.get("SPARK_SUBMIT", f"{PROJECT_ROOT}/.venv/bin/spark-submit")


def default_spark_home() -> str:
    try:
        import pyspark

        return str(pathlib.Path(pyspark.__file__).parent)
    except ImportError:
        return f"{PROJECT_ROOT}/.venv/lib/python3.12/site-packages/pyspark"


SPARK_HOME = os.environ.get("SPARK_HOME", default_spark_home())
JAVA_HOME = os.environ.get("JAVA_HOME", "/opt/homebrew/opt/openjdk@17")
COMMAND_ENV = f"JAVA_HOME={JAVA_HOME} SPARK_HOME={SPARK_HOME} PYTHONPATH={PROJECT_ROOT}"
KAGGLE_CONFIG_DIR = os.environ.get("KAGGLE_CONFIG_DIR", f"{PROJECT_ROOT}/.kaggle")
KAGGLE_API_TOKEN = os.environ.get("KAGGLE_API_TOKEN", os.path.expanduser("~/.kaggle/access_token"))
COMMAND_ENV = f"{COMMAND_ENV} KAGGLE_CONFIG_DIR={KAGGLE_CONFIG_DIR} KAGGLE_API_TOKEN={KAGGLE_API_TOKEN}"
PIPELINE_SOURCE = os.environ.get("PIPELINE_SOURCE", "generated")
PIPELINE_ROWS = os.environ.get("PIPELINE_ROWS", "100000")
KAGGLE_FILE = os.environ.get("KAGGLE_FILE", f"{PROJECT_ROOT}/data/raw/2019-Oct.csv")

RAW_INPUT = f"{PROJECT_ROOT}/data/corrupted/ecommerce_events_with_bad_records.csv"
CURATED_OUTPUT = f"{PROJECT_ROOT}/data/curated/events"
ANALYTICS_OUTPUT = f"{PROJECT_ROOT}/data/analytics"
QUALITY_REPORT = f"{PROJECT_ROOT}/reports/data_quality_report.json"
OUTPUT_VERIFICATION_REPORT = f"{PROJECT_ROOT}/reports/output_verification_report.json"


with DAG(
    dag_id="ecommerce_event_pipeline",
    description="Clean and aggregate e-commerce events with PySpark.",
    start_date=datetime(2026, 5, 1),
    schedule_interval=None,
    catchup=False,
    tags=["data-engineering", "spark", "ecommerce"],
) as dag:
    prepare_input_data = BashOperator(
        task_id="prepare_input_data",
        bash_command=(
            f"{COMMAND_ENV} {PYTHON_BIN} {PROJECT_ROOT}/scripts/prepare_input_data.py "
            f"--source {PIPELINE_SOURCE} --rows {PIPELINE_ROWS} --kaggle-file {KAGGLE_FILE}"
        ),
    )

    inject_bad_records = BashOperator(
        task_id="inject_bad_records",
        bash_command=f"{COMMAND_ENV} {PYTHON_BIN} {PROJECT_ROOT}/scripts/inject_bad_records.py",
    )

    run_quality_checks = BashOperator(
        task_id="run_data_quality_checks",
        bash_command=(
            f"{COMMAND_ENV} {SPARK_SUBMIT} {PROJECT_ROOT}/spark_jobs/data_quality_checks.py "
            f"--input {RAW_INPUT} --report {QUALITY_REPORT}"
        ),
    )

    clean_events = BashOperator(
        task_id="clean_events",
        bash_command=(
            f"{COMMAND_ENV} {SPARK_SUBMIT} {PROJECT_ROOT}/spark_jobs/clean_events.py "
            f"--input {RAW_INPUT} --output {CURATED_OUTPUT}"
        ),
    )

    aggregate_events = BashOperator(
        task_id="aggregate_events",
        bash_command=(
            f"{COMMAND_ENV} {SPARK_SUBMIT} {PROJECT_ROOT}/spark_jobs/aggregate_events.py "
            f"--input {CURATED_OUTPUT} --output {ANALYTICS_OUTPUT}"
        ),
    )

    verify_outputs = BashOperator(
        task_id="verify_outputs",
        bash_command=(
            f"{COMMAND_ENV} {SPARK_SUBMIT} {PROJECT_ROOT}/spark_jobs/verify_outputs.py "
            f"--curated {CURATED_OUTPUT} --analytics {ANALYTICS_OUTPUT} "
            f"--report {OUTPUT_VERIFICATION_REPORT}"
        ),
    )

    prepare_input_data >> inject_bad_records >> run_quality_checks >> clean_events >> aggregate_events >> verify_outputs
