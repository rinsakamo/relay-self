from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    DecisionStatus,
    RelayEngine,
    RelayEngineResult,
)
from relay_self.runtime_coordination import coordinate_decision_epoch
from relay_self.skill import SkillExecution, SkillState

QUALIFICATION_SOURCE = "llama-cpp-relay-engine-qualification"


class LlamaCppQualificationError(RuntimeError):
    """Raised when the real model-backed RelayEngine path is not qualified."""


@dataclass(frozen=True, slots=True)
class LlamaCppRuntimeIdentity:
    origin: str
    health_status: str
    model: str
    build_info: str | None
    model_alias: str | None
    model_path: str | None
    model_ftype: str | None


@dataclass(frozen=True, slots=True)
class RelayEngineQualificationReport:
    evidence_class: str
    runtime: LlamaCppRuntimeIdentity
    request_id: str
    final_status: str
    choice_id: str | None
    expected_choice_id: str
    escalated: bool
    attempts: tuple[dict[str, object], ...]
    intent_id: str
    skill_state: str
    open_action_count: int
    qualified: bool


def _provenance(reference: str) -> Provenance:
    return Provenance(
        source=QUALIFICATION_SOURCE,
        reference=reference,
    )


def build_reference_request() -> BoundedChoiceRequest:
    """Build one deliberately bounded FLEE-local parameter decision."""

    return BoundedChoiceRequest(
        request_id="mvp-flee-destination-qualification",
        instruction=(
            "Choose the safer currently reachable destination for the active "
            "FLEE skill using only the supplied facts."
        ),
        intent_id="intent-reach-safety",
        focus="FLEE",
        choices=(
            BoundedChoice(
                "cave",
                "Reachable cave with explicit shelter evidence.",
            ),
            BoundedChoice(
                "ridge",
                "Reachable exposed ridge with no shelter evidence.",
            ),
        ),
        context=(
            CognitionDatum.from_value(
                "health",
                6,
                _provenance("fixture:health"),
            ),
            CognitionDatum.from_value(
                "is_day",
                False,
                _provenance("fixture:time"),
            ),
            CognitionDatum.from_value(
                "nearby_entity",
                {"name": "zombie", "distance": 3.0},
                _provenance("fixture:entity"),
            ),
            CognitionDatum.from_value(
                "route_open:cave",
                True,
                _provenance("fixture:route:cave"),
            ),
            CognitionDatum.from_value(
                "route_open:ridge",
                True,
                _provenance("fixture:route:ridge"),
            ),
            CognitionDatum.from_value(
                "shelter:cave",
                True,
                _provenance("fixture:shelter:cave"),
            ),
            CognitionDatum.from_value(
                "shelter:ridge",
                False,
                _provenance("fixture:shelter:ridge"),
            ),
        ),
    )


def qualify_relay_engine(
    engine: RelayEngine,
    runtime: LlamaCppRuntimeIdentity,
) -> RelayEngineQualificationReport:
    """Run one model-facing FLEE parameter decision through canonical owners."""

    commitment = IntentCommitment()
    commitment.commit(
        "intent-reach-safety",
        objective="reach safety",
        at_ns=1,
        provenance=_provenance("intent"),
    )
    skill = SkillExecution.start(
        "skill-flee-qualification",
        skill_id="FLEE",
        intent_commitment=commitment,
        at_ns=2,
        provenance=_provenance("skill"),
    )
    supervisor = ActionSupervisor()
    request = build_reference_request()

    epoch = coordinate_decision_epoch(
        supervisor,
        at_ns=3,
        provenance=_provenance("epoch"),
        decision_step=lambda: request,
        relay_engine=engine,
    )
    result = epoch.cognition_result
    if not isinstance(result, RelayEngineResult):
        raise LlamaCppQualificationError(
            "RelayEngine did not return RelayEngineResult"
        )

    expected_choice = "cave"
    if result.status is not DecisionStatus.RESOLVED:
        raise LlamaCppQualificationError(
            "real RelayEngine path remained unresolved"
        )
    if result.choice_id != expected_choice:
        raise LlamaCppQualificationError(
            "real RelayEngine path selected unexpected choice: "
            f"{result.choice_id}; expected {expected_choice}"
        )
    if commitment.current_intent is None:
        raise LlamaCppQualificationError(
            "model-backed cognition released Current Intent"
        )
    if skill.state is not SkillState.STARTED:
        raise LlamaCppQualificationError(
            "model-backed cognition mutated SkillExecution state"
        )
    if supervisor.open_actions:
        raise LlamaCppQualificationError(
            "model-backed cognition created or issued an Action"
        )

    return RelayEngineQualificationReport(
        evidence_class="model_or_system_quality",
        runtime=runtime,
        request_id=request.request_id,
        final_status=result.status.value,
        choice_id=result.choice_id,
        expected_choice_id=expected_choice,
        escalated=result.escalated,
        attempts=tuple(
            {
                "mode": attempt.mode.value,
                "status": attempt.status.value,
                "choice_id": attempt.choice_id,
                "reason": attempt.reason,
            }
            for attempt in result.attempts
        ),
        intent_id=commitment.current_intent.intent_id,
        skill_state=skill.state.value,
        open_action_count=len(supervisor.open_actions),
        qualified=True,
    )


def inspect_llama_cpp_runtime(
    *,
    origin: str,
    timeout: float,
) -> LlamaCppRuntimeIdentity:
    normalized = _validate_origin(origin)
    health = _get_json(f"{normalized}/health", timeout=timeout)
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise LlamaCppQualificationError(
            "llama.cpp /health did not report status=ok"
        )

    models = _get_json(f"{normalized}/v1/models", timeout=timeout)
    if not isinstance(models, dict) or not isinstance(models.get("data"), list):
        raise LlamaCppQualificationError(
            "llama.cpp /v1/models response is invalid"
        )
    model_ids = [
        item.get("id")
        for item in models["data"]
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and item["id"]
    ]
    if len(model_ids) != 1:
        raise LlamaCppQualificationError(
            "qualification requires exactly one served model"
        )

    props = _get_json(f"{normalized}/props", timeout=timeout)
    if not isinstance(props, dict):
        raise LlamaCppQualificationError(
            "llama.cpp /props response is invalid"
        )

    def optional_text(key: str) -> str | None:
        value = props.get(key)
        return value if isinstance(value, str) and value else None

    return LlamaCppRuntimeIdentity(
        origin=normalized,
        health_status="ok",
        model=model_ids[0],
        build_info=optional_text("build_info"),
        model_alias=optional_text("model_alias"),
        model_path=optional_text("model_path"),
        model_ftype=optional_text("model_ftype"),
    )


def run_live_qualification(
    *,
    origin: str = "http://127.0.0.1:1234",
    timeout: float = 60.0,
) -> RelayEngineQualificationReport:
    runtime = inspect_llama_cpp_runtime(
        origin=origin,
        timeout=timeout,
    )
    provider = LlamaCppRelayProvider(
        endpoint=f"{runtime.origin}/v1/chat/completions",
        model=runtime.model,
        timeout=timeout,
    )
    return qualify_relay_engine(
        RelayEngine(provider),
        runtime,
    )


def _get_json(url: str, *, timeout: float) -> object:
    if (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or timeout <= 0
    ):
        raise LlamaCppQualificationError(
            "timeout must be a positive number"
        )
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=float(timeout),
        ) as response:
            return json.loads(response.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        TimeoutError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise LlamaCppQualificationError(
            f"llama.cpp runtime inspection failed: {type(exc).__name__}: {exc}"
        ) from exc


def _validate_origin(origin: object) -> str:
    if not isinstance(origin, str) or not origin.strip():
        raise LlamaCppQualificationError(
            "origin must be a non-empty string"
        )
    parsed = urllib.parse.urlsplit(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise LlamaCppQualificationError(
            "origin must be an http(s) URL"
        )
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise LlamaCppQualificationError(
            "origin must not contain a path, query, or fragment"
        )
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, "", "", "")
    ).rstrip("/")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Qualify one real llama.cpp-backed RelayEngine bounded decision."
        )
    )
    parser.add_argument(
        "--origin",
        default="http://127.0.0.1:1234",
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser


def main() -> int:
    args = _parser().parse_args()
    report = run_live_qualification(
        origin=args.origin,
        timeout=args.timeout,
    )
    print(
        json.dumps(
            asdict(report),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
