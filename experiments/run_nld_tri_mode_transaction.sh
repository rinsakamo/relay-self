#!/usr/bin/env bash
set -euo pipefail

exec python3 -B -m experiments.nld_tri_mode_transaction "$@"
