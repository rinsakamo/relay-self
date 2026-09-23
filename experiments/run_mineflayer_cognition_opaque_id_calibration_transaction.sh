#!/usr/bin/env bash
set -euo pipefail

exec python3 -B -m experiments.mineflayer_cognition_opaque_id_calibration_transaction "$@"
