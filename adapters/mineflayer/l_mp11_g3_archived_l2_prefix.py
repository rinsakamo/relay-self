"""Read-only L2 context from an ARCHIVED MP11 G3 postrun summary.

This is not online evidence. The full archived report was produced *after*
all three real Actions; prefix slicing only demonstrates the data boundary
needed for a future live L2 bridge. Never grant S49/Memory/L1/L0 authority.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Callable

from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionDatum,
    OpenCognitionRequest,
    OpenCognitionResult,
)

G3_RUN = 41289358266
G3_EXECUTING_HEAD = "38e19c367eb6ef16e1f2cdef9a0b544128c6a762"
G3_PAPER_SHA = "22d867d4efdb17403dd6105bfdd5284d23bf0c65df35f054606af7e1f4516d03"
G3_NODE_SHA = "4dd24b895dbd57ddb45366d0c730ea6b5ef3878f0f693dcc2e63951a544f0b54"
G3_ZIP_SHA = "c58e423fecbb9bbbc70e86790b912330b756e1657a9422942d1b6500a904dc59"

NEXT_TESTS = frozenset({
    "CHECK_INITIAL_VELOCITY",
    "CHECK_PAPER_CALLBACK_PHASE",
    "VARY_INPUT_DURATION",
    "COMPARE_GRASS_AND_ICE",
})
MODEL_FAMILIES = frozenset({
    "SINGLE_DECAY", "PHASE_DEPENDENT", "SURFACE_DEPENDENT",
    "INITIAL_SPEED_DEPENDENT", "OTHER_BOUNDED",
})
RECONSIDERATIONS = frozenset({
    "KEEP_UNRESOLVED", "QUESTION_APPLICABILITY",
    "PROPOSE_STRUCTURAL_REVISION", "ABSTAIN",
})
SOURCE_STATUS = "ARCHIVED_G3_POSTRUN_SUMMARY_PREFIX_ONLY_NOT_LIVE_SOURCE"


class G3PrefixRejected(ValueError):
    """Invalid archived evidence, prefix visibility, or L2 hypothesis."""


@dataclass(frozen=True, slots=True)
class PriorTrial:
    ordinal: int
    action_id: str
    wait_first_tick: int
    wait_last_tick: int
    observed_wait_total_m: float
    observed_first_wait_m: float
    cheap_zero_next_motion_mae_m: float
    fixed_slope_next_motion_mae_m: float
    floor: str = "GRASS_BLOCK"
    input_action: str = "MOVE_BACKWARD"
    input_duration_variation_proven: bool = False
    physical_cause_identified: bool = False


@dataclass(frozen=True, slots=True)
class ArchivedPrefix:
    world_uuid: str
    subject_uuid: str
    session_id: str
    visible_count: int
    previous_trials: tuple[PriorTrial, ...]
    report_sha256: str
    source_status: str = SOURCE_STATUS
    original_bytes_reauthenticated: bool = False
    physically_online_at_prefix: bool = False


@dataclass(frozen=True, slots=True)
class ArchivedL2Hypothesis:
    report_sha256: str
    visible_count: int
    referenced_prior_ordinals: tuple[int, ...]
    reconsideration: str
    model_family: str
    next_test: str
    explanation: str
    falsification_test: str
    predicted_wait_total_m: float | None
    provider_source: str
    proposal_sha256: str
    source_status: str = "ARCHIVED_G3_L2_SHADOW_HYPOTHESIS_UNTESTED"
    executable_action: bool = False
    world_mutation_allowed: bool = False
    learning_admissions: int = 0
    l0_promotions: int = 0


def _valid_sha(value: object) -> bool:
    return (
        isinstance(value, str) and len(value) == 64
        and all(x in "0123456789abcdef" for x in value)
    )


def _finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _sha(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def parse_g3_readback(data: object) -> tuple[PriorTrial, ...]:
    """Validate pinned archived independent readback: never original raw bytes."""
    if not isinstance(data, dict):
        raise G3PrefixRejected("archived readback must be an object")
    b = data.get("source_binding")
    a = data.get("original_artifact")
    e = data.get("evidence_limits")
    review = data.get("independent_review")
    if not all(isinstance(x, dict) for x in (b, a, e, review)):
        raise G3PrefixRejected("missing original audit scope")
    if (
        data.get("schema") !=
        "MP11_G3_SAME_PAPER_WORLD_THREE_S49_S16_AND_S50_ORIGINALS_INDEPENDENT_READBACK_V1"
        or data.get("github_run") != G3_RUN
        or data.get("executing_head") != G3_EXECUTING_HEAD
        or data.get("job_conclusion") != "SUCCESS"
        or data.get("actual_world_attempts") != 1
        or data.get("retry_count") != 0
        or a.get("paper_stdout_sha256") != G3_PAPER_SHA
        or a.get("node_stdout_sha256") != G3_NODE_SHA
        or a.get("zip_sha256") != G3_ZIP_SHA
        or review.get("zip_and_file_sha256_recomputed") is not True
        or review.get("paper_world_uuid_stable_and_true_source") is not True
        or review.get("paper_local_predictions_original_not_host_afterfact") is not True
        or review.get("no_s15_duplicate_or_s16_unknown") is not True
        or review.get("w3_original_sha_matches_w3_capture_receipt") is not True
        or b.get("original_s15_clear_count") != 3
        or b.get("original_s16_outcome_count") != 3
        or b.get("paper_wait_tick_count") != 24
        or b.get("paper_frozen_pre_next_tick_prediction_count") != 21
        or b.get("all_surfaces") != "GRASS_BLOCK"
        or b.get("all_input_motions") != "MOVE_BACKWARD"
        or b.get("real_gemma_calls") != 0
        or b.get("l2_selected_experiment_count") != 0
        or b.get("learning_admission_count") != 0
        or e.get("real_llm_l2_experiment_choice") != "NOT_RUN"
        or e.get("model_predictive_gain") != "NOT_ESTABLISHED"
        or e.get("controlled_input_duration_variation", "NOT_RUN") == "VERIFIED"
        or e.get("qualification") != "NO_GO"
        or e.get("science") != "NOT_RUN"
    ):
        raise G3PrefixRejected("unverified or strengthened G3 postrun claims")
    for key in ("paper_world_uuid", "paper_subject_uuid", "native_session_id"):
        val = b.get(key)
        if not isinstance(val, str) or not 0 < len(val) <= 128:
            raise G3PrefixRejected("missing original identity")
    ids = b.get("original_s49_action_ids")
    trials = data.get("trials")
    if (
        not isinstance(ids, list) or len(ids) != 3
        or len(set(ids)) != 3 or not all(isinstance(x, str) and x for x in ids)
        or not isinstance(trials, list) or len(trials) != 3
    ):
        raise G3PrefixRejected("missing ordered real original Action list")
    seen = []
    last_tick = -1
    for i, (t, action_id) in enumerate(zip(trials, ids), 1):
        if not isinstance(t, dict):
            raise G3PrefixRejected("missing real trial")
        ticks = t.get("paper_wait_ticks")
        total = t.get("wait8_total_m")
        first = t.get("first_wait_displacement_m")
        mae = t.get("prequential_mae_m")
        cheap = t.get("same_information_zero_baseline_mae_m")
        if (
            t.get("ordinal") != i or t.get("action_id") != action_id
            or not isinstance(ticks, list) or len(ticks) != 2
            or not all(type(x) is int for x in ticks)
            or ticks[0] <= last_tick or ticks[1] != ticks[0]+7
            or not all(_finite(x) for x in (total, first, mae, cheap))
            or first > total + 1e-9 or not _finite(t.get("native_movement_m"))
            or t.get("prequential_fixed_slope") != 0.65
            or not mae > cheap  # retain the real negative control
        ):
            raise G3PrefixRejected("invalid or retrofitted G3 trial evidence")
        last_tick = ticks[1]
        seen.append(PriorTrial(
            ordinal=i, action_id=action_id, wait_first_tick=ticks[0],
            wait_last_tick=ticks[1], observed_wait_total_m=float(total),
            observed_first_wait_m=float(first),
            cheap_zero_next_motion_mae_m=float(cheap),
            fixed_slope_next_motion_mae_m=float(mae),
        ))
    return tuple(seen)


def freeze_archived_prefix(data: dict, *, visible_count: int) -> ArchivedPrefix:
    """Expose only completed earlier trials despite full postrun report access."""
    if type(visible_count) is not int or not 0 <= visible_count <= 2:
        raise G3PrefixRejected("only pre-next-action 0..2 prefixes permitted")
    trials = parse_g3_readback(data)
    b = data["source_binding"]
    return ArchivedPrefix(
        world_uuid=b["paper_world_uuid"],
        subject_uuid=b["paper_subject_uuid"],
        session_id=b["native_session_id"],
        visible_count=visible_count,
        previous_trials=trials[:visible_count],
        report_sha256=_sha(data),
    )


def make_l2_request(prefix: ArchivedPrefix) -> OpenCognitionRequest:
    if (
        type(prefix) is not ArchivedPrefix
        or prefix.source_status != SOURCE_STATUS
        or prefix.physically_online_at_prefix
        or prefix.original_bytes_reauthenticated
        or not _valid_sha(prefix.report_sha256)
        or prefix.visible_count != len(prefix.previous_trials)
        or not 0 <= prefix.visible_count <= 2
        or any(t.ordinal != i+1 for i, t in enumerate(prefix.previous_trials))
        or any(t.floor != "GRASS_BLOCK" or t.input_action != "MOVE_BACKWARD"
               or t.input_duration_variation_proven or t.physical_cause_identified
               for t in prefix.previous_trials)
    ):
        raise G3PrefixRejected("untrusted archived G3 prefix")
    return OpenCognitionRequest(
        request_id=f"mp11-g3-archived:{prefix.report_sha256[:16]}:before-{prefix.visible_count + 1}",
        instruction=(
            "You are fallible L2 scientific cognition. The following is a "
            "POSTRUN archive sliced to simulate what an earlier epoch could see, "
            "NOT actual live observation. The three physical G3 Actions all used "
            "GRASS/MOVE_BACKWARD and did not vary controlled input duration. "
            "Do NOT claim a mechanism was established or that your output caused "
            "an earlier Action. Return EXACTLY one JSON object with keys: "
            "referenced_prior_ordinals (array of prior trial numbers only), "
            "reconsideration (KEEP_UNRESOLVED, QUESTION_APPLICABILITY, "
            "PROPOSE_STRUCTURAL_REVISION, ABSTAIN), model_family "
            "(SINGLE_DECAY, PHASE_DEPENDENT, SURFACE_DEPENDENT, "
            "INITIAL_SPEED_DEPENDENT, OTHER_BOUNDED), next_test "
            "(CHECK_INITIAL_VELOCITY, CHECK_PAPER_CALLBACK_PHASE, "
            "VARY_INPUT_DURATION, COMPARE_GRASS_AND_ICE), explanation, "
            "falsification_test, predicted_wait_total_m (number 0..3 or null). "
            "These are UNAPPROVED research ideas: do not issue commands, "
            "grant an Action, claim learning, or change World physics. "
            "State uncertainty; future measurement can contradict your proposal."
        ),
        intent_id="investigate-g3-motion-discrepancy",
        focus="L2_ARCHIVED_G3_CAUSAL_HYPOTHESIS_PREVIEW_ONLY",
        context=(
            CognitionDatum.from_value(
                "source_limitations",
                {
                    "status": SOURCE_STATUS,
                    "actual_gemma_calls_in_original_run": 0,
                    "physical_online_proposal": False,
                    "controlled_conditions_varied": False,
                    "physical_cause_identified": False,
                    "original_paper_sha256": G3_PAPER_SHA,
                    "original_node_sha256": G3_NODE_SHA,
                    "source_report_sha256": prefix.report_sha256,
                    "original_world_uuid": prefix.world_uuid,
                    "original_subject_uuid": prefix.subject_uuid,
                    "original_session_id": prefix.session_id,
                    "visible_prior_trials": prefix.visible_count,
                    "future_trial_values_in_input": False,
                    "next_test_approved_by_owner": False,
                    "learning_admitted": False,
                },
                Provenance("mp11.g3.archived.report.readonly", prefix.report_sha256),
            ),
            CognitionDatum.from_value(
                "prior_completed_trials_only",
                [asdict(x) for x in prefix.previous_trials],
                Provenance("mp11.g3.archived.prefix", f"{prefix.report_sha256}:{prefix.visible_count}"),
            ),
        ),
    )


def shadow_l2_preview(
    prefix: ArchivedPrefix,
    open_provider: Callable[[OpenCognitionRequest], OpenCognitionResult],
) -> ArchivedL2Hypothesis:
    """Type-check a real RelayEngine OPEN API result; provider may be fake."""
    request = make_l2_request(prefix)
    if not callable(open_provider):
        raise G3PrefixRejected("explicit OPEN provider required; no fallback")
    result = open_provider(request)
    if (
        type(result) is not OpenCognitionResult
        or result.request_id != request.request_id
        or not isinstance(result.provenance, Provenance)
        or not result.provenance.source.strip()
        or not result.text or len(result.text.encode("utf-8")) > 2500
    ):
        raise G3PrefixRejected("missing exact bounded L2 OPEN result")
    try:
        raw = json.loads(result.text)
    except (ValueError, TypeError) as exc:
        raise G3PrefixRejected("invalid L2 JSON") from exc
    keys = {
        "referenced_prior_ordinals", "reconsideration", "model_family",
        "next_test", "explanation", "falsification_test",
        "predicted_wait_total_m",
    }
    if not isinstance(raw, dict) or set(raw) != keys:
        raise G3PrefixRejected("L2 proposal has excess or missing fields")
    ordinals = raw["referenced_prior_ordinals"]
    if (
        type(ordinals) is not list or len(ordinals) > prefix.visible_count
        or any(type(x) is not int or x < 1 or x > prefix.visible_count
               for x in ordinals)
        or len(set(ordinals)) != len(ordinals)
        or ordinals != sorted(ordinals)
        or type(raw["reconsideration"]) is not str
        or raw["reconsideration"] not in RECONSIDERATIONS
        or type(raw["model_family"]) is not str
        or raw["model_family"] not in MODEL_FAMILIES
        or type(raw["next_test"]) is not str
        or raw["next_test"] not in NEXT_TESTS
        or any(not isinstance(raw[k], str) or not 16 <= len(raw[k]) <= 360
               for k in ("explanation", "falsification_test"))
    ):
        raise G3PrefixRejected("future-leaking, unbounded or unfalsifiable proposal")
    predicted = raw["predicted_wait_total_m"]
    if predicted is not None and (
        type(predicted) not in (float, int)
        or not math.isfinite(predicted) or not 0 <= predicted <= 3
    ):
        raise G3PrefixRejected("invalid prospective prediction")
    if (
        raw["reconsideration"] in (
            "QUESTION_APPLICABILITY", "PROPOSE_STRUCTURAL_REVISION",
        ) and not ordinals
    ):
        raise G3PrefixRejected("no available evidence for revision candidate")
    fields = dict(
        report_sha256=prefix.report_sha256,
        visible_count=prefix.visible_count,
        referenced_prior_ordinals=tuple(ordinals),
        reconsideration=raw["reconsideration"],
        model_family=raw["model_family"],
        next_test=raw["next_test"],
        explanation=raw["explanation"],
        falsification_test=raw["falsification_test"],
        predicted_wait_total_m=float(predicted) if predicted is not None else None,
        provider_source=result.provenance.source,
    )
    return ArchivedL2Hypothesis(**fields, proposal_sha256=_sha(fields))
