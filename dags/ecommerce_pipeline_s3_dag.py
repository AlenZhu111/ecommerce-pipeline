from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


PROJECT_ROOT = os.environ.get("PROJECT_ROOT", "/home/ubuntu/ecommerce-pipeline")
S3_PREFIX = os.environ.get("S3_PREFIX", "s3://s3-test-bucket-stella/ecommerce-event-pipeline").rstrip("/")
JAVA_HOME = os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-17-openjdk-amd64")
SPARK_HOME = os.environ.get("SPARK_HOME", f"{PROJECT_ROOT}/.venv/lib/python3.12/site-packages/pyspark")
COMMAND_ENV = (
    f"PROJECT_ROOT={PROJECT_ROOT} "
    f"JAVA_HOME={JAVA_HOME} "
    f"SPARK_HOME={SPARK_HOME} "
    f"PYTHONPATH={PROJECT_ROOT}"
)


with DAG(
    dag_id="ecommerce_event_pipeline_s3",
    description="Run the e-commerce Spark pipeline against S3 data.",
    start_date=datetime(2026, 5, 1),
    schedule_interval=None,
    catchup=False,
    tags=["data-engineering", "spark", "s3", "ecommerce"],
) as dag:
    check_s3_input = BashOperator(
        task_id="check_s3_input",
        bash_command=(
            f"aws s3 ls {S3_PREFIX}/corrupted/ecommerce_events_with_bad_records.csv"
        ),
    )

    run_s3_pipeline = BashOperator(
        task_id="run_s3_pipeline",
        bash_command=(
            f"cd {PROJECT_ROOT} && "
            f"{COMMAND_ENV} "
            f"{PROJECT_ROOT}/scripts/run_pipeline_s3.sh {S3_PREFIX}"
        ),
    )

    show_verification_report = BashOperator(
        task_id="show_verification_report",
        bash_command=(
            f"aws s3 cp {S3_PREFIX}/reports/output_verification_report.json -"
        ),
    )

    check_s3_input >> run_s3_pipeline >> show_verification_report
