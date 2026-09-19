#!/usr/bin/env bash
set -euo pipefail

exec python3 -B -m experiments.nld_gemma_cross_substrate_transaction "$@"
