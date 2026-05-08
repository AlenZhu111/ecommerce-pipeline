from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config.pipeline_config import CORRUPTED_FILE, QUALITY_REPORT_FILE, VALID_EVENT_TYPES


def main() -> None:
    df = pd.read_csv(CORRUPTED_FILE)
    parsed_time = pd.to_datetime(df["event_time"].str.replace(" UTC", "", regex=False), errors="coerce")

    duplicate_cols = ["event_time", "event_type", "product_id", "price", "user_id", "user_session"]
    report = {
        "total_rows": int(len(df)),
        "missing_event_time_rows": int(parsed_time.isna().sum()),
        "missing_user_id_rows": int(df["user_id"].isna().sum()),
        "missing_user_session_rows": int((df["user_session"].fillna("").str.strip() == "").sum()),
        "invalid_event_type_rows": int((~df["event_type"].isin(VALID_EVENT_TYPES)).sum()),
        "negative_price_rows": int((pd.to_numeric(df["price"], errors="coerce") < 0).sum()),
        "duplicate_rows": int(df.duplicated(subset=duplicate_cols).sum()),
    }

    Path(QUALITY_REPORT_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(QUALITY_REPORT_FILE).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
