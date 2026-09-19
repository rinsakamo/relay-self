from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from experiments.gemma_flee_crystallization import (
    METADATA_BLINDING,
    filter_request,
    write_protocol_failure,
)
from experiments.gemma_skill_narrowing import (
    ObservedLlamaCppProtocolFailure,
    ObservedLlamaCppProvider,
    _condition_summary,
    _sum_numeric,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    DecisionStatus,
    RelayEngine,
)

SOURCE = "gemma-flee-artifact-reuse"
FROZEN_RETAINED_KEYS = (
    "route_open:cave",
    "route_open:ridge",
    "shelter:ridge",
)
CONDITIONS = ("full", "artifact")
CHOICE_ORDERS = ("forward", "reverse")


@dataclass(frozen=True, slots=True)
class ReuseState:
    state_id: str
    route_cave: bool
    route_ridge: bool
    shelter_cave: bool
    shelter_ridge: bool
    expected_destination: str | None
    family: str


STATES = (
    ReuseState("K1", True, False, True, False, "cave", "known"),
    ReuseState("K2", False, True, False, True, "ridge", "known"),
    ReuseState("K3", True, True, True, False, "cave", "known"),
    ReuseState("K4", True, True, False, True, "ridge", "known"),
    ReuseState("N1", True, True, True, True, None, "novel"),
    ReuseState("N2", True, True, False, False, None, "novel"),
    ReuseState("N3", False, False, True, True, None, "novel"),
    ReuseState("N4", True, False, False, True, "cave", "novel"),
    ReuseState("N5", False, True, True, False, "ridge", "novel"),
)

MAPPINGS = (
    {"cave": "cave", "ridge": "ridge"},
    {"cave": "A", "ridge": "B"},
    {"cave": "B", "ridge": "A"},
)


def _datum(
    key: str,
    value: object,
    *,
    state_index: int,
    mapping_index: int,
    order_index: int,
    datum_index: int,
) -> CognitionDatum:
    return CognitionDatum.from_value(
        key,
        value,
        Provenance(
            source=SOURCE,
            reference=(
                f"reuse:{state_index:02d}:{mapping_index:02d}:"
                f"{order_index:02d}:{datum_index:02d}"
            ),
        ),
    )


def _mapping(mapping_index: int) -> dict[str, str]:
    try:
        return dict(MAPPINGS[mapping_index])
    except IndexError as exc:
        raise ValueError(
            f"unsupported mapping_index: {mapping_index}"
        ) from exc


def _choice_destination_map(mapping_index: int) -> dict[str, str]:
    mapping = _mapping(mapping_index)
    return {
        mapping["cave"]: "cave",
        mapping["ridge"]: "ridge",
    }


def _choices(
    *,
    mapping_index: int,
    order_index: int,
) -> tuple[BoundedChoice, ...]:
    mapping = _mapping(mapping_index)
    choices = (
        BoundedChoice(mapping["cave"], "Destination cave"),
        BoundedChoice(mapping["ridge"], "Destination ridge"),
    )
    if CHOICE_ORDERS[order_index] == "reverse":
        return tuple(reversed(choices))
    return choices


def build_full_request(
    state: ReuseState,
    *,
    state_index: int,
    mapping_index: int,
    order_index: int,
) -> BoundedChoiceRequest:
    values = (
        ("threat_nearby", True),
        ("health", 6),
        ("route_open:cave", state.route_cave),
        ("route_open:ridge", state.route_ridge),
        ("shelter:cave", state.shelter_cave),
        ("shelter:ridge", state.shelter_ridge),
    )
    context = tuple(
        _datum(
            key,
            value,
            state_index=state_index,
            mapping_index=mapping_index,
            order_index=order_index,
            datum_index=datum_index,
        )
        for datum_index, (key, value) in enumerate(values)
    )
    return BoundedChoiceRequest(
        request_id=(
            f"artifact-reuse:{state_index:02d}:"
            f"{mapping_index:02d}:{order_index:02d}"
        ),
        instruction=(
            "Choose the safer currently reachable destination for the active "
            "FLEE skill. A destination is admissible only when route_open is "
            "true. If both destinations are reachable, prefer the one whose "
            "shelter fact is true. If the supplied facts do not establish one "
            "unique preferred reachable destination, return unresolved. "
            "Use only supplied context."
        ),
        intent_id="intent-reach-safety",
        focus="FLEE",
        choices=_choices(
            mapping_index=mapping_index,
            order_index=order_index,
        ),
        context=context,
    )


def expected_choice_id(
    state: ReuseState,
    *,
    mapping_index: int,
) -> str | None:
    if state.expected_destination is None:
        return None
    return _mapping(mapping_index)[state.expected_destination]


def decode_destination(
    choice_id: str | None,
    *,
    mapping_index: int,
) -> str | None:
    if choice_id is None:
        return None
    return _choice_destination_map(mapping_index).get(choice_id)


def build_schedule() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    observation_index = 0
    cell_index = 0
    for state_index, state in enumerate(STATES):
        for mapping_index in range(len(MAPPINGS)):
            for order_index, order in enumerate(CHOICE_ORDERS):
                condition_order = (
                    CONDITIONS
                    if cell_index % 2 == 0
                    else tuple(reversed(CONDITIONS))
                )
                for condition in condition_order:
                    rows.append(
                        {
                            "observation_index": observation_index,
                            "cell_index": cell_index,
                            "state_id": state.state_id,
                            "family": state.family,
                            "state_index": state_index,
                            "mapping_index": mapping_index,
                            "order_index": order_index,
                            "choice_order": order,
                            "condition": condition,
                            "expected_destination": (
                                state.expected_destination
                            ),
                            "expected_choice_id": expected_choice_id(
                                state,
                                mapping_index=mapping_index,
                            ),
                        }
                    )
                    observation_index += 1
                cell_index += 1
    return rows


def run_episode(
    *,
    provider: ObservedLlamaCppProvider,
    request: BoundedChoiceRequest,
    state: ReuseState,
    mapping_index: int,
    condition: str,
) -> dict[str, object]:
    provider.clear_records()
    result = RelayEngine(provider)(request)
    records = [dict(record) for record in provider.records]
    destination = decode_destination(
        result.choice_id,
        mapping_index=mapping_index,
    )
    if state.expected_destination is None:
        correct = (
            result.status is DecisionStatus.UNRESOLVED
            and result.choice_id is None
        )
    else:
        correct = (
            result.status is DecisionStatus.RESOLVED
            and destination == state.expected_destination
        )
    inadmissible = any(
        "inadmissible" in attempt.reason
        for attempt in result.attempts
    )
    bounded_record = next(
        (
            record
            for record in records
            if record.get("mode") == CognitionMode.BOUNDED.value
        ),
        None,
    )
    think_record = next(
        (
            record
            for record in records
            if record.get("mode") == CognitionMode.THINK.value
        ),
        None,
    )
    return {
        "state_id": state.state_id,
        "family": state.family,
        "condition": condition,
        "expected_destination": state.expected_destination,
        "final_status": result.status.value,
        "final_choice_id": result.choice_id,
        "final_destination": destination,
        "decision_correct": correct,
        "escalated": result.escalated,
        "inadmissible_attempt": inadmissible,
        "context_datum_count": len(request.context),
        "context_keys": [datum.key for datum in request.context],
        "model_call_count": len(records),
        "total_model_latency_seconds": _sum_numeric(
            records,
            "elapsed_seconds",
        ),
        "total_prompt_tokens": _sum_numeric(
            records,
            "prompt_tokens",
        ),
        "total_completion_tokens": _sum_numeric(
            records,
            "completion_tokens",
        ),
        "total_request_json_bytes": _sum_numeric(
            records,
            "request_json_bytes",
        ),
        "bounded_latency_seconds": (
            bounded_record.get("elapsed_seconds")
            if isinstance(bounded_record, dict)
            else None
        ),
        "think_latency_seconds": (
            think_record.get("elapsed_seconds")
            if isinstance(think_record, dict)
            else None
        ),
        "attempts": [
            {
                "mode": attempt.mode.value,
                "status": attempt.status.value,
                "choice_id": attempt.choice_id,
                "reason": attempt.reason,
            }
            for attempt in result.attempts
        ],
        "provider_calls": records,
    }


def _rows(
    observations: list[dict[str, object]],
    *,
    condition: str | None = None,
    family: str | None = None,
) -> list[dict[str, object]]:
    return [
        row
        for row in observations
        if (
            (condition is None or row.get("condition") == condition)
            and (family is None or row.get("family") == family)
        )
    ]


def classify_result(
    observations: list[dict[str, object]],
) -> str:
    known_full = _rows(
        observations,
        condition="full",
        family="known",
    )
    known_artifact = _rows(
        observations,
        condition="artifact",
        family="known",
    )
    if not all(row.get("decision_correct") is True for row in known_full):
        return "C_REPRESENTATION_DEPENDENT_FAILURE"
    if not all(
        row.get("decision_correct") is True for row in known_artifact
    ):
        return "C_REPRESENTATION_DEPENDENT_FAILURE"

    n3_artifact = [
        row
        for row in observations
        if row.get("condition") == "artifact"
        and row.get("state_id") == "N3"
    ]
    if any(
        row.get("final_status") == DecisionStatus.RESOLVED.value
        for row in n3_artifact
    ):
        return "D_STRONG_SEMANTIC_FAILURE"

    novel_full = _rows(
        observations,
        condition="full",
        family="novel",
    )
    novel_artifact = _rows(
        observations,
        condition="artifact",
        family="novel",
    )
    full_correct = all(
        row.get("decision_correct") is True for row in novel_full
    )
    artifact_correct = all(
        row.get("decision_correct") is True
        for row in novel_artifact
    )
    if full_correct and artifact_correct:
        return "A_REMAPPING_ROBUST_TESTED_SURFACE"
    if full_correct and not artifact_correct:
        return "B_REUSE_BOUNDARY_EXPOSED"
    return "C_REPRESENTATION_DEPENDENT_FAILURE"


def summarize(
    observations: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "classification": classify_result(observations),
        "by_condition": {
            condition: _condition_summary(
                _rows(observations, condition=condition)
            )
            for condition in CONDITIONS
        },
        "known_by_condition": {
            condition: _condition_summary(
                _rows(
                    observations,
                    condition=condition,
                    family="known",
                )
            )
            for condition in CONDITIONS
        },
        "novel_by_condition": {
            condition: _condition_summary(
                _rows(
                    observations,
                    condition=condition,
                    family="novel",
                )
            )
            for condition in CONDITIONS
        },
    }


def dry_run_payload() -> dict[str, object]:
    return {
        "evidence_class": "gemma flee artifact reuse plan only",
        "metadata_blinding": METADATA_BLINDING,
        "provider_visible_semantic_case_ids": False,
        "frozen_retained_keys": list(FROZEN_RETAINED_KEYS),
        "state_count": len(STATES),
        "mapping_count": len(MAPPINGS),
        "choice_order_count": len(CHOICE_ORDERS),
        "condition_count": len(CONDITIONS),
        "measured_episode_count": len(build_schedule()),
        "schedule": build_schedule(),
        "excluded_warmups": [
            CognitionMode.BOUNDED.value,
            CognitionMode.THINK.value,
        ],
        "non_claims": [
            "this gate does not re-induce or update the frozen artifact",
            "the artifact remains experiment evidence only",
            "choice remapping is not key-schema remapping",
            "no applicability predictor or novelty detector is added",
        ],
    }


def run_actual(
    *,
    endpoint: str,
    model: str,
    timeout: float,
) -> dict[str, object]:
    provider = ObservedLlamaCppProvider(
        endpoint=endpoint,
        model=model,
        timeout=timeout,
    )
    warmup_request = build_full_request(
        STATES[0],
        state_index=0,
        mapping_index=0,
        order_index=0,
    )
    warmups: list[dict[str, object]] = []
    for mode in (CognitionMode.BOUNDED, CognitionMode.THINK):
        provider.clear_records()
        provider(warmup_request, mode=mode)
        warmups.extend(
            {**record, "warmup": True}
            for record in provider.records
        )

    states = {state.state_id: state for state in STATES}
    observations: list[dict[str, object]] = []
    for schedule_row in build_schedule():
        state = states[str(schedule_row["state_id"])]
        state_index = int(schedule_row["state_index"])
        mapping_index = int(schedule_row["mapping_index"])
        order_index = int(schedule_row["order_index"])
        condition = str(schedule_row["condition"])
        full = build_full_request(
            state,
            state_index=state_index,
            mapping_index=mapping_index,
            order_index=order_index,
        )
        request = (
            full
            if condition == "full"
            else filter_request(
                full,
                retained_keys=FROZEN_RETAINED_KEYS,
            )
        )
        row = run_episode(
            provider=provider,
            request=request,
            state=state,
            mapping_index=mapping_index,
            condition=condition,
        )
        row.update(schedule_row)
        observations.append(row)

    return {
        "evidence_class": "actual-model gemma flee artifact reuse",
        "endpoint": endpoint,
        "model": model,
        "metadata_blinding": METADATA_BLINDING,
        "provider_visible_semantic_case_ids": False,
        "frozen_retained_keys": list(FROZEN_RETAINED_KEYS),
        "warmups": warmups,
        "observations": observations,
        "summary": summarize(observations),
    }


def write_payload(
    payload: dict[str, object],
    output: str | None,
) -> None:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    if output is None:
        print(serialized)
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized + "\n", encoding="utf-8")
    print(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Test the frozen blinded FLEE artifact under choice "
            "remapping and novel ambiguity."
        )
    )
    parser.add_argument("--run", action="store_true")
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:1234/v1/chat/completions",
    )
    parser.add_argument("--model", default="gemma-local")
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--output")
    parser.add_argument("--protocol-failure-output")
    args = parser.parse_args()

    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    try:
        payload = (
            run_actual(
                endpoint=args.endpoint,
                model=args.model,
                timeout=args.timeout,
            )
            if args.run
            else dry_run_payload()
        )
        write_payload(payload, args.output)
    except ObservedLlamaCppProtocolFailure as exc:
        write_protocol_failure(
            exc.record,
            args.protocol_failure_output,
        )
        parser.error(str(exc))
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
