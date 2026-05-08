from __future__ import annotations

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("ecommerce-aggregate-events")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def aggregate_events(input_path: str, output_path: str) -> None:
    spark = build_spark()
    events = spark.read.parquet(input_path)

    daily = (
        events.groupBy("event_date")
        .agg(
            F.count("*").alias("event_count"),
            F.countDistinct("user_id").alias("active_users"),
            F.sum(F.when(F.col("event_type") == "view", 1).otherwise(0)).alias("views"),
            F.sum(F.when(F.col("event_type") == "cart", 1).otherwise(0)).alias("carts"),
            F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("purchases"),
            F.sum(F.when(F.col("event_type") == "purchase", F.col("price")).otherwise(0)).alias("revenue"),
        )
        .withColumn(
            "view_to_purchase_rate",
            F.when(F.col("views") > 0, F.col("purchases") / F.col("views")).otherwise(F.lit(0.0)),
        )
    )

    product = (
        events.groupBy("category_code", "brand")
        .agg(
            F.count("*").alias("event_count"),
            F.countDistinct("user_id").alias("unique_users"),
            F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("purchases"),
            F.sum(F.when(F.col("event_type") == "purchase", F.col("price")).otherwise(0)).alias("revenue"),
        )
        .orderBy(F.desc("revenue"))
    )

    daily.write.mode("overwrite").parquet(f"{output_path}/daily_metrics")
    product.write.mode("overwrite").parquet(f"{output_path}/product_metrics")
    spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create analytics tables from clean events.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    aggregate_events(args.input, args.output)


if __name__ == "__main__":
    main()
