#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: scripts/sync_outputs_from_s3.sh s3://your-bucket/prefix" >&2
  exit 1
fi

S3_PREFIX="${1%/}"

mkdir -p data/curated data/analytics reports
aws s3 sync "${S3_PREFIX}/curated" data/curated
aws s3 sync "${S3_PREFIX}/analytics" data/analytics
aws s3 sync "${S3_PREFIX}/reports" reports
