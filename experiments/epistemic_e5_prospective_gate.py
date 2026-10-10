"""Lane A E5: read-only prospective paired World receipt admission.

No Minecraft/Node/LLM/GPU launch, no Action issuance, no ability to authenticate
a native World source. Even structurally valid LIVE-CLAIM JSON remains UNATTESTED.
Never interpret Action OUTCOME as task success or a measured value-of-information.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.epistemic_e3_s29_integration import plan_epistemic

VERSION = "AC-A-E5-PHYSICAL-ADMISSION-GRAND-NULL-v1"
MANIFEST_SHA256 = "2ede0bd82ab6c8ada2557a5477f9c6d6084e6cbae50a5e1a6b8ffc6d1626e2f3"
MANIFEST = {
    "version": VERSION,
    "base_e4": "b49a573ddd8b916a8b6b184ab065649275dc5a51",
    "source_s29": "5424669a09a69eb364da559e38b9999fee7b6680",
    "arms": ["NO_OBSERVE", "CHEAP_EXACT", "OBSERVE"],
    "distances_cm": [20, 180],
    "price_quarters": [1, 4],
    "arm_orders": [
        ["NO_OBSERVE", "CHEAP_EXACT", "OBSERVE"],
        ["CHEAP_EXACT", "OBSERVE", "NO_OBSERVE"],
        ["OBSERVE", "NO_OBSERVE", "CHEAP_EXACT"],
    ],
    "expected_trials": 36,
    "world_reset": "independent session and reset identity every arm, identical "
                   "declared seed and scenario inside each block",
    "observation_policy": "E0 may use only stipulated prior and declared price; "
                          "policy source read only if probe chosen",
    "evaluator": "separate strictly post-decision independent observation; "
                 "unavailable evidence not interpreted as safety",
    "outcome": "S15/S16 known OUTCOME vs UNKNOWN vs UNAVAILABLE must remain distinct",
    "measurements": [
        "elapsed_ms", "probe_ms", "damage_points", "movement_m",
        "hunger_delta_optional", "energy_joules_optional",
    ],
    "analysis": "paired raw physical outcomes only when independently authenticated; "
                "exact cheap comparator null",
    "physical_authorization": "separate prospective opt-in required; "
                              "no physical execution in this gate",
    "claim_ceiling": "E5_OFFLINE_RECEIPT_ADMISSION_CI_PASS / REAL_WORLD_NOT_RUN / "
                     "PHYSICAL_EFFECT_UNDETERMINED",
}
_ARM_ORDER = tuple(tuple(v) for v in MANIFEST["arm_orders"])
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")


class E5Rejected(ValueError):
    """Missing, misleading, cross-trial or forged-in-structure evidence."""


@dataclass(frozen=True, slots=True)
class TrialSpec:
    trial_id: str
    block_id: str
    distance_cm: int
    price_quarters: int
    order_index: int
    arm: str
    world_seed: int


@dataclass(frozen=True, slots=True)
class E5Audit:
    classification: str
    physical_effect: str
    manifest_sha256: str
    expected_trials: int
    checked_trials: int
    checked_blocks: int
    observed_policy_probes: int
    simulated_actions: int
    unresolved_actions: int
    physically_authenticated: bool
    no_observation_comparator_present: bool
    cheap_exact_comparator_present: bool


def digest(manifest: object = MANIFEST) -> str:
    raw = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def planned_trials() -> tuple[TrialSpec, ...]:
    if digest() != MANIFEST_SHA256:
        raise E5Rejected("prospective E5 manifest drift")
    result: list[TrialSpec] = []
    for distance in MANIFEST["distances_cm"]:
        for price in MANIFEST["price_quarters"]:
            for order_idx, arms in enumerate(_ARM_ORDER):
                block = f"e5-d{distance}-p{price}-o{order_idx}"
                seed = 510_000 + 100 * distance + 10 * price + order_idx
                for position, arm in enumerate(arms):
                    result.append(TrialSpec(
                        trial_id=f"{block}-a{position}", block_id=block,
                        distance_cm=distance, price_quarters=price,
                        order_index=position, arm=arm, world_seed=seed,
                    ))
    if len(result) != 36 or len(set(v.trial_id for v in result)) != 36:
        raise E5Rejected("frozen denominator/order invalid")
    return tuple(result)


def _keys(obj: object, expected: set[str], context: str) -> dict[str, Any]:
    if type(obj) is not dict or set(obj) != expected:
        raise E5Rejected(f"{context} must have exact pre-registered keys")
    return obj


def _int(value: object, name: str, *, least: int = 0) -> int:
    if type(value) is not int or value < least:
        raise E5Rejected(f"{name}: strict nonnegative integer required")
    return value


def _real(value: object, name: str, *, allow_none: bool = False) -> float | None:
    if value is None and allow_none:
        return None
    if type(value) not in (int, float) or not (0 <= value < 1e12):
        raise E5Rejected(f"{name}: bounded finite nonnegative number required")
    return float(value)


def _id(value: object, name: str) -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        raise E5Rejected(f"{name}: invalid unique source identifier")
    return value


def _hash(value: object, name: str) -> None:
    if type(value) is not str or not _HEX64.fullmatch(value):
        raise E5Rejected(f"{name}: expected exact SHA256 form; not authentication")


TRIAL_KEYS = {
    "trial_id", "block_id", "arm", "world_seed",
    "session_id", "action_session_id", "reset_id",
    "source_kind", "policy_inputs",
    "decision_source", "first_distance_cm", "second_distance_cm",
    "policy_request_ids", "policy_probe_seqs", "evaluator_request_id",
    "start_ns", "first_probe_ns", "second_probe_ns", "decision_ns",
    "action_issue_ns", "action_terminal_ns", "evaluator_ns",
    "selected_candidate", "action_owner_state", "world_result", "reason_code",
    "elapsed_ms", "probe_ms", "evaluator_ms",
    "health_before", "health_after", "damage_points", "movement_m",
    "hunger_delta", "energy_joules",
    "server_log_sha256", "adapter_log_sha256", "receipt_sha256",
}
BUNDLE_KEYS = {"manifest_sha256", "source_kind", "trials"}
POLICY_INPUT_KEYS = {"price_quarters", "prior_ref"}
_REASON = {
    "OUTCOME": ("EXECUTED", "observed_execution"),
    "UNKNOWN": ("FAILED", "adapter_failure_consequence_unknown"),
    "UNAVAILABLE": ("UNDETERMINED", "world_consequence_undetermined"),
}


def _check_trial(raw: dict[str, Any], spec: TrialSpec, kind: str) -> tuple[int, bool, bool]:
    t = _keys(raw, TRIAL_KEYS, spec.trial_id)
    if t["trial_id"] != spec.trial_id or t["block_id"] != spec.block_id:
        raise E5Rejected("cross-block, reordered or replayed trial ID")
    if t["arm"] != spec.arm or _int(t["world_seed"], "world seed") != spec.world_seed:
        raise E5Rejected("world/arm assignment drift")
    if t["source_kind"] != kind:
        raise E5Rejected("source kind mixing within receipt bundle")
    for field in ("session_id", "reset_id", "evaluator_request_id"):
        _id(t[field], field)
    for field in ("server_log_sha256", "adapter_log_sha256", "receipt_sha256"):
        _hash(t[field], field)
    policy = _keys(t["policy_inputs"], POLICY_INPUT_KEYS, "E0 policy inputs")
    if policy != {"price_quarters": spec.price_quarters, "prior_ref": "uniform-nearfar-v1"}:
        raise E5Rejected("E0 must see price/prior ONLY, not hidden future World")
    price_choice = plan_epistemic(spec.price_quarters).first
    observed = spec.arm == "OBSERVE" or (
        spec.arm == "CHEAP_EXACT" and price_choice == "OBSERVE"
    )
    expect_probes = 2 if observed else 0
    ids = t["policy_request_ids"]
    seqs = t["policy_probe_seqs"]
    if (
        type(ids) is not list or type(seqs) is not list
        or len(ids) != expect_probes or len(seqs) != expect_probes
    ):
        raise E5Rejected("policy reads differ from frozen intervention/cheap comparator")
    if observed:
        for name in ids:
            _id(name, "correlated request")
        if ids[0] == ids[1] or t["evaluator_request_id"] in ids:
            raise E5Rejected("policy or evaluator request ID reuse")
        a, b = (_int(v, "probe sequence", least=1) for v in seqs)
        if a >= b:
            raise E5Rejected("S29 second correlated probe must have a later sequence")
        if (
            t["decision_source"] != "S29_CORRELATED"
            or _int(t["first_distance_cm"], "first source distance") != 180
            or _int(t["second_distance_cm"], "second source distance")
            != spec.distance_cm
        ):
            raise E5Rejected("source identity/geometry contradicts S29/S24 decision")
    elif (
        t["decision_source"] != "PRIOR_ONLY"
        or t["first_distance_cm"] is not None
        or t["second_distance_cm"] is not None
    ):
        raise E5Rejected("unobserved future distance leaked into cheap E0")
    selected = (
        "MOVE_AWAY" if observed and spec.distance_cm == 20 else "WAIT"
    )
    if t["selected_candidate"] != selected:
        raise E5Rejected("fixed S24 policy or non-observation route mismatch")

    start = _int(t["start_ns"], "start time", least=1)
    decision = _int(t["decision_ns"], "decision time", least=1)
    evaluated = _int(t["evaluator_ns"], "evaluator time", least=1)
    if not start < decision < evaluated:
        raise E5Rejected("decision/evaluator temporal order invalid")
    if _int(t["elapsed_ms"], "elapsed ms") != (evaluated - start) // 1_000_000:
        raise E5Rejected("reported duration not derived from source timestamp")
    if observed:
        p1 = _int(t["first_probe_ns"], "first source time", least=1)
        p2 = _int(t["second_probe_ns"], "second source time", least=1)
        if not start < p1 < p2 < decision:
            raise E5Rejected("source must be consumed in proper two-probe order")
        if _real(t["probe_ms"], "policy probe duration") <= 0:
            raise E5Rejected("a policy read must record nonzero cost")
    elif (
        t["first_probe_ns"] is not None
        or t["second_probe_ns"] is not None
        or t["probe_ms"] != 0
    ):
        raise E5Rejected("NO_OBSERVE must have no policy sensing/cost")
    _real(t["evaluator_ms"], "evaluator duration")
    before = _real(t["health_before"], "health before")
    after = _real(t["health_after"], "health after", allow_none=True)
    if before > 20 or (after is not None and after > 20):
        raise E5Rejected("native Minecraft health outside capped bound")
    for field in ("damage_points", "movement_m", "hunger_delta", "energy_joules"):
        _real(t[field], field, allow_none=True)
    has_action = selected == "MOVE_AWAY"
    state = t["action_owner_state"]
    world = t["world_result"]
    reason = t["reason_code"]
    if not has_action:
        if (
            t["action_session_id"] is not None
            or t["action_issue_ns"] is not None
            or t["action_terminal_ns"] is not None
            or (state, world, reason) != ("NONE", "NONE", "NONE")
        ):
            raise E5Rejected("WAIT must not create Action; no phantom OUTCOME")
    else:
        _id(t["action_session_id"], "distinct S15 World session")
        if t["action_session_id"] == t["session_id"]:
            raise E5Rejected("simulated S15/S29 distinct World sessions collapsed")
        issue = _int(t["action_issue_ns"], "Action issue", least=1)
        if not decision < issue < evaluated:
            raise E5Rejected("ISSUE must follow decision and precede audit")
        if state == "ISSUED":
            if (
                (world, reason) != _REASON["UNAVAILABLE"]
                or t["action_terminal_ns"] is not None
            ):
                raise E5Rejected("UNAVAILABLE cannot turn ISSUED into terminal")
        else:
            if state not in ("OUTCOME", "UNKNOWN"):
                raise E5Rejected("invalid terminal Action state")
            term = _int(t["action_terminal_ns"], "Action terminal time", least=1)
            if not issue < term < evaluated or (world, reason) != _REASON[state]:
                raise E5Rejected("terminal disposition must be owner-conformant")
        if state == "OUTCOME" and (
            after is None or t["damage_points"] is None
            or t["movement_m"] is None
        ):
            raise E5Rejected("known outcome still requires actual evaluator measures")
    unresolved = has_action and state in ("UNKNOWN", "ISSUED")
    return expect_probes, has_action, unresolved


def audit_bundle(payload: object) -> E5Audit:
    if digest() != MANIFEST_SHA256:
        raise E5Rejected("frozen source manifest changed")
    b = _keys(payload, BUNDLE_KEYS, "E5 receipt bundle")
    if b["manifest_sha256"] != MANIFEST_SHA256:
        raise E5Rejected("receipt does not match frozen experiment")
    kind = b["source_kind"]
    if kind not in ("SYNTHETIC", "CLAIMED_LIVE") or type(kind) is not str:
        raise E5Rejected("source must not disguise a synthetic replay as live")
    trials = b["trials"]
    specs = planned_trials()
    if type(trials) is not list or len(trials) != len(specs):
        raise E5Rejected("all 36 prospectively planned trials required")
    sessions: set[str] = set()
    resets: set[str] = set()
    receipts: set[str] = set()
    ids: set[str] = set()
    probes = actions = unresolved = 0
    for item, spec in zip(trials, specs, strict=True):
        count, action, missing = _check_trial(item, spec, kind)
        if item["session_id"] in sessions or item["reset_id"] in resets:
            raise E5Rejected("cross-arm session/reset reuse instead of matched independent reset")
        sessions.add(item["session_id"])
        resets.add(item["reset_id"])
        if item["receipt_sha256"] in receipts:
            raise E5Rejected("identical receipt hash across independent trials")
        receipts.add(item["receipt_sha256"])
        new_ids = item["policy_request_ids"] + [item["evaluator_request_id"]]
        for value in new_ids:
            if value in ids:
                raise E5Rejected("cross-trial correlation/evaluator request replay")
            ids.add(value)
        probes += count
        actions += int(action)
        unresolved += int(missing)
    blocks = len(set(spec.block_id for spec in specs))
    if blocks != 12 or len(sessions) != 36 or len(resets) != 36:
        raise E5Rejected("matched 12-block independent source denominator invalid")
    # These are internal JSON logical checks only. Even a fake LIVE receipt with
    # plausible SHA256 fields is *not* independent physical authentication.
    return E5Audit(
        classification=(
            "OFFLINE_SYNTHETIC_STRUCTURE_VALID"
            if kind == "SYNTHETIC" else "UNATTESTED_PHYSICAL_CLAIM"
        ),
        physical_effect="UNDETERMINED",
        manifest_sha256=MANIFEST_SHA256,
        expected_trials=36, checked_trials=len(trials),
        checked_blocks=blocks, observed_policy_probes=probes,
        simulated_actions=actions, unresolved_actions=unresolved,
        physically_authenticated=False,
        no_observation_comparator_present=True,
        cheap_exact_comparator_present=True,
    )


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="E5 read-only receipt structural gate")
    option = parser.add_mutually_exclusive_group(required=True)
    option.add_argument("--plan", action="store_true", help="show frozen schedule")
    option.add_argument("--audit", type=Path, metavar="RECEIPT.json")
    args = parser.parse_args(argv)
    try:
        if args.plan:
            obj = {
                "manifest_sha256": MANIFEST_SHA256,
                "physical_run": "NOT_AUTHORIZED_OR_LAUNCHED",
                "trials": [vars_spec(v) for v in planned_trials()],
            }
        else:
            if not args.audit.is_file() or args.audit.stat().st_size > 2_000_000:
                raise E5Rejected("receipt file missing or outside 2MB bound")
            raw = json.loads(args.audit.read_text(encoding="utf-8"))
            obj = vars_audit(audit_bundle(raw))
    except (E5Rejected, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"classification": "REJECTED", "reason": str(exc)}))
        return 2
    print(json.dumps(obj, ensure_ascii=False, sort_keys=True))
    return 0


def vars_spec(v: TrialSpec) -> dict[str, object]:
    return {k: getattr(v, k) for k in v.__dataclass_fields__}


def vars_audit(v: E5Audit) -> dict[str, object]:
    return {k: getattr(v, k) for k in v.__dataclass_fields__}


if __name__ == "__main__":
    sys.exit(_main())
