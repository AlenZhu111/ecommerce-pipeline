from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config.pipeline_config import KAGGLE_DEFAULT_FILE, RAW_DIR, RAW_SAMPLE_FILE
from scripts.generate_sample_data import build_events


KAGGLE_DATASET = "mkechinov/ecommerce-behavior-data-from-multi-category-store"


def download_kaggle_dataset(dataset: str) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.setdefault("KAGGLE_CONFIG_DIR", str(project_root / ".kaggle"))
    env.setdefault("KAGGLE_API_TOKEN", str(Path.home() / ".kaggle" / "access_token"))
    kaggle_executable = shutil.which("kaggle") or str(Path(sys.executable).resolve().parent / "kaggle")
    if not Path(kaggle_executable).exists():
        raise FileNotFoundError(
            "Kaggle CLI was not found. Activate the virtual environment and install it with "
            "`pip install kaggle==2.1.2`, then rerun this command."
        )

    command = [
        kaggle_executable,
        "datasets",
        "download",
        "--file",
        "2019-Oct.csv",
        "-d",
        dataset,
        "-p",
        str(RAW_DIR),
        "--unzip",
    ]
    subprocess.run(command, check=True, env=env)


def prepare_generated(rows: int, seed: int, output: Path) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df = build_events(rows, seed)
    df.to_csv(output, index=False)
    print(f"Wrote {len(df):,} generated rows to {output}")


def prepare_kaggle(rows: int, source_file: Path, output: Path, dataset: str) -> None:
    zip_file = source_file.with_suffix(source_file.suffix + ".zip")
    if not source_file.exists():
        if zip_file.exists():
            print(f"{source_file} not found. Sampling directly from {zip_file}...")
        else:
            print(f"{source_file} not found. Downloading Kaggle dataset {dataset}...")
            download_kaggle_dataset(dataset)

    if not source_file.exists() and not zip_file.exists():
        raise FileNotFoundError(
            f"Expected Kaggle CSV at {source_file} or zip at {zip_file}. If the dataset file name changed, "
            "pass --kaggle-file with the downloaded CSV path."
        )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if source_file.exists():
        sample = pd.read_csv(source_file, nrows=rows)
        source_label = str(source_file)
    else:
        sample = pd.read_csv(zip_file, compression="zip", nrows=rows)
        source_label = str(zip_file)

    sample.to_csv(output, index=False)
    print(f"Wrote {len(sample):,} Kaggle rows from {source_label} to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare raw input from generated or Kaggle data.")
    parser.add_argument("--source", choices=["generated", "kaggle"], default="generated")
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=RAW_SAMPLE_FILE)
    parser.add_argument("--kaggle-file", type=Path, default=KAGGLE_DEFAULT_FILE)
    parser.add_argument("--kaggle-dataset", default=KAGGLE_DATASET)
    args = parser.parse_args()

    if args.source == "generated":
        prepare_generated(args.rows, args.seed, args.output)
    else:
        prepare_kaggle(args.rows, args.kaggle_file, args.output, args.kaggle_dataset)


if __name__ == "__main__":
    main()
