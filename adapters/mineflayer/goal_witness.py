"""Offline Mineflayer endpoint witness qualification (AC-C C15).

Consumes EXISTING decoded Mineflayer stream facts; never issues an Action,
changes the adapter protocol, or generates a signed cognitive/goal label.

SPATIAL endpoint observation != a Skill result, causal action proof, or
negative z label. An external owned-server test is required separately.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerEffectResult,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerStreamDecoder,
)

_MANIFEST_FILE = Path(__file__).resolve().parents[2] / "experiments" / "ac_c_c15_manifest.json"
_MANIFEST_SHA = "5e33dd0a0101cdc1d8e540c5d078417d1d343f83db18736a44678c5f39859e8c"
ALLOWED_STATUS = frozenset(
    {"GOAL_REGION_OBSERVED", "ALTERNATIVE_REGION_OBSERVED", "UNDETERMINED"}
)
LIVE_QUALIFICATION = "NOT_RUN"
SIGNED_ACTION_LABEL = "BLOCKED_UNDERDETERMINED"


@lru_cache(maxsize=1)
def manifest() -> dict:
    doc = json.loads(_MANIFEST_FILE.read_text(encoding="utf-8"))
    canonical = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != _MANIFEST_SHA:
        raise ValueError("C15_FROZEN_MANIFEST_DRIFT")
    return doc


class InvalidSpatialContract(ValueError):
    """The proposed goal box or source/action contract is not admissible."""


def _finite_xyz(p: tuple[float, float, float]) -> tuple[float, float, float]:
    if (not isinstance(p, tuple) or len(p) != 3
            or any(isinstance(x, bool) or not isinstance(x, (int, float))
                   or not math.isfinite(x) for x in p)):
        raise InvalidSpatialContract("coordinate must be 3 finite numeric values")
    return tuple(float(x) for x in p)


@dataclass(frozen=True)
class Region:
    low: tuple[float, float, float]
    high: tuple[float, float, float]

    def __post_init__(self) -> None:
        low, high = _finite_xyz(self.low), _finite_xyz(self.high)
        if any(lo >= hi for lo, hi in zip(low, high)):
            raise InvalidSpatialContract("region has non-positive extent")
        object.__setattr__(self, "low", low)
        object.__setattr__(self, "high", high)

    def contains_closed(self, p: MineflayerPosition) -> bool:
        return all(lo <= v <= hi for v, lo, hi in zip(
            (p.x, p.y, p.z), self.low, self.high
        ))

    def contains_strict(self, p: MineflayerPosition) -> bool:
        margin = manifest()["qualification_contract"]["strict_box_interior_margin"]
        return all(lo + margin < v < hi - margin for v, lo, hi in zip(
            (p.x, p.y, p.z), self.low, self.high
        ))


@dataclass(frozen=True)
class SpatialContract:
    session_id: str
    start_action_id: str
    stop_action_id: str
    goal: Region
    alternative: Region

    def __post_init__(self) -> None:
        for label, value in (
            ("session_id", self.session_id),
            ("start_action_id", self.start_action_id),
            ("stop_action_id", self.stop_action_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise InvalidSpatialContract(f"empty {label}")
        if self.start_action_id == self.stop_action_id:
            raise InvalidSpatialContract("control and stop Action IDs must be distinct")
        if not isinstance(self.goal, Region) or not isinstance(self.alternative, Region):
            raise InvalidSpatialContract("regions must be typed")
        separation = manifest()["qualification_contract"]["region_interbox_gap_min"]
        if not any(
            self.goal.high[i] + separation <= self.alternative.low[i]
            or self.alternative.high[i] + separation <= self.goal.low[i]
            for i in range(3)
        ):
            raise InvalidSpatialContract("regions overlap or are too close")


@dataclass(frozen=True)
class EndpointWitness:
    status: str
    reason: str
    session_id: str
    evidence: tuple[str, ...]
    # Deliberately NO z, correctness, signed feedback, Skill or Learning record.

    def __post_init__(self) -> None:
        if self.status not in ALLOWED_STATUS:
            raise ValueError("unregistered spatial witness status")


def _distance_xyz(a: MineflayerPosition, b: MineflayerPosition) -> float:
    return math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2 + (a.z-b.z)**2)


def _region_name(p: MineflayerPosition, spec: SpatialContract) -> str:
    if spec.goal.contains_strict(p):
        return "GOAL_REGION_OBSERVED"
    if spec.alternative.contains_strict(p):
        return "ALTERNATIVE_REGION_OBSERVED"
    return "UNDETERMINED"


class EndpointReducer:
    """One-shot stream reduction. NOT a live listener or new runtime owner."""

    def __init__(self) -> None:
        self._seen: set[tuple[str, str, str]] = set()

    def qualify(self, lines: Iterable[str], spec: SpatialContract) -> EndpointWitness:
        if not isinstance(spec, SpatialContract):
            raise InvalidSpatialContract("spatial contract is required")
        key = (spec.session_id, spec.start_action_id, spec.stop_action_id)
        if key in self._seen:
            return EndpointWitness("UNDETERMINED", "DUPLICATE_TRANSACTION",
                                   spec.session_id, ())
        self._seen.add(key)  # even invalid attempts cannot be replayed
        decoder = MineflayerStreamDecoder()
        state = "EXPECT_PRE_PROBE"
        baseline: MineflayerObservation | None = None
        terminal: list[MineflayerObservation] = []
        references: list[str] = []
        start_seen = False
        stop_seen = False
        invalid: str | None = None

        try:
            for line in lines:
                message = decoder.decode(line)
                if message.session_id != spec.session_id:
                    invalid = "WRONG_SESSION"
                    break
                if message.seq == 0:
                    # Stream decoder already validated adapter_started.
                    references.append(message.provenance.reference)
                    continue
                references.append(message.provenance.reference)
                if isinstance(message, (
                    MineflayerConnectionEnd, MineflayerAdapterErrorMessage,
                    MineflayerCommandError,
                )):
                    invalid = "INTERRUPTED_STREAM"
                    break

                if isinstance(message, MineflayerEffectResult):
                    if state == "EXPECT_START_ACK":
                        if (message.action_id != spec.start_action_id
                                or message.effect != "set_control"
                                or message.result != "applied"):
                            invalid = "INVALID_START_ACK"
                            break
                        start_seen = True
                        state = "EXPECT_STOP_ACK"
                    elif state == "EXPECT_STOP_ACK":
                        if (message.action_id != spec.stop_action_id
                                or message.effect != "clear_controls"
                                or message.result != "applied"):
                            invalid = "INVALID_STOP_ACK"
                            break
                        stop_seen = True
                        state = "EXPECT_TERMINAL_PROBES"
                    else:
                        invalid = "DUPLICATE_OR_UNORDERED_ACK"
                        break
                    continue

                if not isinstance(message, MineflayerObservation):
                    invalid = "UNEXPECTED_SOURCE_MESSAGE"
                    break
                if message.kind in ("forcedMove", "respawn", "death"):
                    invalid = "EXTERNAL_MOVEMENT_OR_RESET"
                    break

                if state == "EXPECT_PRE_PROBE":
                    if message.kind != "probe":
                        invalid = "MISSING_BASELINE_PROBE"
                        break
                    baseline = message
                    state = "EXPECT_START_ACK"
                elif state == "EXPECT_START_ACK":
                    invalid = "OBSERVATION_BEFORE_START_ACK"
                    break
                elif state == "EXPECT_STOP_ACK":
                    # Ordinary move/health updates do not prove the goal.
                    if message.kind == "probe":
                        invalid = "PROBE_BEFORE_STOP_ACK"
                        break
                elif state == "EXPECT_TERMINAL_PROBES":
                    if message.kind != "probe" or len(terminal) >= 2:
                        invalid = "NONTERMINAL_OR_EXCESS_POSTSTOP_EVIDENCE"
                        break
                    terminal.append(message)
        except (ValueError, TypeError) as exc:
            invalid = f"INVALID_DECODED_SOURCE:{type(exc).__name__}"

        if invalid is not None:
            return EndpointWitness("UNDETERMINED", invalid, spec.session_id,
                                   tuple(references))
        if (baseline is None or not start_seen or not stop_seen or len(terminal) != 2):
            return EndpointWitness("UNDETERMINED", "INCOMPLETE_TRANSACTION",
                                   spec.session_id, tuple(references))
        if (spec.goal.contains_closed(baseline.snapshot.position)
                or spec.alternative.contains_closed(baseline.snapshot.position)):
            return EndpointWitness("UNDETERMINED", "PREEXISTING_REGION",
                                   spec.session_id, tuple(references))
        p1, p2 = terminal[0].snapshot.position, terminal[1].snapshot.position
        max_diff = manifest()["qualification_contract"]["probe_tolerance_xyz"]
        if any(abs(a-b) > max_diff for a, b in zip(
            (p1.x,p1.y,p1.z),(p2.x,p2.y,p2.z)
        )):
            return EndpointWitness("UNDETERMINED", "UNSTABLE_ENDPOINT",
                                   spec.session_id, tuple(references))
        if _distance_xyz(baseline.snapshot.position, p2) < (
            manifest()["qualification_contract"]["observed_before_after_displacement_min"]
        ):
            return EndpointWitness("UNDETERMINED", "NO_POSITION_CHANGE",
                                   spec.session_id, tuple(references))
        first_region = _region_name(p1, spec)
        second_region = _region_name(p2, spec)
        if (first_region != second_region or first_region == "UNDETERMINED"):
            return EndpointWitness("UNDETERMINED", "NO_STABLE_EXCLUSIVE_REGION",
                                   spec.session_id, tuple(references))
        return EndpointWitness(second_region, "SPATIAL_ENDPOINT_ONLY",
                               spec.session_id, tuple(references))
