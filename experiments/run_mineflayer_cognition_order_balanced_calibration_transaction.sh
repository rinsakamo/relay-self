#!/usr/bin/env bash
set -euo pipefail

exec python3 -B -m experiments.mineflayer_cognition_order_balanced_calibration_transaction "$@"
