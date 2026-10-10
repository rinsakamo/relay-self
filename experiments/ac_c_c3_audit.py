"""C3 read-only causal audit of frozen C1 toy; no models or production owners.

It reuses, but never edits, frozen Lane-C #440 functions. This file must
not be interpreted as real-world learning, physical attestation or energy.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from experiments.ac_c_allocation import (
    MODES,
    TICKS,
    WORK,
    Evidence,
    LearningState,
    SyntheticWorld,
    canonical_hash,
    cases_for,
    choose,
    viable,
)

PATH = Path(__file__).with_name("ac_c_c3_manifest.json")
MANIFEST_SHA256 = "dc59ee97b955fb23e3b5c3d12cde38f7fee6ae0976c0769508297d5b48d6e7d8"


def frozen_config() -> dict:
    config = json.loads(PATH.read_text(encoding="utf-8"))
    if canonical_hash(config) != MANIFEST_SHA256:
        raise ValueError("C3_FROZEN_MANIFEST_MISMATCH")
    return config


@dataclass(frozen=True)
class OutcomeReceipt:
    session: str
    decision_revision: int
    outcome_revision: int
    mechanism: str
    observed_success: bool
    damage: int
    exposure: int
    evidence_digest: str


def evidence_hash(evidence: Evidence) -> str:
    from dataclasses import asdict
    return hashlib.sha256(
        json.dumps(
            asdict(evidence), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


class WorldReceiptLedger:
    """Trusted in-memory issuance/consumption seam only within toy simulator.

    Identity-based acceptance prevents a caller from forging a new equivalent
    receipt and passing it as observed feedback. This is NOT remote attestation.
    """

    def __init__(self) -> None:
        self._issued: dict[str, OutcomeReceipt] = {}
        self._consumed: set[str] = set()

    def issue(self, world: SyntheticWorld, evidence: Evidence, mode: str) -> OutcomeReceipt:
        if evidence.session in self._issued:
            raise ValueError("DUPLICATE_OUTCOME_ISSUANCE")
        if mode == "CHEAP_EXACT":
            if evidence != world.evidence(fatigue=evidence.fatigue):
                raise ValueError("STALE_OR_FOREIGN_WORLD_EVIDENCE")
            if world.executed or evidence.revision != 0 or evidence.observation is not None:
                raise ValueError("INVALID_WORLD_SEQUENCE")
            if evidence.deadline < 1 or evidence.health <= 0:
                raise ValueError("CHEAP_EXACT_NOT_ADMISSIBLE")
            # A cheap deterministic alternative using exactly the same visible
            # glyph; its result is checked against hidden World truth only here.
            guess = evidence.glyph.bit_count() % 2
            world.executed = True
            succeeded = guess == world.case.target
            exposure = 0  # one synthetic tick, threat exposure requires >=3
            damage = 0 if succeeded else 2
        elif mode in MODES:
            succeeded, damage, exposure = world.execute(evidence, mode)
        else:
            raise ValueError("UNKNOWN_MECHANISM")
        receipt = OutcomeReceipt(
            evidence.session, 0, 1, mode, succeeded, damage, exposure,
            evidence_hash(evidence),
        )
        self._issued[evidence.session] = receipt
        return receipt

    def consume(self, evidence: Evidence, mode: str, receipt: OutcomeReceipt) -> bool:
        if (
            receipt.session != evidence.session
            or receipt.mechanism != mode
            or receipt.decision_revision != evidence.revision
            or receipt.outcome_revision != evidence.revision + 1
            or receipt.evidence_digest != evidence_hash(evidence)
            or self._issued.get(evidence.session) is not receipt
        ):
            raise ValueError("FOREIGN_OR_STALE_OR_FORGED_OUTCOME")
        if receipt.session in self._consumed:
            raise ValueError("DUPLICATE_FEEDBACK_CONSUMPTION")
        self._consumed.add(receipt.session)
        return receipt.observed_success


def _selection(evidence: Evidence, arm: str, state: LearningState) -> str:
    if arm == "CHEAP_EXACT":
        return "CHEAP_EXACT" if evidence.deadline >= 1 and evidence.health > 0 else "ABSTAIN"
    kind = "LEARNED" if arm == "LEARNED_NO_FEEDBACK" else arm
    return choose(evidence, kind, "BODY_AWARE", state)


def trajectory(seed: int, arm: str) -> dict:
    cfg = frozen_config()
    if arm not in cfg["arms"]:
        raise ValueError("UNPREDECLARED_ARM")
    state = LearningState()
    ledger = WorldReceiptLedger()
    case_groups = cases_for(seed, cfg["episodes_per_phase"])
    phases: dict[str, dict] = {}
    shift_frames: list[dict] = []
    for phase in cfg["phase_schedule"]:
        frame_list: list[dict] = []
        for case in case_groups:
            if case.phase != phase:
                continue
            world = SyntheticWorld(case)
            e = world.evidence(fatigue=state.fatigue)
            mode = _selection(e, arm, state)
            if mode != "ABSTAIN" and mode != "CHEAP_EXACT" and not viable(e, mode, "BODY_AWARE"):
                raise AssertionError("VIABILITY_VIOLATED")
            receipt = None
            if mode == "ABSTAIN":
                success = False
            else:
                receipt = ledger.issue(world, e, mode)
                success = ledger.consume(e, mode, receipt)
            if arm in ("FIXED", "LEARNED") and mode in MODES:
                # The *only* learning admission is a validated, single-use
                # World outcome receipt from the current session/revision.
                if receipt is None or not success == receipt.observed_success:
                    raise AssertionError("NO_GROUNDED_FEEDBACK")
                state.update(e, mode, success, bridge=False)
            else:
                # In NO_FEEDBACK, keep exploration period / opportunity
                # counts identical. CHEAP_EXACT never learns by design.
                state.seen += 1
            frame_list.append({
                "cue": e.cue,
                "mode": mode,
                "success": success if mode != "ABSTAIN" else None,
                "session": e.session,
                "outcome_revision": None if receipt is None else receipt.outcome_revision,
                "damage": 0 if receipt is None else receipt.damage,
            })
        frames = tuple(frame_list)
        if len(frames) != cfg["episodes_per_phase"]:
            raise AssertionError("PHASE_LENGTH_MISMATCH")
        phases[phase] = {
            "success": sum(f["success"] is True for f in frames),
            "failure": sum(f["success"] is False for f in frames),
            "abstain": sum(f["success"] is None for f in frames),
            "counts": dict(sorted(Counter(f["mode"] for f in frames).items())),
            "work_units": sum(WORK.get(f["mode"], 0) for f in frames),
            "selector_ops": cfg["episodes_per_phase"] * (
                6 if arm in ("LEARNED", "LEARNED_NO_FEEDBACK") else
                1 if arm == "FIXED" else 0
            ),
            "damage": sum(f["damage"] for f in frames),
        }
        if phase == "shift":
            shift_frames = list(frames)
    witnessed = {}
    for cue in (0, 1):
        failures = [i for i, frame in enumerate(shift_frames)
                    if frame["cue"] == cue and frame["mode"] == "FAST"
                    and frame["success"] is False]
        if not failures:
            witnessed[str(cue)] = {"failed_fast": False, "lag": None, "censored": True}
            continue
        first_failure = failures[0]
        escalations = [j for j in range(first_failure + 1, len(shift_frames))
                       if shift_frames[j]["cue"] == cue
                       and shift_frames[j]["mode"] in ("SLOW", "OBSERVE")]
        witnessed[str(cue)] = {
            "failed_fast": True, "failure_at": first_failure,
            "lag": escalations[0] - first_failure if escalations else None,
            "censored": not bool(escalations),
        }
    recovery_frames = [
        case for case in case_groups if case.phase == "recovery"
    ]
    if len(recovery_frames) != 64:
        raise AssertionError("RECOVERY_PHASE_MISMATCH")
    # Do not mistake raw post-shift cheap correctness for learning recovery.
    return {
        "seed": seed, "arm": arm, "phases": phases,
        "shift_witness": witnessed,
        "frames": tuple(
            {"phase": phase, **frame} for phase in cfg["phase_schedule"]
            for frame in _frames_again(seed, arm, phase, cfg)
        ) if False else None,
    }


def paired_report() -> dict:
    cfg = frozen_config()
    records = [trajectory(seed, arm) for seed in cfg["confirmation_seeds"]
               for arm in cfg["arms"]]
    summaries = {}
    for arm in cfg["arms"]:
        rows = [r for r in records if r["arm"] == arm]
        summaries[arm] = {
            "success": sum(p["success"] for r in rows for p in r["phases"].values()),
            "failure": sum(p["failure"] for r in rows for p in r["phases"].values()),
            "abstain": sum(p["abstain"] for r in rows for p in r["phases"].values()),
            "work_units": sum(p["work_units"] for r in rows for p in r["phases"].values()),
            "selector_ops": sum(p["selector_ops"] for r in rows for p in r["phases"].values()),
            "post_failure_escalation_witnesses": sum(
                v["failed_fast"] and not v["censored"]
                for r in rows for v in r["shift_witness"].values()
            ),
            "post_failure_escalation_censored": sum(
                v["censored"] for r in rows for v in r["shift_witness"].values()
            ),
        }
    return {
        "manifest_sha256": MANIFEST_SHA256,
        "records_sha256": canonical_hash(records),
        "records": records,
        "summaries": summaries,
        "cheap_exact_provisional_work_costs": {
            str(k): 5 * 4 * 64 * k for k in (1, 2, 3)
        },
    }


if __name__ == "__main__":
    print(json.dumps(paired_report(), sort_keys=True, ensure_ascii=False))
