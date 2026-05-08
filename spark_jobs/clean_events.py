from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config.pipeline_config import VALID_EVENT_TYPES


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("ecommerce-clean-events")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def clean_events(input_path: str, output_path: str) -> None:
    spark = build_spark()
    valid_event_types = [F.lit(event_type) for event_type in VALID_EVENT_TYPES]

    raw = spark.read.option("header", True).option("inferSchema", True).csv(input_path)

    cleaned = (
        raw.withColumn("event_time_clean", F.regexp_replace("event_time", " UTC$", ""))
        .withColumn("event_ts", F.to_timestamp("event_time_clean", "yyyy-MM-dd HH:mm:ss"))
        .withColumn("price", F.col("price").cast("double"))
        .withColumn("user_id", F.col("user_id").cast("long"))
        .withColumn("product_id", F.col("product_id").cast("long"))
        .withColumn("category_id", F.col("category_id").cast("long"))
        .withColumn("brand", F.coalesce(F.col("brand"), F.lit("unknown")))
        .withColumn("category_code", F.coalesce(F.col("category_code"), F.lit("unknown")))
        .drop("event_time_clean")
    )

    valid = (
        cleaned.filter(F.col("event_ts").isNotNull())
        .filter(F.col("event_type").isin(VALID_EVENT_TYPES))
        .filter(F.col("price") >= 0)
        .filter(F.col("user_id").isNotNull())
        .filter(F.col("user_session").isNotNull())
        .filter(F.trim(F.col("user_session")) != "")
        .dropDuplicates(
            ["event_time", "event_type", "product_id", "price", "user_id", "user_session"]
        )
        .withColumn("event_date", F.to_date("event_ts"))
    )

    valid.write.mode("overwrite").partitionBy("event_date").parquet(output_path)
    spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean e-commerce event data with PySpark.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    clean_events(args.input, args.output)


if __name__ == "__main__":
    main()
