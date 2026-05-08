from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config.pipeline_config import CORRUPTED_FILE, CORRUPTED_DIR, RAW_SAMPLE_FILE


BAD_RECORDS = [
    {
        "event_time": "2019-10-01 10:00:00 UTC",
        "event_type": "purchase",
        "product_id": 1001,
        "category_id": 2001,
        "category_code": "electronics.smartphone",
        "brand": "apple",
        "price": -999.0,
        "user_id": 12345,
        "user_session": "bad-negative-price",
    },
    {
        "event_time": "2019-10-01 10:05:00 UTC",
        "event_type": "click_wrong",
        "product_id": 1002,
        "category_id": 2002,
        "category_code": "electronics.laptop",
        "brand": "lenovo",
        "price": 800.0,
        "user_id": 12346,
        "user_session": "bad-event-type",
    },
    {
        "event_time": "",
        "event_type": "purchase",
        "product_id": 1003,
        "category_id": 2003,
        "category_code": "electronics.audio",
        "brand": "sony",
        "price": 120.0,
        "user_id": 12347,
        "user_session": "bad-missing-time",
    },
    {
        "event_time": "2019-10-01 10:10:00 UTC",
        "event_type": "cart",
        "product_id": 1004,
        "category_id": 2004,
        "category_code": "electronics.tablet",
        "brand": "samsung",
        "price": 300.0,
        "user_id": "",
        "user_session": "bad-missing-user",
    },
    {
        "event_time": "2035-01-01 00:00:00 UTC",
        "event_type": "view",
        "product_id": 1005,
        "category_id": 2005,
        "category_code": "electronics.camera",
        "brand": "canon",
        "price": 550.0,
        "user_id": 12348,
        "user_session": "",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Append controlled bad records for quality testing.")
    parser.add_argument("--input", default=str(RAW_SAMPLE_FILE))
    parser.add_argument("--output", default=str(CORRUPTED_FILE))
    parser.add_argument("--duplicate-rows", type=int, default=25)
    args = parser.parse_args()

    CORRUPTED_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.input)
    duplicates = df.head(args.duplicate_rows)
    bad = pd.DataFrame(BAD_RECORDS)
    output = pd.concat([df, duplicates, bad], ignore_index=True)
    output.to_csv(args.output, index=False)
    print(f"Wrote {len(output):,} rows to {args.output}")
    print(f"Injected {len(duplicates):,} duplicates and {len(bad):,} bad records")


if __name__ == "__main__":
    main()
