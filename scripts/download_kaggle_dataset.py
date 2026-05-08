from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config.pipeline_config import RAW_DIR


DATASET = "mkechinov/ecommerce-behavior-data-from-multi-category-store"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the Kaggle e-commerce behavior dataset.")
    parser.add_argument("--dataset", default=DATASET)
    parser.add_argument("--output-dir", default=str(RAW_DIR))
    parser.add_argument("--unzip", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    command = [
        "kaggle",
        "datasets",
        "download",
        "-d",
        args.dataset,
        "-p",
        str(output_dir),
    ]
    if args.unzip:
        command.append("--unzip")

    subprocess.run(command, check=True)
    print(f"Downloaded {args.dataset} into {output_dir}")


if __name__ == "__main__":
    main()
