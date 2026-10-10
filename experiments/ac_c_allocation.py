"""AC-C offline synthetic allocation experiment; NOT a RelaySelf semantic owner."""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path

MANIFEST_PATH = Path(__file__).with_name("ac_c_allocation_manifest.json")
MANIFEST_SHA256 = "d444b96c40a5bec21603122298b3d138e4b0139ad77e027de80d190d2316a481"
MODES = ("FAST", "MEDIUM", "SLOW", "OBSERVE")
ARMS = ("FAST_ONLY", "SLOW_ONLY", "FIXED", "LEARNED", "ORACLE_UPPER_BOUND")
SCENARIOS = (
    "TIME_ONLY", "TIME_PLUS_WORK", "BODY_AWARE", "FATIGUE_BRIDGE_OFF",
    "FATIGUE_BRIDGE_ON", "HIGH_OVERHEAD",
)
TICKS = {"FAST": 1, "MEDIUM": 2, "SLOW": 5, "OBSERVE": 4}
WORK = {"FAST": 1, "MEDIUM": 3, "SLOW": 12, "OBSERVE": 2}


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def manifest() -> dict:
    result = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if canonical_hash(result) != MANIFEST_SHA256:
        raise ValueError("FROZEN_MANIFEST_MISMATCH")
    return result


@dataclass(frozen=True)
class HiddenCase:
    """Evaluator/World truth: never supply this object to an ordinary selector."""

    session: str
    glyph: int
    cue: int
    deadline: int
    health: int
    hunger: int
    threat: bool
    scan_available: bool
    phase: str

    @property
    def target(self) -> int:
        return self.glyph.bit_count() % 2


@dataclass(frozen=True)
class Evidence:
    session: str
    revision: int
    glyph: int
    cue: int
    deadline: int
    health: int
    hunger: int
    threat: bool
    scan_available: bool
    fatigue: int = 0
    observation: int | None = None


def cases_for(seed: int, n: int) -> tuple[HiddenCase, ...]:
    config = manifest()
    rng = random.Random(seed)
    cases = []
    for phase in config["phases"]:
        for step in range(n):
            glyph = rng.randrange(8)
            target = glyph.bit_count() % 2
            agree = rng.random() < config["cue_matches_parity_probability"][phase]
            cases.append(HiddenCase(
                session=f"ac-c:{seed}:{phase}:{step}", glyph=glyph,
                cue=target if agree else 1 - target,
                deadline=rng.choice((1, 2, 3, 4, 5, 7)),
                health=rng.choice((2, 3, 5, 8)),
                hunger=rng.choice((2, 4, 9, 16)),
                threat=bool(rng.randrange(2)),
                scan_available=rng.random() < 0.5,
                phase=phase,
            ))
    return tuple(cases)


class SyntheticWorld:
    """Source-fenced, one-outcome simulator. No physical or model execution."""

    def __init__(self, case: HiddenCase):
        self.case = case
        self.executed = False

    def evidence(self, *, fatigue: int) -> Evidence:
        return Evidence(
            session=self.case.session, revision=0, glyph=self.case.glyph,
            cue=self.case.cue, deadline=self.case.deadline, health=self.case.health,
            hunger=self.case.hunger, threat=self.case.threat,
            scan_available=self.case.scan_available, fatigue=fatigue,
        )

    def execute(self, initial: Evidence, mechanism: str) -> tuple[bool, int, int]:
        if self.executed:
            raise ValueError("DUPLICATE_TERMINAL_WORLD_OUTCOME")
        if initial != self.evidence(fatigue=initial.fatigue):
            raise ValueError("STALE_OR_FOREIGN_WORLD_EVIDENCE")
        if initial.revision != 0 or initial.observation is not None:
            raise ValueError("UNAUTHORIZED_OR_STALE_OBSERVATION")
        if mechanism not in MODES:
            raise ValueError("INVALID_MECHANISM")
        if mechanism == "OBSERVE" and not initial.scan_available:
            raise ValueError("SCAN_UNAVAILABLE")
        if TICKS[mechanism] > initial.deadline:
            raise ValueError("DEADLINE_VIOLATION")
        self.executed = True
        if mechanism == "OBSERVE":
            # Authorized experimental scan: a new World bit at revision 1,
            # not a secret freely inserted into the original selector input.
            later = Evidence(
                session=initial.session, revision=1, glyph=initial.glyph,
                cue=initial.cue, deadline=initial.deadline, health=initial.health,
                hunger=initial.hunger, threat=initial.threat,
                scan_available=initial.scan_available, fatigue=initial.fatigue,
                observation=self.case.target,
            )
            chosen = later.observation
        elif mechanism == "SLOW":
            chosen = initial.glyph.bit_count() % 2
        elif mechanism == "MEDIUM":
            chosen = (initial.glyph & 3).bit_count() % 2
        else:
            chosen = initial.cue
        success = chosen == self.case.target
        exposure = int(initial.threat and TICKS[mechanism] >= 3)
        damage = int(not success) * 2 + exposure
        return success, damage, exposure


def viable(evidence: Evidence, mode: str, scenario: str) -> bool:
    if mode not in MODES or TICKS[mode] > evidence.deadline:
        return False
    if mode == "OBSERVE" and not evidence.scan_available:
        return False
    exposure = int(evidence.threat and TICKS[mode] >= 3)
    worst_damage = exposure + (2 if mode in ("FAST", "MEDIUM") else 0)
    if evidence.health <= worst_damage:
        return False
    if scenario in ("BODY_AWARE", "FATIGUE_BRIDGE_OFF", "FATIGUE_BRIDGE_ON", "HIGH_OVERHEAD"):
        if mode == "SLOW" and evidence.hunger <= 3:
            return False
        if mode == "OBSERVE" and evidence.hunger <= 2:
            return False
    if scenario == "FATIGUE_BRIDGE_ON" and evidence.fatigue >= 8 and mode in ("SLOW", "OBSERVE"):
        return False
    return True


@dataclass
class LearningState:
    # Only observed outcomes of the chosen cheap method. No oracle labels.
    outcomes: dict[tuple[int, str], deque[bool]] = field(default_factory=dict)
    seen: int = 0
    fatigue: int = 0

    def estimate(self, cue: int, mechanism: str) -> float:
        if mechanism in ("SLOW", "OBSERVE"):
            # Declared toy capability, NOT estimated real-world LLM accuracy.
            return 1.0
        recent = self.outcomes.get((cue, mechanism), ())
        return (1 + sum(recent)) / (2 + len(recent))

    def update(self, evidence: Evidence, mechanism: str, success: bool, *, bridge: bool) -> None:
        if mechanism in ("FAST", "MEDIUM"):
            key = (evidence.cue, mechanism)
            self.outcomes.setdefault(key, deque(maxlen=6)).append(success)
        if bridge:
            self.fatigue = max(0, self.fatigue - 1) + (WORK.get(mechanism, 0) // 3)
        self.seen += 1


def choose(evidence: Evidence, arm: str, scenario: str, state: LearningState) -> str:
    """No HiddenCase, phase, answer, oracle or future consequence argument."""
    eligible = [m for m in MODES if viable(evidence, m, scenario)]
    if not eligible:
        return "ABSTAIN"
    if arm == "FAST_ONLY":
        return "FAST" if "FAST" in eligible else "ABSTAIN"
    if arm == "SLOW_ONLY":
        return "SLOW" if "SLOW" in eligible else "ABSTAIN"
    if arm == "FIXED":
        if "FAST" in eligible and evidence.health >= 5:
            return "FAST"
        for m in ("OBSERVE", "SLOW", "MEDIUM", "FAST"):
            if m in eligible:
                return m
    if arm == "LEARNED":
        if state.seen % 8 == 7 and "MEDIUM" in eligible:
            return "MEDIUM"
        if state.seen % 4 == 3 and "FAST" in eligible:
            return "FAST"
        good = [m for m in eligible if state.estimate(evidence.cue, m) >= 0.75]
        if not good:
            return "ABSTAIN"
        weight = 0 if scenario == "TIME_ONLY" else 0.1
        return min(good, key=lambda m: (TICKS[m] + weight * WORK[m], TICKS[m], m))
    raise ValueError("ORACLE_MUST_NOT_ACCESS_ORDINARY_SELECTOR")


def oracle(evidence: Evidence, case: HiddenCase, scenario: str) -> str:
    """Privileged evaluator-only upper bound; NOT a valid ordinary arm."""
    elig = [m for m in MODES if viable(evidence, m, scenario)]
    options = []
    for mode in elig:
        guess = {
            "FAST": evidence.cue,
            "MEDIUM": (evidence.glyph & 3).bit_count() % 2,
            "SLOW": evidence.glyph.bit_count() % 2,
            "OBSERVE": case.target,
        }[mode]
        if guess == case.target:
            options.append(mode)
    return min(options, key=lambda m: (TICKS[m], WORK[m])) if options else "ABSTAIN"


def evaluate(seed: int, arm: str, scenario: str, n: int = 64) -> dict:
    if arm not in ARMS or scenario not in SCENARIOS:
        raise ValueError("INVALID_EXPERIMENT_CONDITION")
    state = LearningState()
    phases = {}
    all_counts = Counter()
    for phase in manifest()["phases"]:
        counts = Counter()
        total_ticks = total_work = overhead = damage_total = hunger_used = 0
        success_count = failed = violations = abstained = deadline_misses = 0
        transition_to_expensive = None
        for index, case in enumerate(cases_for(seed, n)):
            if case.phase != phase:
                continue
            world = SyntheticWorld(case)
            evidence = world.evidence(fatigue=state.fatigue)
            mode = (oracle(evidence, case, scenario) if arm == "ORACLE_UPPER_BOUND"
                    else choose(evidence, arm, scenario, state))
            ops = (0 if arm in ("FAST_ONLY", "SLOW_ONLY", "ORACLE_UPPER_BOUND")
                   else 1 if arm == "FIXED" else 40 if scenario == "HIGH_OVERHEAD" else 6)
            overhead += ops
            counts[mode] += 1
            all_counts[mode] += 1
            if mode == "ABSTAIN":
                abstained += 1
                if not any(viable(evidence, m, scenario) for m in MODES):
                    if any(TICKS[m] > evidence.deadline for m in MODES):
                        deadline_misses += 1
                state.update(evidence, mode, False, bridge=scenario == "FATIGUE_BRIDGE_ON")
                continue
            if not viable(evidence, mode, scenario):
                violations += 1
                raise AssertionError("selector violated HARD viability")
            did_succeed, damage, hunger = world.execute(evidence, mode)
            success_count += did_succeed
            failed += not did_succeed
            damage_total += damage
            hunger_used += hunger
            total_ticks += TICKS[mode]
            total_work += WORK[mode]
            if phase == "shift" and mode in ("OBSERVE", "SLOW") and transition_to_expensive is None:
                transition_to_expensive = index
            state.update(evidence, mode, did_succeed, bridge=scenario == "FATIGUE_BRIDGE_ON")
        phases[phase] = {
            "success": success_count, "failure": failed, "abstain": abstained,
            "deadline_miss": deadline_misses, "violation": violations,
            "counts": dict(sorted(counts.items())), "ticks": total_ticks,
            "work_units": total_work, "selector_ops": overhead,
            "damage": damage_total, "hunger_consumed_from_exposure": hunger_used,
            "ending_virtual_fatigue": state.fatigue,
            "shift_first_slow_or_observe_index": transition_to_expensive,
        }
    return {"seed": seed, "arm": arm, "scenario": scenario, "phases": phases,
            "total_counts": dict(sorted(all_counts.items()))}


def run() -> dict:
    info = manifest()
    records = [evaluate(seed, arm, scenario, info["episodes_per_phase"])
               for seed in info["training_seeds"] + info["heldout_seeds"]
               for scenario in SCENARIOS for arm in ARMS]
    return {
        "manifest_sha256": MANIFEST_SHA256,
        "result_sha256": canonical_hash(records),
        "n_records": len(records),
        "records": records,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, ensure_ascii=False, separators=(",", ":")))
