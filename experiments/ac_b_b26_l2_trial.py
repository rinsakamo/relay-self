"""B26: one optional REAL local L2 proposal, never a gifted competing World law.

The caller must explicitly run the CLI with --run-local-l2 and a local
OpenAI-compatible endpoint. GitHub CI only tests the deterministic runner
with synthetic proposals, NEVER issues an LLM/GPU call. Source training
and heldout evaluations use original B24 offline World.act outcomes only.

ANF coefficient mask bit0=a, bit1=b, bit2=c, bit3=d. Coefficients for
16 masks are a proposed *representation*, not a known World formula.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from experiments.ac_b_b24_structural_transfer import (
    ANCHORS,
    FIELDS,
    HELDOUT,
    PAIRS,
    StructuralWorld,
    WorldAction,
    infer_degree2_cheap,
)

RESPONSE_KEY = "coefficients"
MASKS = tuple(range(16))
MAX_RESPONSE_BYTES = 65536
VALID_MODELS = ("LOCAL_L2_FROZEN_PROPOSAL", "CHEAP_DEG2")
WORLD_KINDS = ("NORMAL", "TWIN")


class InvalidB26Proposal(ValueError):
    """No complete actual source-fit hypothesis or qualified run request."""


@dataclass(frozen=True, slots=True)
class TrainingSource:
    cue: tuple[int, int, int, int]
    winner: int
    source_event_ids: tuple[str, ...]
    original_outcomes: tuple[WorldAction, ...]


@dataclass(frozen=True, slots=True)
class ProposedStructure:
    coefficients: tuple[int, ...]
    source: str


def _strict_json(text: str) -> object:
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, val in pairs:
            if key in result:
                raise InvalidB26Proposal("duplicate model JSON property")
            result[key] = val
        return result

    if not isinstance(text, str):
        raise InvalidB26Proposal("model output must be exact JSON text")
    try:
        return json.loads(text, object_pairs_hook=unique)
    except (ValueError, TypeError) as exc:
        raise InvalidB26Proposal("model output is not valid JSON") from exc


def _terms(cue: tuple[int, int, int, int]) -> tuple[int, ...]:
    if type(cue) is not tuple or len(cue) != 4 or any(
        type(x) is not int or x not in (0, 1) for x in cue
    ):
        raise InvalidB26Proposal("four binary relevant features required")
    return tuple(
        int(all(cue[k] == 1 for k in range(4) if mask & (1 << k)))
        for mask in MASKS
    )


def predict(coefficients: tuple[int, ...], cue: tuple[int, int, int, int]) -> int:
    if len(coefficients) != 16 or any(
        type(x) is not int or x not in (0, 1) for x in coefficients
    ):
        raise InvalidB26Proposal("model requires 16 binary ANF coefficients")
    return sum(x * b for x, b in zip(coefficients, _terms(cue))) % 2


def train_original_world(world: StructuralWorld) -> tuple[TrainingSource, ...]:
    """11 actual completed source Action successes, action1 issued iff 0 fails."""
    if not isinstance(world, StructuralWorld) or world.actions_executed != 0:
        raise InvalidB26Proposal("fresh offline World required")
    result = []
    for cue in ANCHORS:
        first = world.act(cue, 0)
        tried = [first]
        if not first.succeeded:
            tried.append(world.act(cue, 1))
        if not tried[-1].succeeded or any(not world.observed(x) for x in tried):
            raise InvalidB26Proposal("no original source-confirmed training success")
        result.append(TrainingSource(
            cue=cue, winner=tried[-1].action,
            source_event_ids=tuple(x.event_id for x in tried),
            original_outcomes=tuple(tried),
        ))
    if world.actions_executed != 16:
        raise InvalidB26Proposal("pre-frozen training must issue 16 real toy Actions")
    return tuple(result)


def examples_only(data: tuple[TrainingSource, ...]) -> tuple[
    tuple[tuple[int, int, int, int], int], ...
]:
    if len(data) != len(ANCHORS) or tuple(x.cue for x in data) != ANCHORS:
        raise InvalidB26Proposal("11 original source anchors in fixed order required")
    for row in data:
        if (
            type(row.winner) is not int
            or row.winner not in (0, 1)
            or not row.original_outcomes
            or len(row.original_outcomes) not in (1, 2)
            or row.source_event_ids != tuple(
                x.event_id for x in row.original_outcomes
            )
            or not row.original_outcomes[-1].succeeded
            or row.original_outcomes[-1].action != row.winner
            or any(x.cue != row.cue for x in row.original_outcomes)
            or any(x.succeeded for x in row.original_outcomes[:-1])
            or tuple(x.action for x in row.original_outcomes)
            not in ((0,), (0, 1))
        ):
            raise InvalidB26Proposal("training examples lack actual Action outcomes")
    return tuple((x.cue, x.winner) for x in data)


def prompt_messages(data: tuple[TrainingSource, ...]) -> list[dict[str, str]]:
    """Only initial SUCCESS evidence and neutral model language; no heldout hints."""
    examples = examples_only(data)
    # No World identity, future target, hidden residual, or trial results.
    task = {
        "feature_names": list(FIELDS),
        "observations": [
            {"features": list(cue), "successful_action": action}
            for cue, action in examples
        ],
        "representation": (
            "16 binary algebraic-normal-form coefficients ordered by subset "
            "mask 0..15, mask bits a=1,b=2,c=4,d=8; prediction is XOR of "
            "selected subset conjunction terms"
        ),
        "instruction": (
            "Propose ONE complete general rule consistent with every given "
            "observation. Make your own assumption for unspecified interactions. "
            "Output ONLY a JSON object with key coefficients and exactly "
            "16 integer values 0 or 1. No explanations, keys or extra text."
        ),
    }
    return [
        {
            "role": "system",
            "content": (
                "Induce a compact action-selection rule from observed "
                "training experiences only. No hidden environment information "
                "is available. Your output must be strict JSON."
            ),
        },
        {"role": "user", "content": json.dumps(
            task, sort_keys=True, separators=(",", ":")
        )},
    ]


def parse_and_qualify(
    output_text: str, training: tuple[TrainingSource, ...],
    *, source: str = "UNVERIFIED_TEST_INPUT",
) -> ProposedStructure:
    data = _strict_json(output_text)
    if type(data) is not dict or set(data) != {RESPONSE_KEY}:
        raise InvalidB26Proposal("exact model JSON key coefficients required")
    raw = data[RESPONSE_KEY]
    if type(raw) is not list or len(raw) != 16 or any(
        type(x) is not int or x not in (0, 1) for x in raw
    ):
        raise InvalidB26Proposal("exactly 16 integer binary coefficients required")
    coeff = tuple(raw)
    examples = examples_only(training)
    if any(predict(coeff, cue) != answer for cue, answer in examples):
        raise InvalidB26Proposal("proposed structure contradicts executed training")
    return ProposedStructure(coefficients=coeff, source=source)


def cheap_anf(training: tuple[TrainingSource, ...]) -> ProposedStructure:
    base = infer_degree2_cheap(examples_only(training))
    raw = [0] * 16
    masks = (0, 1, 2, 4, 8) + tuple(
        (1 << i) | (1 << j) for i, j in PAIRS
    )
    for mask, bit in zip(masks, base):
        raw[mask] = bit
    proposal = ProposedStructure(tuple(raw), "CHEAP_DEG2")
    if any(
        predict(proposal.coefficients, cue) != answer
        for cue, answer in examples_only(training)
    ):
        raise InvalidB26Proposal("cheap source-matched model inconsistent")
    return proposal


def _heldout_original_actions(
    world: StructuralWorld, coeff: tuple[int, ...],
) -> dict[str, object]:
    events = []
    for cue in HELDOUT:
        choice = predict(coeff, cue)
        first = world.act(cue, choice)
        observations = [first]
        if not first.succeeded:
            observations.append(world.act(cue, 1 - choice))
        if not observations[-1].succeeded or not all(
            world.observed(x) for x in observations
        ):
            raise InvalidB26Proposal("heldout source did not confirm successful retry")
        events.append({
            "cue": list(cue),
            "first_action": choice,
            "first_correct": first.succeeded,
            "actually_executed_actions": [x.action for x in observations],
            "actually_issued_event_ids": [x.event_id for x in observations],
        })
    return {
        "novel_first_correct": sum(x["first_correct"] for x in events),
        "novel_action_attempts": sum(
            len(x["actually_executed_actions"]) for x in events
        ),
        "encounters": len(events),
        "events": events,
    }


def evaluate_frozen_proposal(
    proposed: ProposedStructure,
    *, source_mark: str = "B26_TEST_ONLY_INJECTED_NOT_L2",
) -> dict[str, object]:
    """Never call a model: evaluate one immutable source-qualified candidate.

    Each arm has independent World events. Its 11 training experiences
    are verified to agree with the separately frozen candidate's source
    constraints BEFORE any novel World action is issued.
    """
    if not isinstance(proposed, ProposedStructure):
        raise InvalidB26Proposal("frozen validated coefficient proposal required")
    report = {}
    training_sets = []
    total_actions = 0
    for kind in WORLD_KINDS:
        for mode in VALID_MODELS:
            world = StructuralWorld(
                session=f"b26-offline-{kind.lower()}-{mode.lower()}",
                twin=kind == "TWIN",
            )
            training = train_original_world(world)
            examples = examples_only(training)
            training_sets.append(examples)
            selected = (
                proposed if mode == "LOCAL_L2_FROZEN_PROPOSAL"
                else cheap_anf(training)
            )
            if any(
                predict(selected.coefficients, cue) != answer
                for cue, answer in examples
            ):
                raise InvalidB26Proposal("candidate contradicted actual training source")
            heldout = _heldout_original_actions(world, selected.coefficients)
            if world.actions_executed != 16 + heldout["novel_action_attempts"]:
                raise InvalidB26Proposal("source Action attempt ledger disagrees")
            total_actions += world.actions_executed
            report[f"{kind}:{mode}"] = {
                "training_action_attempts": 16,
                "total_original_world_actions": world.actions_executed,
                "proposal": list(selected.coefficients),
                **heldout,
            }
    if len(set(training_sets)) != 1:
        raise InvalidB26Proposal("normal/twin actual source training is not identical")
    if (
        report["NORMAL:LOCAL_L2_FROZEN_PROPOSAL"]["novel_first_correct"]
        + report["TWIN:LOCAL_L2_FROZEN_PROPOSAL"]["novel_first_correct"]
        != 5
    ):
        raise InvalidB26Proposal("pre-frozen indistinguishability control failed")
    return {
        "classification": "B26_OFFLINE_FROZEN_PROPOSAL_BENCHMARK",
        "proposal_origin": proposed.source,
        "receipt_scope": source_mark,
        "worlds": report,
        "total_independently_issued_offline_world_actions": total_actions,
        "original_training_equal_for_both_hidden_world_laws": True,
        "novel_truth_complementarity_for_frozen_proposal": True,
        "model_call_was_performed_by_this_evaluator": False,
        "not_physical_minecraft": True,
        "not_production_S11": True,
    }


def _local_endpoint(endpoint: str) -> str:
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in ("127.0.0.1", "::1", "localhost")
        or parsed.path != "/v1/chat/completions"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.port is None
    ):
        raise InvalidB26Proposal(
            "explicit local http://127.0.0.1:<port>/v1/chat/completions only"
        )
    return endpoint


def run_local_one_call(
    *, endpoint: str, model: str, messages: list[dict[str, str]],
    timeout_seconds: int = 90,
) -> dict[str, object]:
    """One user-authorized synchronous local L2 call. NO retries/fallbacks."""
    endpoint = _local_endpoint(endpoint)
    if not isinstance(model, str) or not model.strip() or len(model) > 256:
        raise InvalidB26Proposal("explicit exact locally loaded model ID required")
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 300:
        raise InvalidB26Proposal("bounded HTTP inference timeout required")
    payload = json.dumps({
        "model": model, "messages": messages,
        "temperature": 0, "max_tokens": 512, "stream": False,
    }, separators=(",", ":")).encode("utf-8")
    request = Request(
        endpoint, data=payload, headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise InvalidB26Proposal("oversized L2 inference response")
    outer = _strict_json(raw.decode("utf-8"))
    if type(outer) is not dict:
        raise InvalidB26Proposal("OpenAI-compatible response must be an object")
    choices = outer.get("choices")
    if type(choices) is not list or len(choices) != 1:
        raise InvalidB26Proposal("exactly one local L2 completion required")
    choice = choices[0]
    if type(choice) is not dict or type(choice.get("message")) is not dict:
        raise InvalidB26Proposal("local L2 response is not a message")
    content = choice["message"].get("content")
    if type(content) is not str:
        raise InvalidB26Proposal("L2 completion content must be strict JSON text")
    usage = outer.get("usage")
    return {
        "raw_completion": content,
        "requested_model": model,
        "reported_model": outer.get("model"),
        "reported_usage": usage if isinstance(usage, dict) else None,
        "one_synchronous_real_endpoint_response": True,
    }


def execute_local_trial(
    *, endpoint: str, model: str, timeout_seconds: int = 90,
) -> dict[str, object]:
    """Only CLI calls this after explicit --run-local-l2; NEVER CI."""
    train = train_original_world(
        StructuralWorld("b26-prompt-training-source", twin=False)
    )
    prompt = prompt_messages(train)
    reply = run_local_one_call(
        endpoint=endpoint, model=model, messages=prompt,
        timeout_seconds=timeout_seconds,
    )
    candidate = parse_and_qualify(
        reply["raw_completion"], train,
        source="ONE_ACTUAL_LOCAL_L2_RESPONSE",
    )
    result = evaluate_frozen_proposal(
        candidate, source_mark="B26_ACTUAL_LOCAL_L2_RESULT_IF_EXECUTED_ON_HOST"
    )
    result["local_call_receipt"] = reply
    result["prompt_exact"] = prompt
    result["actual_local_model_execution_by_CLI"] = True
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-local-l2", action="store_true")
    p.add_argument(
        "--endpoint", default="http://127.0.0.1:1234/v1/chat/completions"
    )
    p.add_argument("--model")
    p.add_argument("--timeout-seconds", type=int, default=90)
    p.add_argument("--output", type=Path)
    args = p.parse_args(argv)
    if not args.run_local_l2:
        p.error("no inference by default: specify --run-local-l2 explicitly")
    if not args.model:
        p.error("--model exact loaded model ID is required")
    if args.output is None:
        p.error("--output is required for permanent exact local inference receipt")
    r = execute_local_trial(
        endpoint=args.endpoint, model=args.model,
        timeout_seconds=args.timeout_seconds,
    )
    # Persist receipt before printing terminal interpretation: one call,
    # no regeneration, no hidden model-scored fallback.
    args.output.write_text(
        json.dumps(r, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "classification": r["classification"],
        "actual_local_model_execution_by_CLI": True,
        "result_file": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
