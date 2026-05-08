#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3-pip openjdk-17-jdk unzip git

python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install awscli==1.32.116

echo "EC2 setup complete."
echo "Set AWS credentials with an instance role or aws configure, then run scripts/run_pipeline_s3.sh."
