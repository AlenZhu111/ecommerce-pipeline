from __future__ import annotations

import argparse
import os
import re
from urllib.parse import urlparse


DAILY_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS DAILY_METRICS (
    EVENT_DATE DATE,
    EVENT_COUNT NUMBER,
    ACTIVE_USERS NUMBER,
    VIEWS NUMBER,
    CARTS NUMBER,
    PURCHASES NUMBER,
    REVENUE FLOAT,
    VIEW_TO_PURCHASE_RATE FLOAT
)
"""

PRODUCT_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS PRODUCT_METRICS (
    CATEGORY_CODE VARCHAR,
    BRAND VARCHAR,
    EVENT_COUNT NUMBER,
    UNIQUE_USERS NUMBER,
    PURCHASES NUMBER,
    REVENUE FLOAT
)
"""


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def snowflake_connection():
    try:
        import snowflake.connector
    except ImportError as exc:
        raise RuntimeError(
            "Missing Snowflake Python connector. Install it with "
            "`pip install snowflake-connector-python`."
        ) from exc

    connection_kwargs = {
        "account": require_env("SF_ACCOUNT"),
        "user": require_env("SF_USER"),
        "warehouse": require_env("SF_WAREHOUSE"),
        "database": require_env("SF_DATABASE"),
        "schema": require_env("SF_SCHEMA"),
    }
    if os.environ.get("SF_ROLE"):
        connection_kwargs["role"] = os.environ["SF_ROLE"]

    if os.environ.get("SF_PASSWORD"):
        connection_kwargs["password"] = os.environ["SF_PASSWORD"]
    else:
        raise RuntimeError("Set SF_PASSWORD for this demo load, or extend the script for key-pair auth.")

    return snowflake.connector.connect(**connection_kwargs)


def s3_url_join(prefix: str, *parts: str) -> str:
    return "/".join([prefix.rstrip("/"), *[part.strip("/") for part in parts]])


def stage_credentials_clause() -> str:
    integration = os.environ.get("SF_STORAGE_INTEGRATION")
    if integration:
        return f"STORAGE_INTEGRATION = {integration}"

    key_id = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    session_token = os.environ.get("AWS_SESSION_TOKEN")
    if key_id and secret_key:
        credentials = f"AWS_KEY_ID = '{key_id}' AWS_SECRET_KEY = '{secret_key}'"
        if session_token:
            credentials += f" AWS_TOKEN = '{session_token}'"
        return f"CREDENTIALS = ({credentials})"

    raise RuntimeError(
        "Snowflake needs access to S3. Set SF_STORAGE_INTEGRATION for a production-style "
        "external stage, or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY for a short demo."
    )


def validate_s3_prefix(s3_prefix: str) -> None:
    parsed = urlparse(s3_prefix)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError("--s3-prefix must look like s3://bucket/prefix")


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_identifier(name: str, label: str) -> None:
    if not IDENTIFIER_PATTERN.fullmatch(name):
        raise ValueError(f"{label} must be an unquoted Snowflake identifier, got: {name!r}")


def execute(cursor, sql: str, *, log_sql: bool = True) -> None:
    if log_sql:
        print(sql)
    cursor.execute(sql)


def load_snowflake_tables(s3_prefix: str, stage_name: str) -> None:
    validate_s3_prefix(s3_prefix)
    validate_identifier(stage_name, "stage_name")
    analytics_url = s3_url_join(s3_prefix, "analytics")
    credentials_clause = stage_credentials_clause()

    with snowflake_connection() as conn:
        with conn.cursor() as cursor:
            execute(cursor, DAILY_TABLE_DDL)
            execute(cursor, PRODUCT_TABLE_DDL)
            execute(cursor, "CREATE FILE FORMAT IF NOT EXISTS PARQUET_FORMAT TYPE = PARQUET")
            execute(
                cursor,
                f"""
CREATE STAGE IF NOT EXISTS {stage_name}
    URL = '{analytics_url}'
    {credentials_clause}
    FILE_FORMAT = PARQUET_FORMAT
""",
                log_sql=False,
            )
            execute(cursor, "TRUNCATE TABLE DAILY_METRICS")
            execute(cursor, "TRUNCATE TABLE PRODUCT_METRICS")
            execute(
                cursor,
                f"""
COPY INTO DAILY_METRICS
FROM @{stage_name}/daily_metrics/
FILE_FORMAT = (TYPE = PARQUET)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
""",
            )
            execute(
                cursor,
                f"""
COPY INTO PRODUCT_METRICS
FROM @{stage_name}/product_metrics/
FILE_FORMAT = (TYPE = PARQUET)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
""",
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Load analytics Parquet outputs from S3 into Snowflake.")
    parser.add_argument("--s3-prefix", required=True, help="Example: s3://bucket/ecommerce-event-pipeline")
    parser.add_argument("--stage-name", default=os.environ.get("SF_STAGE", "ECOMMERCE_ANALYTICS_STAGE"))
    args = parser.parse_args()
    load_snowflake_tables(args.s3_prefix, args.stage_name)


if __name__ == "__main__":
    main()
