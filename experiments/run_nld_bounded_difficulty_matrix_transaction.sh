#!/usr/bin/env bash
set -euo pipefail

exec python3 -B -m experiments.nld_bounded_difficulty_matrix_transaction "$@"
