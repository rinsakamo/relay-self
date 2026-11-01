"""MP12: genuine G3 Paper/S49 originals -> bounded READ-ONLY L2 shadow.

Post-run historical replay, NOT online experiment control. Never issues an
Action, changes source World, certifies a model weight file or admits learning.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from adapters.mineflayer.self_body_s50_l2_mp11_experiment import EXPERIMENTS, MODEL_FAMILIES
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionDatum,
    OpenCognitionRequest,
    OpenCognitionResult,
)
from tools.mp11_g3_paper_one_world_audit import review

_ALLOWED_ABILITY = frozenset({"UNKNOWN", "CONDITIONAL_HYPOTHESIS"})
_ALLOWED_FIELDS = frozenset({
    "experiment_id", "model_family", "explanation", "falsification_test",
    "predicted_wait_total_m", "capability_assessment", "ability_boundary_reason",
})


class MP12ShadowRejected(ValueError):
    """Unqualified physical source, uncontrolled model response or false autonomy."""


@dataclass(frozen=True, slots=True)
class OriginalExperience:
    ordinal: int
    action_id: str
    world_uuid: str
    subject_uuid: str
    session_id: str
    paper_wait_ticks: tuple[int, ...]
    paper_wait_motion_m: tuple[float, ...]
    actual_wait_total_m: float
    frozen_slope_065_mae_m: float
    cheap_zero_mae_m: float
    original_paper_prefix_sha256: str
    original_paper_prefix_lines: int
    surface: str = "GRASS_BLOCK"
    action: str = "MOVE_BACKWARD"
    input_duration_kind: str = "UNKNOWN_NOT_ATTESTED"
    effective_s15_clear_world_tick: str = "NOT_ATTESTED"


@dataclass(frozen=True, slots=True)
class ShadowProposal:
    source_round: int
    proposed_test_id: str
    model_family: str
    explanation: str
    falsification_test: str
    predicted_wait_total_m: float
    capability_assessment: str
    ability_boundary_reason: str
    source_prefix_sha256: str
    source_evidence_count: int
    provider_source: str
    proposal_sha256: str
    classification: str = "RETROSPECTIVE_L2_SHADOW_PROPOSAL_NOT_EXECUTED"
    action_authority: bool = False
    learning_admissions: int = 0


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json_sha(value: dict) -> str:
    return _sha(json.dumps(
        value,sort_keys=True,ensure_ascii=False,separators=(",",":"),
        allow_nan=False,
    ).encode())


def _read_bounded(path: Path, limit: int) -> bytes:
    if (not path.is_file() or path.is_symlink()
            or not 0 < path.stat().st_size <= limit):
        raise MP12ShadowRejected("missing, symlinked or oversized original physical file")
    return path.read_bytes()


def _fields(line: str) -> dict[str, str]:
    return dict(part.split("=",1) for part in line.split() if part.count("=")==1)


def _finite_float(value: str) -> float:
    f=float(value)
    if not math.isfinite(f) or f < 0:
        raise MP12ShadowRejected("nonfinite or negative Paper original scalar")
    return f


def load_original_experiences(root: Path) -> tuple[OriginalExperience, ...]:
    """Independently qualify FULL postrun G3 originals before prefix replay.

    The replay later sends only one available 8-tick trial at a time to L2;
    this does not imply that the model made the original G3 Action choices.
    """
    if not isinstance(root,Path) or not root.is_dir() or root.is_symlink():
        raise MP12ShadowRejected("original artifact directory required")
    report=json.loads(_read_bounded(root/"report.json",2_000_000))
    paper=_read_bounded(root/"paper-stdout-original.log",16_000_000)
    native=_read_bounded(root/"native-stdout/w3-node-stdout.raw.jsonl",32_000_000)
    native_receipt=json.loads(_read_bounded(
        root/"native-stdout/w3-node-stdout-receipt.json",100_000))
    if (native_receipt.get("status")!="COMPLETE_NODE_STDOUT"
            or native_receipt.get("stdout_sha256")!=_sha(native)
            or native_receipt.get("session_id")!=report.get("session_id")
            or native_receipt.get("eof_observed") is not True
            or native_receipt.get("shutdown_ack_count")!=1
            or native_receipt.get("process_exit_code")!=0
            or report.get("w3_node_stdout_capture")!=native_receipt):
        raise MP12ShadowRejected("original W3 native source unsealed or foreign")
    physical=review(report,paper)
    if (physical["original_paper_wait_samples"]!=24
            or physical["original_paper_prequential_frozen_pairs"]!=21
            or physical["actual_L2_model_calls"]!=0):
        raise MP12ShadowRejected("not an original G3 3-window, model-free World")
    lines=paper.splitlines(keepends=True)
    events=[(i,raw.decode("utf-8",errors="strict"),_fields(raw.decode("utf-8",errors="strict")))
            for i,raw in enumerate(lines)]
    markers=report["mp11_g3"]["paper_markers"]
    result=[]
    last_index=-1
    for ordinal,marker in enumerate(markers,1):
        def select(kind):
            return [(i,x) for i,line,x in events if kind+" marker_id="+marker+" " in line]
        waits=select("S50_DEV_WAIT_TICK")
        scores=select("S50_DEV_LOCAL_FORECAST_SCORE")
        next_phase=select("M02_DEV_S50_PHASE")
        if (len(waits)!=8 or len(scores)!=7 or len(next_phase)!=2
                or next_phase[0][1].get("phase")!="PRE_FORWARD"
                or next_phase[1][1].get("phase")!="POST_CLEAR"):
            raise MP12ShadowRejected("real Paper eight WAIT / seven score chronology absent")
        cut=max(i for i,_ in scores)
        if not last_index < next_phase[0][0] < cut:
            raise MP12ShadowRejected("future Paper marker leaked into source prefix")
        if ordinal<3:
            next_marker=markers[ordinal]
            future=min(i for i,line,_ in events
                       if "M02_DEV_S50_PHASE marker_id="+next_marker+" " in line)
            if cut>=future:
                raise MP12ShadowRejected("next experiment appears before current last score")
        actual=tuple(physical["per_action_motion_m"][ordinal-1])
        mse=[]
        for j,(_,score) in enumerate(scores,1):
            if (int(score["target_tick"])!=int(waits[j][1]["tick"])
                    or int(score["prior_tick"])!=int(waits[j-1][1]["tick"])):
                raise MP12ShadowRejected("fixed model Paper score tick mismatch")
            error=_finite_float(score["abs_error_m"])
            predicted=_finite_float(score["predicted_m"])
            observed=_finite_float(score["actual_m"])
            if (not math.isclose(observed,actual[j],abs_tol=1e-10)
                    or not math.isclose(
                        error,abs(predicted-observed),abs_tol=1e-10)):
                raise MP12ShadowRejected("recomputed Paper forecast error mismatch")
            mse.append(error)
        original_action=report["actual_native_actions"][ordinal-1]["action"]
        if marker!=original_action+"-"+report["session_id"]:
            raise MP12ShadowRejected("native S49/Paper Action marker mismatch")
        result.append(OriginalExperience(
            ordinal=ordinal,
            action_id=original_action,
            world_uuid=physical["paper_world_uuid"],
            subject_uuid=physical["subject_uuid"],
            session_id=physical["session_id"],
            paper_wait_ticks=tuple(range(
                physical["per_action_wait_tick_ranges"][ordinal-1][0],
                physical["per_action_wait_tick_ranges"][ordinal-1][1]+1)),
            paper_wait_motion_m=actual,
            actual_wait_total_m=sum(actual),
            frozen_slope_065_mae_m=sum(mse)/7,
            cheap_zero_mae_m=sum(actual[1:])/7,
            original_paper_prefix_sha256=_sha(b"".join(lines[:cut+1])),
            original_paper_prefix_lines=cut+1,
        ))
        last_index=cut
    if len({x.original_paper_prefix_sha256 for x in result})!=3:
        raise MP12ShadowRejected("no three independent source-causal prefixes")
    return tuple(result)


def build_l2_request(experiences: tuple[OriginalExperience, ...]) -> OpenCognitionRequest:
    """Use only the historical prefix through one complete original trial."""
    if (type(experiences) is not tuple or not 1<=len(experiences)<=3
            or any(type(x) is not OriginalExperience for x in experiences)):
        raise MP12ShadowRejected("bounded genuine source history required")
    a=experiences[0]
    if (any(x.ordinal!=i+1 or x.world_uuid!=a.world_uuid
            or x.subject_uuid!=a.subject_uuid or x.session_id!=a.session_id
            for i,x in enumerate(experiences))
            or any(x.paper_wait_ticks[-1]>=y.paper_wait_ticks[0]
                   for x,y in zip(experiences,experiences[1:]))):
        raise MP12ShadowRejected("source history is not one World ordered as observed")
    return OpenCognitionRequest(
        request_id=f"mp12:{a.world_uuid}:after-{len(experiences)}-real-trials",
        instruction=(
            "You are fallible L2 analyzing original Minecraft embodied experience. "
            "Return EXACTLY one compact JSON object with keys experiment_id, "
            "model_family, explanation, falsification_test, "
            "predicted_wait_total_m, capability_assessment, "
            "ability_boundary_reason. Select ONE approved future experiment. "
            "model_family must be SINGLE_DECAY, PHASE_DEPENDENT, "
            "SURFACE_DEPENDENT, INITIAL_SPEED_DEPENDENT or OTHER_BOUNDED. "
            "capability_assessment must be UNKNOWN or CONDITIONAL_HYPOTHESIS. "
            "State a falsifiable prediction; distinguish a guess from a learned "
            "capability. No claim of impossibility, no command or learned policy. "
            "The logged three historical trials had identical floor/input "
            "conditions; no causal variation has been performed. Be concise."
        ),
        intent_id="investigate-embodied-adaptation-limit",
        focus="MODEL_ERROR_AND_CURRENT_SELF_CAPABILITY_UNKNOWN",
        context=(
            CognitionDatum.from_value("source_coverage_and_limitations",{
                "mode":"RETROSPECTIVE_SAME_WORLD_SOURCE_PREFIX_REPLAY",
                "not_a_live_next_trial":True,
                "future_history_hidden":True,
                "paper_source_prefix_sha256":experiences[-1].original_paper_prefix_sha256,
                "present_world":a.world_uuid,"present_subject":a.subject_uuid,
                "observed_conditions":"GRASS_BLOCK, identical MOVE_BACKWARD",
                "input_duration":"NOT_ATTESTED",
                "effective_clear_world_tick":"NOT_ATTESTED",
                "movement_skill_limit":"NOT_MEASURED",
                "no_controlled_surface_or_duration_comparison":True,
                "historical_actions_chosen_by_human_staging":True,
                "learning_admission":0,
            },Provenance("mp12.original-source-prefix",experiences[-1].original_paper_prefix_sha256)),
            CognitionDatum.from_value("past_verified_body_world_experience",[
                {
                    "ordinal":x.ordinal,"action_id":x.action_id,
                    "floor":x.surface,"action":x.action,
                    "wait8_m":list(x.paper_wait_motion_m),
                    "wait_ticks":list(x.paper_wait_ticks),
                    "total_wait_m":x.actual_wait_total_m,
                    "frozen_model_mae_m":x.frozen_slope_065_mae_m,
                    "cheap_zero_mae_m":x.cheap_zero_mae_m,
                    "source_prefix_sha256":x.original_paper_prefix_sha256,
                } for x in experiences
            ],Provenance("mp12.verified-g3-original-paper",experiences[-1].original_paper_prefix_sha256)),
            CognitionDatum.from_value("approved_future_tests_hypothetical_only",{
                k:{"surface":v[0],"input_length":v[1]}
                for k,v in EXPERIMENTS.items()
            },Provenance("mp11.experiment-catalog","four-enumerated-conditions")),
        ),
    )


def validate_l2_response(
    answer: OpenCognitionResult, request: OpenCognitionRequest,
    experiences: tuple[OriginalExperience, ...],
) -> ShadowProposal:
    if (not isinstance(answer,OpenCognitionResult)
            or answer.request_id!=request.request_id
            or answer.provenance.source!="llama.cpp"):
        raise MP12ShadowRejected("real llama.cpp OPEN expression with exact request required")
    if len(answer.text.encode("utf-8"))>4096:
        raise MP12ShadowRejected("unbounded L2 response")
    try:
        response=json.loads(answer.text)
    except (ValueError,TypeError) as exc:
        raise MP12ShadowRejected("L2 must return strict JSON") from exc
    if not isinstance(response,dict) or set(response)!=_ALLOWED_FIELDS:
        raise MP12ShadowRejected("L2 did not follow non-action hypothesis schema")
    if (type(response["experiment_id"]) is not str
            or response["experiment_id"] not in EXPERIMENTS
            or type(response["model_family"]) is not str
            or response["model_family"] not in MODEL_FAMILIES
            or response["capability_assessment"] not in _ALLOWED_ABILITY):
        raise MP12ShadowRejected("unbounded action or unsupported ability claim")
    for key in ("explanation","falsification_test","ability_boundary_reason"):
        v=response[key]
        if type(v) is not str or not 12<=len(v)<=400:
            raise MP12ShadowRejected("L2 lacks bounded falsifiable justification")
    value=response["predicted_wait_total_m"]
    if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=3:
        raise MP12ShadowRejected("invalid prospective model prediction")
    fields={
        "source_round":len(experiences),
        "proposed_test_id":response["experiment_id"],
        "model_family":response["model_family"],
        "explanation":response["explanation"],
        "falsification_test":response["falsification_test"],
        "predicted_wait_total_m":float(value),
        "capability_assessment":response["capability_assessment"],
        "ability_boundary_reason":response["ability_boundary_reason"],
        "source_prefix_sha256":experiences[-1].original_paper_prefix_sha256,
        "source_evidence_count":len(experiences),
        "provider_source":answer.provenance.source,
    }
    return ShadowProposal(**fields,proposal_sha256=_json_sha(fields))


def render_shadow_result(
    observations: tuple[OriginalExperience, ...],
    proposal: ShadowProposal | None,
    *,
    model: str | None = None,
    elapsed_ns: int | None = None,
    provider_call_count: int = 0,
) -> dict:
    return {
        "classification":(
            "MP12_ORIGINAL_SOURCE_PREFIX_PREFLIGHT_NO_MODEL"
            if proposal is None else
            "MP12_LLAMA_CPP_OPEN_SHADOW_HYPOTHESIS_NOT_PHYSICAL_EXPERIMENT"
        ),
        "model_requested_not_weights_attested":model,
        "actual_open_calls_observed_in_this_run":provider_call_count,
        "llama_cpp_response_elapsed_ns":elapsed_ns,
        "source_count":len(observations),
        "source_prefix_sha256":observations[-1].original_paper_prefix_sha256,
        "source_experiences":[asdict(x) for x in observations],
        "candidate":None if proposal is None else asdict(proposal),
        "future_physical_actions_executed":0,
        "future_hypothesis_experiments_executed":0,
        "actual_effect_of_L2_on_original_G3_actions":0,
        "ability_infeasibility_established":False,
        "learning_admissions":0,
        "goal":"UNDETERMINED",
        "qualification":"NO_GO",
        "science":"NOT_RUN",
    }
