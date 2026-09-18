#!/usr/bin/env bash
set -euo pipefail

exec python3 -B -m experiments.nld_easy_permutation_isolation_transaction "$@"
