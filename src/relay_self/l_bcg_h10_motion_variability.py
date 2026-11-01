"""H10: source-qualified *retrospective* motion variability diagnostic.

Describe existing original S49 native sequence order and 8 Paper samples.
Never correlate Paper World ticks to native seq by invented clocks.
A World after-action signal is NOT an Action-pre input or formal L1 label.
"""
from __future__ import annotations

import hashlib
import math
from collections import Counter
from dataclasses import asdict, dataclass

SLOTS = ("A-F1", "B-F1", "B-F2", "A-F2", "B-E1", "A-E1", "A-E2", "B-E2")
BASELINE_PATTERN_M = (0.049492188301323736, 0.009543604920851934, 0.005210808286784996)
PATTERN_TOLERANCE_M = 1e-9


class H10Rejected(ValueError):
    """Archived source/effect relation failed; no inference allowed."""


@dataclass(frozen=True, slots=True)
class H10WorldMotion:
    slot: str
    arm: str
    role: str
    session_id: str
    paper_world_id: str
    report_raw_sha256: str
    source_original_audit: str
    original_s42_distance_m: float
    original_action_move_m: float
    original_dispatch_seq: int
    original_clear_seq: int
    original_s16_after_seq: int
    native_dispatch_to_clear_seq_delta: int
    native_clear_to_s16_after_seq_delta: int
    native_after_seq_before_settling: bool
    paper_sample_count: int
    paper_first_tick: int
    paper_last_tick: int
    paper_reported_input_off_all: bool
    paper_displacements_m: tuple[float, ...]
    paper_proxy_total_m: float
    paper_positive_sample_count: int
    first_sample_share_of_proxy: float
    pattern_matches_modal_baseline: bool
    l22_settling_native_move_count: int
    l22_settling_probe_count: int
    l22_quiet_streak: int
    clock_alignment: str = "NOT_ATTESTED"
    physically_effective_clear: str = "NOT_ATTESTED"
    temporal_causation_claim: bool = False
    source_is_pre_action_condition: bool = False


@dataclass(frozen=True, slots=True)
class H10Diagnostic:
    classification: str
    worlds: tuple[H10WorldMotion, ...]
    modal_baseline_worlds: int
    modal_baseline_world_ids: tuple[str, ...]
    unique_proxy_patterns: int
    max_proxy_total_slot: str
    min_proxy_total_slot: str
    same_arm_proxy_range_a_m: float
    same_arm_proxy_range_b_m: float
    action_move_distinct_counts: int
    paper_native_clock_alignment: str = "NOT_ATTESTED"
    effective_clear: str = "NOT_ATTESTED"
    label_type: str = "RETROSPECTIVE_DEV_SAMPLED_PAPER_PROXY"
    cause_of_variability: str = "UNDETERMINED"
    h9b_model_predictive_improvement: str = "NOT_DEMONSTRATED"
    original_h9b_eval_unchanged: bool = True
    new_worlds: int = 0
    original_actions_added: int = 0
    additional_native_probes: int = 0
    model_calls: int = 0
    learning_updates: int = 0
    qualified_training_worlds: int = 0
    l1_advice: str = "DEFER_UNKNOWN"
    qualification: str = "NO_GO"
    science: str = "NOT_RUN"


def _guard(ok: bool, why: str) -> None:
    if not ok:
        raise H10Rejected(why)


def _finite(v: object) -> bool:
    return type(v) in (int, float) and math.isfinite(v)


def inspect_h10_world(
    *, slot: str, report: dict, report_original: bytes,
    audit: dict, original_manifest: dict,
) -> H10WorldMotion:
    _guard(slot in SLOTS and type(report) is dict and type(audit) is dict
           and type(original_manifest) is dict and type(report_original) is bytes,
           "H10 exact archived original required")
    digest = hashlib.sha256(report_original).hexdigest()
    _guard(
        original_manifest.get("s49-report.json") == digest
        and audit.get("original_sha256", {}).get("s49-report.json") == digest
        and audit.get("classification") == "DEV_H8_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED"
        and audit.get("actions") == audit.get("s16_outcomes") == audit.get("worlds") == 1
        and audit.get("additional_actions") == audit.get("additional_native_probes") == 0
        and audit.get("model_calls") == audit.get("learning_updates") == 0
        and audit.get("qualified_training_worlds") == 0
        and audit.get("effective_clear") == "NOT_ATTESTED"
        and audit.get("goal") == "UNDETERMINED"
        and audit.get("qualification") == "NO_GO"
        and audit.get("science") == "NOT_RUN",
        "original independent H8 audit and raw SHA required",
    )
    try:
        sid = report["session_id"]
        act = report["actual_native_actions"][0]
        ex = act["execution_evidence"]
        decisions = report["decisions"]
        window = report["live_next_epoch"]["window"]
        ticks = window["ticks"]
        settling = report["l22_settling"]["runtime"]
        pre = report["l_bcg_h8_preaction"]
    except (KeyError, TypeError, IndexError) as exc:
        raise H10Rejected("S49/H8/Paper/L22 original field unavailable") from exc
    _guard(
        type(sid) is str and bool(sid)
        and len(report["actual_native_actions"]) == 1
        and len(decisions) == 3
        and [d["selected"] for d in decisions] == ["WAIT", "MOVE_AWAY", "WAIT"]
        and [d["issued"] for d in decisions] == [False, True, False]
        and pre == audit.get("preaction")
        and pre["session_id"] == sid
        and pre["native_seq"] == decisions[1]["probe_seq"]
        and pre["advice"] == "DEFER_UNKNOWN"
        and pre["action_authority"] is False
        and pre["qualified_training_worlds"] == 0
        and pre["owner_receipts"] == {}
        and report["l_bcg_shadow"]["advice"] == "DEFER_UNKNOWN"
        and ex["action_ref"] == "MOVE_BACKWARD"
        and ex["status"] == "executed"
        and ex["goal_success_attested"] is False
        and ex["learning_feedback_qualified"] is False
        and ex["session_id"] == sid == window["session_id"]
        and ex["action_id"] == window["action_id"]
        and ex["action_id"] == act["action"]
        and ex["dispatch_receipt"]["result"] == "applied"
        and ex["cleanup_receipt"]["result"] == "applied"
        and ex["before_observation"]["session_id"] == sid
        and ex["after_observation"]["session_id"] == sid
        and settling["session_id"] == sid
        and settling["action_id"] == ex["action_id"]
        and settling["physically_stopped_proven"] is False
        and settling["stable_world_ticks_attested"] is False
        and window["provisional"] is True
        and window["effective_clear_tick"] == "NOT_ATTESTED"
        and window["physical_stability_attested"] is False
        and report["l23_paper"]["readback"]["clock_alignment"] == "NOT_ATTESTED"
        and report["l23_paper"]["readback"]["paper_effective_input_clear_tick"] == "NOT_ATTESTED",
        "H10 source/Action identity, owner, or physical scope changed",
    )
    dseq = ex["dispatch_receipt"]["seq"]
    cseq = ex["cleanup_receipt"]["seq"]
    aseq = ex["after_observation"]["seq"]
    _guard(
        all(type(x) is int for x in (dseq, cseq, aseq))
        and pre["native_seq"] < dseq < cseq < aseq
        and aseq < min(settling["observed_probe_seqs"])
        and _finite(ex["movement_m"]) and ex["movement_m"] >= 0
        and _finite(decisions[1]["distance_m"]),
        "original native Action source sequence not qualified",
    )
    _guard(
        type(ticks) is list and len(ticks) == 8
        and window["paper_world_uuid"]
        and window["paper_sample_count"] == 8 if "paper_sample_count" in window
        else type(ticks) is list and len(ticks) == 8 and bool(window["paper_world_uuid"]),
        "H10 complete Paper eight tick window required",
    )
    _guard(
        all(
            type(t) is dict
            and type(t.get("world_tick")) is int
            and type(t.get("last_reported_input_active")) is bool
            and _finite(t.get("displacement_m"))
            and t["displacement_m"] >= 0 for t in ticks
        ) and all(
            ticks[i + 1]["world_tick"] == ticks[i]["world_tick"] + 1
            for i in range(7)
        ),
        "Paper tick samples are missing, malformed or noncontiguous",
    )
    values = tuple(t["displacement_m"] for t in ticks)
    off = all(not t["last_reported_input_active"] for t in ticks)
    _guard(off, "H10 expected same reported input-OFF proxy source for all 8")
    total = sum(values)
    _guard(math.isfinite(total) and total > 0, "H10 source proxy sum invalid")
    baseline = (
        len(values) == 8
        and all(
            abs(values[i] - BASELINE_PATTERN_M[i]) <= PATTERN_TOLERANCE_M
            for i in range(3)
        )
        and all(abs(v) <= PATTERN_TOLERANCE_M for v in values[3:])
    )
    _guard(
        len(settling["observed_move_seqs"]) >= 1
        and len(settling["observed_probe_seqs"]) >= 1
        and type(settling["quiet_streak"]) is int
        and window["paper_world_uuid"] != sid
        and audit["l_bcg_shadow"]["advice"] == "DEFER_UNKNOWN",
        "postS16 settling source/clock ceiling missing",
    )
    return H10WorldMotion(
        slot=slot, arm="A" if slot.startswith("A-") else "B",
        role="DEV_FIT" if "-F" in slot else "DEV_EVAL",
        session_id=sid, paper_world_id=window["paper_world_uuid"],
        report_raw_sha256=digest,
        source_original_audit=audit["classification"],
        original_s42_distance_m=float(decisions[1]["distance_m"]),
        original_action_move_m=float(ex["movement_m"]),
        original_dispatch_seq=dseq, original_clear_seq=cseq,
        original_s16_after_seq=aseq,
        native_dispatch_to_clear_seq_delta=cseq - dseq,
        native_clear_to_s16_after_seq_delta=aseq - cseq,
        native_after_seq_before_settling=True,
        paper_sample_count=len(ticks),
        paper_first_tick=ticks[0]["world_tick"],
        paper_last_tick=ticks[-1]["world_tick"],
        paper_reported_input_off_all=off,
        paper_displacements_m=values,
        paper_proxy_total_m=total,
        paper_positive_sample_count=sum(v > 1e-12 for v in values),
        first_sample_share_of_proxy=values[0] / total,
        pattern_matches_modal_baseline=baseline,
        l22_settling_native_move_count=len(settling["observed_move_seqs"]),
        l22_settling_probe_count=len(settling["observed_probe_seqs"]),
        l22_quiet_streak=settling["quiet_streak"],
    )


def summarize_h10(worlds: tuple[H10WorldMotion, ...]) -> H10Diagnostic:
    _guard(type(worlds) is tuple and len(worlds) == 8,
           "H10 requires all eight archived original Worlds")
    _guard(
        tuple(w.slot for w in worlds) == SLOTS
        and len(set(w.session_id for w in worlds)) == 8
        and len(set(w.paper_world_id for w in worlds)) == 8
        and len(set(w.report_raw_sha256 for w in worlds)) == 8
        and all(
            w.clock_alignment == w.physically_effective_clear == "NOT_ATTESTED"
            and not w.temporal_causation_claim
            and not w.source_is_pre_action_condition
            for w in worlds
        ),
        "H10 cross-World source, order or ceiling changed",
    )
    baseline = tuple(w.slot for w in worlds if w.pattern_matches_modal_baseline)
    _guard(len(baseline) >= 1, "H10 known baseline did not recur")
    # Floating point Paper diffs within 1e-9m are one observed sample pattern.
    signatures = [
        tuple(round(v, 9) for v in w.paper_displacements_m) for w in worlds
    ]
    a = [w.paper_proxy_total_m for w in worlds if w.arm == "A"]
    b = [w.paper_proxy_total_m for w in worlds if w.arm == "B"]
    _guard(len(a) == len(b) == 4, "H10 fixed A/B World count changed")
    return H10Diagnostic(
        classification="H10_8_WORLD_ARCHIVED_MOTION_WINDOW_FORENSIC_DEV_ONLY",
        worlds=worlds,
        modal_baseline_worlds=len(baseline),
        modal_baseline_world_ids=baseline,
        unique_proxy_patterns=len(Counter(signatures)),
        max_proxy_total_slot=max(worlds, key=lambda x: x.paper_proxy_total_m).slot,
        min_proxy_total_slot=min(worlds, key=lambda x: x.paper_proxy_total_m).slot,
        same_arm_proxy_range_a_m=max(a) - min(a),
        same_arm_proxy_range_b_m=max(b) - min(b),
        action_move_distinct_counts=len({round(w.original_action_move_m, 9) for w in worlds}),
    )
