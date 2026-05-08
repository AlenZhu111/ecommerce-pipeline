from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyspark.sql import SparkSession


def build_spark() -> SparkSession:
    return SparkSession.builder.appName("ecommerce-verify-outputs").getOrCreate()


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify local pipeline output row counts.")
    parser.add_argument("--curated", required=True)
    parser.add_argument("--analytics", required=True)
    parser.add_argument("--report", default="reports/output_verification_report.json")
    args = parser.parse_args()

    spark = build_spark()
    results = {
        "curated_event_rows": spark.read.parquet(args.curated).count(),
        "daily_metric_rows": spark.read.parquet(f"{args.analytics}/daily_metrics").count(),
        "product_metric_rows": spark.read.parquet(f"{args.analytics}/product_metrics").count(),
    }

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    spark.stop()


if __name__ == "__main__":
    main()
