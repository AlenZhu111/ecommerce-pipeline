#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: scripts/sync_raw_to_s3.sh s3://your-bucket/prefix" >&2
  exit 1
fi

S3_PREFIX="${1%/}"

aws s3 sync data/raw "${S3_PREFIX}/raw" --exclude "*" --include "*.csv"
aws s3 sync data/corrupted "${S3_PREFIX}/corrupted" --exclude "*" --include "*.csv"
