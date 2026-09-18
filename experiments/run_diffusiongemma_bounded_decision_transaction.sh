#!/usr/bin/env bash
set -euo pipefail

exec python3 -B -m experiments.diffusiongemma_bounded_decision_transaction "$@"
