"""Offline factorial analysis of the unchanged evidence-use owner; no selection."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from experiments import self_world_cognitive_evidence_use as gate
from experiments import self_world_host_two_axis as host
from experiments.self_world_metadata_ablation import digest

KINDS = ("EXPLAIN_OBSERVED", "ASSESS_FORECAST")
COSTS = (0.0, 0.5)
MORE = "REQUEST_MORE_EVIDENCE"
MODEL_NECESSITY = "MODEL_NECESSITY_UNDETERMINED"


@dataclass(frozen=True, slots=True)
class FactorialRecord:
    """Host-private analysis envelope. Only candidates.request is model-facing."""

    case_id: str
    epoch: str
    goal: gate.GoalSpec
    host_record: dict
    candidates: gate.EvidenceUseCandidates


def _require(condition, message):
    if not condition:
        raise gate.EvidenceUseBlocked(message)


def _strings(value):
    if isinstance(value, str):
        yield value
        try:
            decoded = json.loads(value)
        except ValueError:
            return
        if not isinstance(decoded, str):
            yield from _strings(decoded)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)


def check_redaction(request, record):
    """Fixed DEV pseudo-provenance is allowed; real custody is never projected."""
    projected = asdict(request)
    strings = tuple(_strings(projected))
    raw = record["observation"]
    protected = list(record["binding"].values()) + [
        raw["source_bound_digest"],
        record["prediction"]["source_bound_review_digest"],
        *raw["observation_provenance"].values(),
        *raw["observation_source"].values(),
        *[x["entity_ref"] for x in raw["selected_positive_observations"]],
    ]
    # Case class/epoch are public categories; numeric seq is not an identity
    # string. Opaque identities/digests and source request IDs remain private.
    public = {record["binding"][k] for k in ("case_id", "source_class", "epoch")}
    for item in protected:
        if isinstance(item, str) and item and item not in public:
            _require(item not in strings, "host identity/provenance leaked")
            if len(item) > 1:
                _require(all(item not in s for s in strings), "host custody substring leaked")
    for key in ("entity_ref", "source_receipt_sha256", "source_bound_digest",
                "source_bound_review_digest", "self_id", "session_id", "epoch_id"):
        _require(key not in strings, "host-only key leaked")


def _normalized_request(row):
    if row.candidates.request is None:
        return None
    result = asdict(row.candidates.request)
    result.pop("request_id")
    goal = json.loads(result["context"][0]["value_json"])
    goal.pop("kind")
    result["context"][0]["value_json"] = goal
    return result


def audit_factorial(rows):
    """Check orthogonality and exact cost delta; never choose or score a strategy.

    Records must originate from collect_factorial's fresh strict reader.
    This comparison is an analysis invariant, not an independent source issuer.
    """
    expected_keys = {(case, epoch, kind, cost) for case in host.probe.CASE_IDS
                     for epoch in ("prior", "following")
                     for kind in KINDS for cost in COSTS}
    indexed = {}
    request_ids = []
    for row in rows:
        _require(type(row) is FactorialRecord, "untyped factorial record")
        g, r = row.goal, row.candidates
        _require(type(g) is gate.GoalSpec and g.importance == 2, "invalid factorial goal")
        key = (row.case_id, row.epoch, g.kind, g.max_additional_cost)
        _require(key in expected_keys and key not in indexed, "foreign/duplicate factorial cell")
        indexed[key] = row
        record = row.host_record
        _require(record["binding"]["case_id"] == row.case_id
                 and record["binding"]["epoch"] == row.epoch, "foreign cell identity")
        gate._checked_record(record, r.custody_manifest["source_digest"])
        _require(r.custody_manifest["binding"] == record["binding"]
                 and r.custody_manifest["observation_digest"]
                 == record["observation"]["source_bound_digest"]
                 and r.custody_manifest["prediction_digest"]
                 == record["prediction"]["source_bound_review_digest"], "custody substitution")
        observed, prediction = record["observation"], record["prediction"]
        matched = gate._matched_scope(record)
        eligible = tuple(k for k in gate.CHOICES if (
            k == "USE_CURRENT_POSITIVE" and observed["positive_selected_count"] > 0
            or k == "USE_MATCHED_FORECAST_SCOPE" and matched is not None
            or k in (MORE, "WITHHOLD_UNSUPPORTED_CLAIM")))
        available = tuple(k for k in eligible if k != MORE or g.max_additional_cost >= 0.5)
        _require(r.admissible == eligible and r.available == available, "eligibility/cost mutation")
        _require(r.custody_manifest["admissible"] == eligible
                 and r.custody_manifest["available"] == available, "custody candidate mutation")
        _require((r.model_calls, r.world_actions, r.memory_writes, r.s10_updates)
                 == (0, 0, 0, 0) and r.scope == gate.SCOPE, "authority changed")
        if len(available) < 2:
            _require(r.status == "DEFER" and r.request is None
                     and r.request_sha256 is None, "DEFER bypassed two-choice bound")
        else:
            _require(r.status == "READY" and r.request is not None, "missing typed request")
            request = r.request
            _require(r.request_sha256 == digest(asdict(request)), "request digest mutation")
            expected_id = (f"w4-coguse-{host.probe.CASE_IDS.index(row.case_id)}-{row.epoch}-"
                           f"{g.kind.lower()}-{g.importance}-{g.max_additional_cost:g}")
            _require(request.request_id == expected_id, "request ID substitution")
            request_ids.append(request.request_id)
            _require(tuple(c.choice_id for c in request.choices) == available, "choice mutation")
            _require(json.loads(request.context[0].value_json) == asdict(g), "goal/cost swap")
            projected = json.loads(request.context[1].value_json)
            _require(projected["positive_selected_count"] == observed["positive_selected_count"]
                     and projected["review_status"] == prediction["review_status"]
                     and projected["matched_scope"] == matched, "projected fact mutation")
            positives = [{k: p[k] for k in ("label", "position", "distance_m", "visible_action")}
                         for p in observed["selected_positive_observations"]]
            _require(projected["current_positive"] == positives, "positive observation mutation")
            _require(projected["candidate_costs"] == {
                k: 0.5 if k == MORE else 0.0 for k in available}, "candidate cost mutation")
            check_redaction(request, record)
    _require(set(indexed) == expected_keys, "incomplete factorial matrix")
    _require(len(request_ids) == len(set(request_ids)), "request ID collision")
    for case in host.probe.CASE_IDS:
        for epoch in ("prior", "following"):
            group = [indexed[case, epoch, kind, cost] for kind in KINDS for cost in COSTS]
            _require(all(r.host_record == group[0].host_record for r in group), "source truth changed")
            _require(all(r.candidates.admissible == group[0].candidates.admissible
                         for r in group), "Goal changed admissibility")
            for cost in COSTS:
                a, b = (indexed[case, epoch, kind, cost] for kind in KINDS)
                _require(a.candidates == b.candidates if a.candidates.request is None else
                         (a.candidates.custody_manifest == b.candidates.custody_manifest
                          and a.candidates.status == b.candidates.status
                          and _normalized_request(a) == _normalized_request(b)),
                         "Goal changed host facts/availability/request outside goal and ID")
            for kind in KINDS:
                low, high = (indexed[case, epoch, kind, cost].candidates for cost in COSTS)
                _require(set(high.available) - set(low.available) == {MORE}
                         and set(low.available) <= set(high.available), "unexplained cost delta")
    ready = sum(r.candidates.status == "READY" for r in rows)
    _require((ready, len(rows) - ready) == (30, 10), "registered count hypothesis failed")
    return {"conditions": len(rows), "READY": ready, "DEFER": len(rows) - ready,
            "goal_pairs": 20, "cost_pairs": 20, "model_necessity": MODEL_NECESSITY,
            "scope": gate.SCOPE, "strategy_selections": 0}


def collect_factorial(source_root, source_pins):
    """Use original strict saved replay + original factories; never repair inputs."""
    _require(set(source_pins) == set(host.probe.CASE_IDS), "missing/foreign source pins")
    rows = []
    for case in host.probe.CASE_IDS:
        for epoch in ("prior", "following"):
            for kind in KINDS:
                for cost in COSTS:
                    goal = gate.GoalSpec(kind, 2, cost)
                    record = host.read_epoch(source_root, case_id=case, epoch=epoch,
                                             expected_source_digest=source_pins[case])
                    candidates = gate.prepare_evidence_use(
                        source_root, case_id=case, epoch=epoch, goal=goal,
                        expected_source_digest=source_pins[case], claimed_record=record)
                    rows.append(FactorialRecord(case, epoch, goal, record, candidates))
    audit_factorial(rows)
    return tuple(rows)
