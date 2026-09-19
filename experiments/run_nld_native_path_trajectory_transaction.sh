#!/usr/bin/env bash
set -euo pipefail
exec python3 -B -m experiments.nld_native_path_trajectory_transaction "$@"
