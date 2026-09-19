from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from experiments.nld_adequate_cost_surface import (
    DEFAULT_DTYPE,
    DEFAULT_MAX_NEW_TOKENS,
    _run_observation,
    build_cost_cases,
)
from experiments.nld_tri_mode import (
    DEFAULT_MAX_THINKING_TOKENS,
    DEFAULT_MODEL_ID,
    DEFAULT_SEED,
    _cuda_memory_snapshot,
    _import_runtime,
    _prepare_prompt,
    _torch_dtype,
)
from experiments.nld_tri_mode_repeatability import _numeric_summary

MODE = "linear_spec"
CASE_ORDERS = (
    (0, 1, 2, 3),
    (3, 2, 1, 0),
    (1, 2, 3, 0),
    (2, 3, 0, 1),
    (0, 3, 2, 1),
    (1, 0, 3, 2),
)
