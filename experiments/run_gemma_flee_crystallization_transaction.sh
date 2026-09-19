#!/usr/bin/env bash
set -euo pipefail

exec python3 -B -m experiments.gemma_flee_crystallization_transaction "$@"
