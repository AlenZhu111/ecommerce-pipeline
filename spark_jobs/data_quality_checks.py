from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config.pipeline_config import VALID_EVENT_TYPES


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("ecommerce-data-quality")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def run_quality_checks(input_path: str, report_path: str) -> None:
    spark = build_spark()
    df = spark.read.option("header", True).option("inferSchema", True).csv(input_path)
    parsed = df.withColumn(
        "event_ts", F.to_timestamp(F.regexp_replace("event_time", " UTC$", ""), "yyyy-MM-dd HH:mm:ss")
    ).withColumn("price", F.col("price").cast("double"))

    duplicate_count = (
        parsed.groupBy("event_time", "event_type", "product_id", "price", "user_id", "user_session")
        .count()
        .filter(F.col("count") > 1)
        .agg(F.sum(F.col("count") - 1).alias("duplicate_rows"))
        .collect()[0]["duplicate_rows"]
    )

    checks = {
        "total_rows": parsed.count(),
        "missing_event_time_rows": parsed.filter(F.col("event_ts").isNull()).count(),
        "missing_user_id_rows": parsed.filter(F.col("user_id").isNull()).count(),
        "missing_user_session_rows": parsed.filter(
            F.col("user_session").isNull() | (F.trim(F.col("user_session")) == "")
        ).count(),
        "invalid_event_type_rows": parsed.filter(~F.col("event_type").isin(VALID_EVENT_TYPES)).count(),
        "negative_price_rows": parsed.filter(F.col("price") < 0).count(),
        "future_event_time_rows": parsed.filter(F.col("event_ts") > F.current_timestamp()).count(),
        "duplicate_rows": int(duplicate_count or 0),
    }

    checks["invalid_rows_estimate"] = sum(
        value for key, value in checks.items() if key not in {"total_rows", "duplicate_rows"}
    ) + checks["duplicate_rows"]
    checks["valid_rows_estimate"] = checks["total_rows"] - checks["invalid_rows_estimate"]

    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(json.dumps(checks, indent=2), encoding="utf-8")
    print(json.dumps(checks, indent=2))
    spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run data quality checks with PySpark.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    run_quality_checks(args.input, args.report)


if __name__ == "__main__":
    main()
