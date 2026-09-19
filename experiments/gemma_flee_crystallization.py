from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from experiments.gemma_skill_narrowing import (
    CASES,
    ObservedLlamaCppProvider,
    _condition_summary,
    _sum_numeric,
    build_request,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    DecisionStatus,
    RelayEngine,
)

SOURCE = "gemma-flee-crystallization"
ARTIFACT_ALGORITHM = "greedy_lexicographic_ablation_v1"
CONDITIONS = ("before", "after")
ORDER_SCHEDULE = (
    ("before", "after"),
    ("after", "before"),
) * 3


@dataclass(frozen=True, slots=True)
class CrystallizationArtifact:
    skill_id: str
    algorithm: str
    retained_context_keys: tuple[str, ...]
    removed_context_keys: tuple[str, ...]
    training_request_hashes: tuple[str, ...]
