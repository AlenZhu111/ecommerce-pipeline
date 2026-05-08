from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config.pipeline_config import RAW_SAMPLE_FILE, RAW_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a smaller sample from a large Kaggle CSV.")
    parser.add_argument("--input", required=True, help="Path to a Kaggle CSV, for example data/raw/2019-Oct.csv")
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--output", default=str(RAW_SAMPLE_FILE))
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    sample = pd.read_csv(args.input, nrows=args.rows)
    sample.to_csv(args.output, index=False)
    print(f"Wrote {len(sample):,} sampled rows to {args.output}")


if __name__ == "__main__":
    main()
