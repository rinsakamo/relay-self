#!/usr/bin/env bash
set -euo pipefail

exec python3 -B -m experiments.nld_reversed_mapping_token_budget_transaction "$@"
