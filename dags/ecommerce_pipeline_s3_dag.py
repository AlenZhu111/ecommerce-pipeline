from __future__ import annotations

import os
import pathlib
import shlex
from datetime import datetime

from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator


PROJECT_ROOT = os.environ.get("PROJECT_ROOT", "/home/ubuntu/ecommerce-pipeline")
JAVA_HOME = os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-17-openjdk-amd64")
S3_PREFIX = (os.environ.get("S3_PREFIX") or Variable.get("S3_PREFIX", default_var="")).rstrip("/")
ENABLE_SNOWFLAKE_LOAD = (
    os.environ.get("ENABLE_SNOWFLAKE_LOAD")
    or Variable.get("ENABLE_SNOWFLAKE_LOAD", default_var="false")
).lower()


def default_spark_home() -> str:
    try:
        import pyspark

        return str(pathlib.Path(pyspark.__file__).parent)
    except ImportError:
        return f"{PROJECT_ROOT}/.venv/lib/python3.12/site-packages/pyspark"


SPARK_HOME = os.environ.get("SPARK_HOME", default_spark_home())
COMMAND_ENV = (
    f"PROJECT_ROOT={shlex.quote(PROJECT_ROOT)} "
    f"JAVA_HOME={shlex.quote(JAVA_HOME)} "
    f"SPARK_HOME={shlex.quote(SPARK_HOME)} "
    f"PYTHONPATH={shlex.quote(PROJECT_ROOT)}"
)
S3_PREFIX_ARG = shlex.quote(S3_PREFIX)
PROJECT_ROOT_ARG = shlex.quote(PROJECT_ROOT)
REQUIRE_S3_PREFIX = (
    f"test -n {S3_PREFIX_ARG} || "
    '(echo "Set S3_PREFIX as an environment variable or Airflow Variable." >&2; exit 1)'
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
            f"{REQUIRE_S3_PREFIX} && "
            f"aws s3 ls {S3_PREFIX_ARG}/corrupted/ecommerce_events_with_bad_records.csv"
        ),
    )

    run_s3_pipeline = BashOperator(
        task_id="run_s3_pipeline",
        bash_command=(
            f"{REQUIRE_S3_PREFIX} && "
            f"cd {PROJECT_ROOT_ARG} && "
            f"{COMMAND_ENV} "
            f"{PROJECT_ROOT_ARG}/scripts/run_pipeline_s3.sh {S3_PREFIX_ARG}"
        ),
    )

    show_verification_report = BashOperator(
        task_id="show_verification_report",
        bash_command=(
            f"{REQUIRE_S3_PREFIX} && "
            f"aws s3 cp {S3_PREFIX_ARG}/reports/output_verification_report.json -"
        ),
    )

    load_snowflake_tables = BashOperator(
        task_id="load_snowflake_tables",
        bash_command=(
            f"if [ {shlex.quote(ENABLE_SNOWFLAKE_LOAD)} != true ]; then "
            'echo "Snowflake load disabled. Set ENABLE_SNOWFLAKE_LOAD=true to enable."; exit 0; '
            f"fi && {REQUIRE_S3_PREFIX} && "
            f"cd {PROJECT_ROOT_ARG} && "
            f"{COMMAND_ENV} "
            f"{PROJECT_ROOT_ARG}/.venv/bin/python "
            f"{PROJECT_ROOT_ARG}/scripts/load_snowflake_from_s3.py --s3-prefix {S3_PREFIX_ARG}"
        ),
    )

    check_s3_input >> run_s3_pipeline >> load_snowflake_tables >> show_verification_report
