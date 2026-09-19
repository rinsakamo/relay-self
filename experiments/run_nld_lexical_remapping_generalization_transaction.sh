#!/usr/bin/env bash
set -euo pipefail
exec python3 -B -m experiments.nld_lexical_remapping_generalization_transaction "$@"
