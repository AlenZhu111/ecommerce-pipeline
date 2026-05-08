from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config.pipeline_config import RAW_SAMPLE_FILE, RAW_DIR, VALID_EVENT_TYPES


CATEGORIES = [
    ("electronics.smartphone", "apple"),
    ("electronics.smartphone", "samsung"),
    ("electronics.audio.headphone", "sony"),
    ("electronics.laptop", "lenovo"),
    ("appliances.kitchen.kettle", "xiaomi"),
    ("computers.notebook", "asus"),
]


def build_events(rows: int, seed: int) -> pd.DataFrame:
    random.seed(seed)
    start = datetime(2019, 10, 1, tzinfo=timezone.utc)
    records = []

    for index in range(rows):
        category_code, brand = random.choice(CATEGORIES)
        event_type = random.choices(VALID_EVENT_TYPES, weights=[78, 12, 3, 7], k=1)[0]
        event_time = start + timedelta(seconds=random.randint(0, 31 * 24 * 3600 - 1))
        product_id = random.randint(100000, 999999)
        category_id = random.randint(2000000000, 2999999999)
        user_id = random.randint(10000000, 99999999)
        session_id = f"s{user_id}-{random.randint(1, 50)}"
        base_price = random.uniform(8, 1500)

        records.append(
            {
                "event_time": event_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "event_type": event_type,
                "product_id": product_id,
                "category_id": category_id,
                "category_code": category_code,
                "brand": brand,
                "price": round(base_price, 2),
                "user_id": user_id,
                "user_session": session_id,
            }
        )

    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a local e-commerce event sample.")
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default=str(RAW_SAMPLE_FILE))
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df = build_events(args.rows, args.seed)
    df.to_csv(args.output, index=False)
    print(f"Wrote {len(df):,} rows to {args.output}")


if __name__ == "__main__":
    main()
