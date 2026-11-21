#!/usr/bin/env bash
set -euo pipefail

exec python3 -B -m experiments.mineflayer_cognition_f46_successor_transaction "$@"
