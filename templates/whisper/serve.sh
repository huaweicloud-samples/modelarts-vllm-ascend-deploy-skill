#!/bin/bash
set -euo pipefail
export WEIGHT_DIR="${WEIGHT_DIR:-/weight}"
export DEVICE="${DEVICE:-npu:0}"
exec python3 /code/server.py
