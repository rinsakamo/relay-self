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


CASES = (
    NarrowingCase(
        case_id="cave_only",
        route_cave=True,
        route_ridge=False,
        shelter_cave=True,
        shelter_ridge=False,
        expected_choice_id="cave",
    ),
    NarrowingCase(
        case_id="ridge_only",
        route_cave=False,
        route_ridge=True,
        shelter_cave=True,
        shelter_ridge=False,
        expected_choice_id="ridge",
    ),
    NarrowingCase(
        case_id="both_cave_shelter",
        route_cave=True,
        route_ridge=True,
        shelter_cave=True,
        shelter_ridge=False,
        expected_choice_id="cave",
    ),
    NarrowingCase(
        case_id="both_ridge_shelter",
        route_cave=True,
        route_ridge=True,
        shelter_cave=False,
        shelter_ridge=True,
        expected_choice_id="ridge",
    ),
)

BROAD_DISTRACTORS: tuple[tuple[str, object], ...] = (
    ("hunger", 14),
    ("saturation", 3.5),
    ("inventory:oak_log", 12),
    ("inventory:cobblestone", 31),
    ("inventory:torch", 9),
    ("tool:pickaxe_durability", 0.62),
    ("xp_level", 7),
    ("crafting_queue", ["stone_pickaxe"]),
    ("furnace_active", False),
    ("farm:wheat_mature_count", 3),
    ("storage_free_slots", 11),
    ("conversation_topic", "base organization"),
    ("companion_speaking", False),
    ("chat_unread_count", 2),
    ("recipe_unlocked_count", 18),
    ("map_marker_count", 4),
)


def _provenance(reference: str) -> Provenance:
    return Provenance(source=SOURCE, reference=reference)


def _datum(key: str, value: object, reference: str) -> CognitionDatum:
    return CognitionDatum.from_value(
        key,
        value,
        _provenance(reference),
    )


def relevant_context(case: NarrowingCase) -> tuple[CognitionDatum, ...]:
    return (
        _datum("threat_nearby", True, f"{case.case_id}:threat"),
        _datum("health", 6, f"{case.case_id}:health"),
        _datum(
            "route_open:cave",
            case.route_cave,
            f"{case.case_id}:route:cave",
        ),
        _datum(
            "route_open:ridge",
            case.route_ridge,
            f"{case.case_id}:route:ridge",
        ),
        _datum(
            "shelter:cave",
            case.shelter_cave,
            f"{case.case_id}:shelter:cave",
        ),
        _datum(
            "shelter:ridge",
            case.shelter_ridge,
            f"{case.case_id}:shelter:ridge",
        ),
    )


def broad_context(case: NarrowingCase) -> tuple[CognitionDatum, ...]:
    relevant = relevant_context(case)
    distractors = tuple(
        _datum(key, value, f"{case.case_id}:broad:{index}:{key}")
        for index, (key, value) in enumerate(BROAD_DISTRACTORS)
    )
    return relevant + distractors


def build_request(
    case: NarrowingCase,
    *,
    condition: str,
) -> BoundedChoiceRequest:
    if condition not in CONDITIONS:
        raise ValueError(f"unsupported condition: {condition}")
    context = (
        broad_context(case)
        if condition == "broad"
        else relevant_context(case)
    )
    return BoundedChoiceRequest(
        request_id=f"skill-narrowing:{case.case_id}:{condition}",
        instruction=(
            "Choose the safer currently reachable destination for the active "
            "FLEE skill. A destination is admissible only when route_open is "
            "true. If both destinations are reachable, prefer the one whose "
            "shelter fact is true. Use only supplied context."
        ),
        intent_id="intent-reach-safety",
        focus="FLEE",
        choices=(
            BoundedChoice("cave", "Destination cave"),
            BoundedChoice("ridge", "Destination ridge"),
        ),
        context=context,
    )
