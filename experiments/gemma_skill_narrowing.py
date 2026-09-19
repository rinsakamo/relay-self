from __future__ import annotations

import argparse
import collections
import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from adapters.llama_cpp.relay_engine import (
    parse_llama_cpp_decision,
    render_llama_cpp_request,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    DecisionStatus,
    ProviderDecision,
    RelayEngine,
)
from experiments.nld_tri_mode_repeatability import _numeric_summary

SOURCE = "gemma-skill-narrowing"
CONDITIONS = ("broad", "narrow")
ORDER_SCHEDULE = (
    ("broad", "narrow"),
    ("narrow", "broad"),
) * 3


@dataclass(frozen=True, slots=True)
class NarrowingCase:
    case_id: str
    route_cave: bool
    route_ridge: bool
    shelter_cave: bool
    shelter_ridge: bool
    expected_choice_id: str
