from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from experiments.mineflayer_cognition_llama_cpp_transaction import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    EXPECTED_GGUF_SHA256,
    PhysicalTransactionError,
    _collect_llama_revision,
    _collect_server_version,
    _port_is_free,
    _probe_and_attest,
    _require_clean_repo,
    _require_llama_cpp_paths,
    _server_command,
    _start_server,
    _terminate_owned_process,
    _verify_artifact,
    _wait_until_ready,
)
from experiments.nld_adequate_cost_surface import (
    build_cost_cases,
)
from experiments.nld_linear_spec_matched import (
    build_schedule,
)
from experiments.nld_tri_mode import (
    DEFAULT_MODEL_ID,
    parse_decision,
)
from experiments.nld_tri_mode_repeatability import _numeric_summary
from experiments.nld_tri_mode_transaction import (
    DEFAULT_TIMEOUT_SECONDS,
    _load_json,
    _prepare_evidence_root,
    _run_probe_command,
    _write_json,
)

FORMAT_VERSION = 1
GEMMA_MAX_TOKENS = 32
GEMMA_TEMPERATURE = 0
GEMMA_SEED = 1
