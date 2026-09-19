#!/usr/bin/env bash
set -euo pipefail

exec python3 -B -m experiments.nld_adequate_cost_surface_transaction "$@"
