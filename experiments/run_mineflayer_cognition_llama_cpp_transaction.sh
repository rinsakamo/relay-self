#!/usr/bin/env bash
set -euo pipefail

exec python3 -B -m experiments.mineflayer_cognition_llama_cpp_transaction "$@"
