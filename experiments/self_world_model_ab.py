"""W4 SelfWorld optional-context matched local-model A/B, DEV/OFFLINE.

One existing RelayEngine and llama.cpp adapter; no model launcher, World, Action,
S10, or scientific qualification. A/B manipulates ONLY SelfWorld context.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from adapters.llama_cpp.relay_engine import (
    LlamaCppProviderError,
    LlamaCppRelayProvider,
)
from adapters.mineflayer.self_world_observation_only_cognition import (
    W4OfflineCognitionInputs,
    prepare_w4_offline_cognition_inputs,
)
from adapters.mineflayer.self_world_observation_only_epoch_replay import (
    replay_w4_saved_self_world_epochs,
)
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    DecisionStatus,
    OpenCognitionRequest,
    RelayEngine,
)

ARM_BASE = "without_selfworld"
ARM_CONTEXT = "with_selfworld"
ARMS = (ARM_BASE, ARM_CONTEXT)
CHOICES = frozenset(("INSPECT_SOURCE", "DEFER_RECHECK"))
SOURCE_HEAD = "1b221d845e42ea0e8be003239525c50de20e7fef"
SOURCE_RUN = "1e86a714f3ea3374"
SOURCE_REPORT_SHA = "a2f16d3bec33fcb6ea86d225858da8bf4df6dbedf5908eba950a0998f18c755f"


class W4ModelABBlocked(ValueError):
    """An experiment input, output path or local endpoint is not admissible."""


@dataclass(frozen=True, slots=True)
class CognitionCase:
    case_id: str
    prepared: W4OfflineCognitionInputs
    expected_prior: str
    expected_following: str
    source_class: str


def paired_order(index: int) -> tuple[str, str]:
    if type(index) is not int or index < 0:
        raise W4ModelABBlocked("pair index must be nonnegative integer")
    return ARMS if index % 2 == 0 else ARMS[::-1]


def ab_requests(
    prepared: W4OfflineCognitionInputs, epoch: str, route: str,
) -> tuple[BoundedChoiceRequest | OpenCognitionRequest, ...]:
    if type(prepared) is not W4OfflineCognitionInputs:
        raise W4ModelABBlocked("exact read-only cognition inputs required")
    if epoch not in {"prior", "following"} or route not in {"bounded", "open"}:
        raise W4ModelABBlocked("invalid epoch or request route")
    full = getattr(prepared, f"{epoch}_{route}")
    if (type(full) not in (BoundedChoiceRequest, OpenCognitionRequest)
            or len(full.context) < 2
            or tuple(d.key for d in full.context[:2]) != (
                "self_world_observer", "self_world_observed",
            )
            or any(not d.key.startswith("self_world_") for d in full.context)):
        raise W4ModelABBlocked("invalid context manipulation source")
    if route == "bounded" and (
        not full.think_allowed
        or frozenset(c.choice_id for c in full.choices) != CHOICES
    ):
        raise W4ModelABBlocked("bounded choice surface differs from preregistration")
    # All other request attributes, including request_id/choice order/instruction,
    # are EXACTLY identical. Empty context is lack of source, not absence.
    return replace(full, context=()), full


def _request_digest(request: BoundedChoiceRequest | OpenCognitionRequest) -> str:
    from adapters.llama_cpp.relay_engine import (
        render_llama_cpp_open_request,
        render_llama_cpp_request,
    )
    from relay_self.relay_engine import CognitionMode

    if type(request) is BoundedChoiceRequest:
        body = render_llama_cpp_request(
            request, mode=CognitionMode.BOUNDED, model="HASH_MODEL_PLACEHOLDER",
        )
    else:
        body = render_llama_cpp_open_request(
            request, model="HASH_MODEL_PLACEHOLDER",
        )
    return hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


def run_matched_ab(
    *, cases: tuple[CognitionCase, ...], engine: RelayEngine,
    repeats: int = 4, warmup_pairs: int = 1, include_open: bool = True,
    on_record: Callable[[dict[str, object]], None] | None = None,
) -> dict[str, object]:
    """Execute the predeclared A/B order; never select outcomes adaptively.

    Each scored choice is a DEV *rubric* about positive source/uncertainty,
    not actual World ground truth. OPEN content is hashed, not graded.
    """
    if (not isinstance(cases, tuple) or not cases
            or type(engine) is not RelayEngine
            or type(repeats) is not int or repeats <= 0 or repeats > 100
            or type(warmup_pairs) is not int or not 0 <= warmup_pairs <= 10
            or type(include_open) is not bool):
        raise W4ModelABBlocked("finite cases/engine/budgets required")
    names = tuple(case.case_id for case in cases)
    if len(set(names)) != len(names):
        raise W4ModelABBlocked("duplicate case ID")
    for case in cases:
        if (type(case) is not CognitionCase
                or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", case.case_id)
                or case.expected_prior not in CHOICES
                or case.expected_following not in CHOICES
                or case.source_class not in {"SAVED_DEV_LOCAL", "SYNTHETIC_DEV"}
                or type(case.prepared) is not W4OfflineCognitionInputs
                or case.prepared.model_calls != 0
                or case.prepared.action_count != 0
                or case.prepared.outcome_count != 0
                or case.prepared.s10_update_count != 0
                or case.prepared.memory_writes != 0
                or case.prepared.world_qualified or case.prepared.science_qualified):
            raise W4ModelABBlocked("case not source-bound nonexecuting DEV")
    rows = []
    routes = ("bounded", "open") if include_open else ("bounded",)
    for case in cases:
        for epoch in ("prior", "following"):
            for route in routes:
                no_context, with_context = ab_requests(case.prepared, epoch, route)
                requests = {ARM_BASE: no_context, ARM_CONTEXT: with_context}
                for pair in range(warmup_pairs + repeats):
                    for position, arm in enumerate(paired_order(pair)):
                        request = requests[arm]
                        start = time.perf_counter_ns()
                        data = {
                            "case_id": case.case_id, "source_class": case.source_class,
                            "epoch": epoch, "route": route, "arm": arm,
                            "pair": pair, "position": position,
                            "warmup": pair < warmup_pairs,
                            "request_sha256": _request_digest(request),
                            "expected_choice": (
                                case.expected_prior if epoch == "prior"
                                else case.expected_following
                            ) if route == "bounded" else None,
                            "status": None, "choice_id": None,
                            "correct_rubric": None, "escalated": None,
                            "provider_calls": None, "prompt_tokens": None,
                            "completion_tokens": None, "open_text_sha256": None,
                            "error_type": None,
                        }
                        try:
                            if route == "bounded":
                                outcome = engine(request)
                                data.update({
                                    "status": outcome.status.value,
                                    "choice_id": outcome.choice_id,
                                    "correct_rubric": (
                                        outcome.status is DecisionStatus.RESOLVED
                                        and outcome.choice_id == data["expected_choice"]
                                    ),
                                    "escalated": outcome.escalated,
                                    "provider_calls": outcome.provider_call_count,
                                    "prompt_tokens": outcome.observed_prompt_tokens,
                                    "completion_tokens": outcome.observed_completion_tokens,
                                })
                            else:
                                opened = engine.open(request)
                                data.update({
                                    "status": "generated",
                                    "provider_calls": opened.provider_call_count,
                                    "prompt_tokens": opened.observed_prompt_tokens,
                                    "completion_tokens": opened.observed_completion_tokens,
                                    "open_text_sha256": hashlib.sha256(
                                        opened.text.encode("utf-8")
                                    ).hexdigest(),
                                })
                        except LlamaCppProviderError as exc:
                            data["error_type"] = type(exc).__name__
                        data["wall_ns"] = time.perf_counter_ns() - start
                        rows.append(data)
                        if on_record is not None:
                            on_record(dict(data))
    measured = [r for r in rows if not r["warmup"]]
    summary = {}
    for case in cases:
        for epoch in ("prior", "following"):
            for route in routes:
                for arm in ARMS:
                    group = [
                        row for row in measured
                        if row["case_id"] == case.case_id and row["epoch"] == epoch
                        and row["route"] == route and row["arm"] == arm
                    ]
                    key = "/".join((case.case_id, epoch, route, arm))
                    available_tokens = [
                        row["prompt_tokens"] for row in group
                        if row["prompt_tokens"] is not None
                    ]
                    summary[key] = {
                        "count": len(group),
                        "errors": sum(row["error_type"] is not None for row in group),
                        "resolved": sum(row["status"] == "resolved" for row in group),
                        "rubric_correct": (
                            sum(row["correct_rubric"] is True for row in group)
                            if route == "bounded" else None
                        ),
                        "think_escalations": (
                            sum(row["escalated"] is True for row in group)
                            if route == "bounded" else None
                        ),
                        "median_wall_ms": statistics.median(
                            row["wall_ns"] for row in group
                        ) / 1_000_000,
                        "prompt_tokens_median": (
                            statistics.median(available_tokens)
                            if len(available_tokens) == len(group) else None
                        ),
                        "completion_tokens_median": (
                            statistics.median(row["completion_tokens"] for row in group)
                            if all(row["completion_tokens"] is not None for row in group)
                            else None
                        ),
                        "provider_calls_median": (
                            statistics.median(row["provider_calls"] for row in group)
                            if all(row["provider_calls"] is not None for row in group)
                            else None
                        ),
                        "token_metadata_complete": (
                            len(available_tokens) == len(group)
                            and all(row["completion_tokens"] is not None for row in group)
                        ),
                    }
    return {
        "schema": "W4_SELF_WORLD_MODEL_AB_DEV_V1",
        "classification": "DEV_ONLY_LOCAL_MODEL_OBSERVATION_NOT_SCIENCE",
        "rubric": (
            "Explicit positive prior evidence permits INSPECT_SOURCE; "
            "missing or discrepant positive evidence calls for DEFER_RECHECK. "
            "This is a synthetic normative rubric, NOT measured World safety."
        ),
        "arms": list(ARMS), "repeats": repeats,
        "warmup_pairs": warmup_pairs, "include_open": include_open,
        "cases": [
            {"id": c.case_id, "source_class": c.source_class,
             "expected_prior": c.expected_prior,
             "expected_following": c.expected_following}
            for c in cases
        ],
        "summary": summary, "rows": rows,
        "new_world_runs": 0, "physical_actions": 0, "outcomes": 0,
        "s10_commits": 0, "science_qualified": False,
    }


def validate_local_endpoint(endpoint: str) -> str:
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise W4ModelABBlocked("malformed endpoint") from exc
    if (
        parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
        or port is None or not 1 <= port <= 65535
        or parsed.path != "/v1/chat/completions"
        or parsed.username or parsed.password or parsed.query or parsed.fragment
    ):
        raise W4ModelABBlocked("only exact localhost chat-completions supported")
    return endpoint


def _repo_pins(root: Path, head: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", head) is None:
        raise W4ModelABBlocked("exact HEAD required")
    try:
        actual = subprocess.check_output(
            ("git", "-C", str(root), "rev-parse", "HEAD"), text=True,
        ).strip()
        dirty = subprocess.check_output(
            ("git", "-C", str(root), "status", "--porcelain"),
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise W4ModelABBlocked("repository identity unavailable") from exc
    if actual != head or dirty:
        raise W4ModelABBlocked("unmatched HEAD or unclean experiment checkout")


def build_real_case(root: Path) -> CognitionCase:
    replay = replay_w4_saved_self_world_epochs(
        evidence_root=root, expected_report_sha256=SOURCE_REPORT_SHA,
        expected_source_head=SOURCE_HEAD,
        expected_run_id=SOURCE_RUN, self_id="w4-offline-observer",
    )
    if (replay.prior_attention.selected or replay.following_attention.selected
            or replay.prediction_review is not None):
        raise W4ModelABBlocked("saved real DEV case changed from frozen empty probe")
    return CognitionCase(
        "w4-original-empty", prepare_w4_offline_cognition_inputs(replay),
        "DEFER_RECHECK", "DEFER_RECHECK", "SAVED_DEV_LOCAL",
    )


def _synthetic_cases() -> tuple[CognitionCase, ...]:
    """Use existing DEV-only synthetic raw fixture factory, not World data."""
    from unittest.mock import patch

    from test_self_world_observation_only_epoch_replay import _case, _offline_lines, _pin

    cases = []
    with tempfile.TemporaryDirectory(prefix="w4-model-ab-synthetic-") as temp:
        for label, kind in (("match", "zombie"), ("mismatch", "skeleton"),
                            ("unknown", "missing")):
            root = Path(temp) / label
            report = _case(root, target_before=True, later_kind=kind)
            replay = replay_w4_saved_self_world_epochs(**_pin(root, report))
            cases.append(CognitionCase(
                label, prepare_w4_offline_cognition_inputs(replay),
                "INSPECT_SOURCE",
                "INSPECT_SOURCE" if kind == "zombie" else "DEFER_RECHECK",
                "SYNTHETIC_DEV",
            ))
        def empty_lines():
            first, second, lines = _offline_lines()
            changed = []
            for raw in lines:
                item = json.loads(raw)
                if item.get("type") == "observation":
                    item["snapshot"]["nearby_entities"] = []
                    item["snapshot"]["nearby_entities_coverage"]["candidate_count"] = 0
                changed.append((json.dumps(item) + "\n").encode())
            return first, second, changed

        import test_self_world_observation_only_epoch_replay as fixture
        with patch.object(fixture, "_offline_lines", empty_lines):
            root = Path(temp) / "empty"
            report = _case(root)
            replay = replay_w4_saved_self_world_epochs(**_pin(root, report))
            cases.append(CognitionCase(
                "synthetic-empty", prepare_w4_offline_cognition_inputs(replay),
                "DEFER_RECHECK", "DEFER_RECHECK", "SYNTHETIC_DEV",
            ))
    return tuple(cases)


def _check_new_path(path: Path) -> None:
    if (not path.is_absolute() or not path.parent.is_dir()
            or path.exists() or path.is_symlink()
            or any(part.is_symlink() for part in path.parents)):
        raise W4ModelABBlocked("new external non-symlink output path required")


def _write_new_report(path: Path, report: dict[str, object]) -> None:
    _check_new_path(path)
    payload = (json.dumps(
        report, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False,
    ) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(payload)
        out.flush()
        os.fsync(out.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("real", "synthetic"), required=True)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=4)
    parser.add_argument("--warmup-pairs", type=int, default=1)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if (
        args.confirm != "LOCAL_MODEL_DEV_ONLY"
        or sys.version_info[:2] != (3, 12)
        or not args.repo_root.is_absolute()
        or not args.model.strip()
    ):
        raise W4ModelABBlocked("explicit DEV confirmation, Python3.12, model and root")
    endpoint = validate_local_endpoint(args.endpoint)
    _repo_pins(args.repo_root, args.expected_head)
    if args.output.is_relative_to(args.repo_root):
        raise W4ModelABBlocked("write results outside repository")
    if (args.evidence_root is not None
            and args.output.is_relative_to(args.evidence_root)):
        raise W4ModelABBlocked("write results outside immutable source evidence")
    if args.source == "real":
        if args.evidence_root is None:
            raise W4ModelABBlocked("original saved W4 DEV root required")
        cases = (build_real_case(args.evidence_root),)
    else:
        if args.evidence_root is not None:
            raise W4ModelABBlocked("synthetic source cannot use real evidence")
        cases = _synthetic_cases()
    journal = args.output.with_name(args.output.name + ".journal.jsonl")
    # Validate *both* paths BEFORE any provider/model call; do not discard
    # measurements because a target output was pre-existing or non-local.
    _check_new_path(args.output)
    _check_new_path(journal)
    if journal.is_relative_to(args.repo_root) or (
        args.evidence_root is not None
        and journal.is_relative_to(args.evidence_root)
    ):
        raise W4ModelABBlocked("journal must be outside checkout and original")
    engine = RelayEngine(LlamaCppRelayProvider(
        endpoint=endpoint, model=args.model,
    ))
    fd = os.open(journal, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as witness:
        def record(row: dict[str, object]) -> None:
            witness.write((json.dumps(
                row, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"), allow_nan=False,
            ) + "\n").encode("utf-8"))
            witness.flush()
            os.fsync(witness.fileno())

        record({
            "schema": "W4_LOCAL_MODEL_AB_DEV_JOURNAL_V1",
            "source_class": args.source,
            "repo_head": args.expected_head,
            "model_alias": args.model,
            "classification": "IN_PROGRESS_UNQUALIFIED",
        })
        result = run_matched_ab(
            cases=cases, engine=engine,
            repeats=args.repeats, warmup_pairs=args.warmup_pairs,
            include_open=not args.no_open, on_record=record,
        )
    result["journal_sha256"] = hashlib.sha256(journal.read_bytes()).hexdigest()
    result["repo_head"] = args.expected_head
    result["model_alias"] = args.model
    result["endpoint_scope"] = "HTTP_LOOPBACK_ONLY"
    result["real_source_head"] = SOURCE_HEAD if args.source == "real" else None
    result["real_source_run"] = SOURCE_RUN if args.source == "real" else None
    result["real_report_sha256"] = (
        SOURCE_REPORT_SHA if args.source == "real" else None
    )
    _write_new_report(args.output, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
