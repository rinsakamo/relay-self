from __future__ import annotations

import argparse
import collections
import json
import time
from dataclasses import asdict
from pathlib import Path

from experiments.nld_lexical_remapping_generalization import (
    LexicalCase,
    build_cases,
    parsed_destination,
)
from experiments.nld_tri_mode import (
    DEFAULT_MAX_THINKING_TOKENS,
    DEFAULT_MODEL_ID,
    DEFAULT_MODES,
    DEFAULT_SEED,
    _cuda_memory_snapshot,
    _import_runtime,
    _nfe_value,
    _prepare_prompt,
    _reset_seed,
    _torch_dtype,
    dispatch_generation,
    mode_arguments,
    parse_decision,
)
from experiments.nld_tri_mode_repeatability import (
    MODE_PERMUTATIONS,
    _numeric_summary,
)

DEFAULT_DTYPE = "bf16"
DEFAULT_MAX_NEW_TOKENS = 32
