"""DEV-only SOUL A/B/C/D, identical K3-G L2 task and zero mock/World Actions.

Execute ONE condition per explicit invocation. This tests a model-visible value
prior, not established persistent MySelf identity or developed personality.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.skill_crystallization_k3g_ten_action_choice_dev import (
    run_choice,
    verify_input_manifests,
)

# Neutral reproduces the original K3-G system instruction byte-for-byte.
# Variant names and expected behavior are never placed in the L2 request.
SOUL_DIRECTIVES: dict[str, str | None] = {
    "neutral": None,
    "curious": (
        "Learning about relevant uncertainty matters to you even when a "
        "bounded attempt might fail. You still care about resources, "
        "viability and the limits of your actions."
    ),
    "cautious": (
        "Preserving viability and avoiding poorly understood losses matter "
        "to you under uncertainty. You still value useful learning "
        "opportunities and respect the limits of your actions."
    ),
    "bold": (
        "You value learning through bounded trial and error and can "
        "tolerate unsuccessful attempts. You still care about "
        "consequences, resources and the limits of your actions."
    ),
}


def select_directive(condition: str) -> str | None:
    if condition not in SOUL_DIRECTIVES:
        raise ValueError("UNKNOWN_SOUL_CONDITION")
    return SOUL_DIRECTIVES[condition]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def run_matched_choice(
    originals: list[dict[str, Any]],
    *, condition: str, mode: str,
    fixture: dict[str, Any] | None = None,
    endpoint: str | None = None,
    model: str | None = None,
    record_dir: Path | None = None,
    timeout: float = 300,
) -> dict[str, Any]:
    """Run one decision without evaluating even a valid changed Skill.

    K3-G preserves its original behavior unless optional arguments are used.
    No SOUL label, fake experience, probe outcome or evaluation seed is passed.
    """
    if len(originals) != 4:
        raise ValueError("REQUIRE_FOUR_HISTORIC_REPORTS")
    directive = select_directive(condition)
    result = run_choice(
        *originals, mode=mode, fixture=fixture,
        endpoint=endpoint, model=model, timeout=timeout,
        record_dir=record_dir, soul_directive=directive,
        evaluate_skill=False,
    )
    report = dict(result)
    report.update({
        "classification": "DEV_ONLY_SOUL_MATCHED_L2_CHOICE_ONLY",
        "soul_condition": condition,
        "soul_directive": directive,
        "soul_directive_sha256": _sha(
            (directive or "").encode("utf-8"),
        ),
        "comparison_protocol": "K3G_1_TO_10_SAME_TASK_SCHEMA_OBSERVATIONS",
        "choice_semantically_valid": "PROPOSAL_VALIDATED" in result["stages"],
        "raw_model_choice": (
            result["proposal"].get("status")
            if isinstance(result["proposal"], dict) else None
        ),
        "observed_actions": 0,
        "holdout_or_probe_executed": False,
        "personality_or_learning_proven": False,
    })
    if report["skill_holdout"] is not None or report["skill_holdout_seed"] is not None:
        raise ValueError("MATCHED_SOUL_MUST_NOT_OPEN_SKILL_HOLDOUT")
    if report["native_s49_actions"] != 0:
        raise ValueError("MATCHED_SOUL_MUST_NOT_ISSUE_S49")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--condition", choices=tuple(SOUL_DIRECTIVES), required=True)
    p.add_argument("--mode", choices=("fixture", "gemma"), required=True)
    p.add_argument("--first", type=Path, required=True)
    p.add_argument("--k3b-report", type=Path, required=True)
    p.add_argument("--k3d-report", type=Path, required=True)
    p.add_argument("--k3e-report", type=Path, required=True)
    p.add_argument("--fixture", type=Path)
    p.add_argument("--endpoint")
    p.add_argument("--model")
    p.add_argument("--timeout", type=float, default=300)
    p.add_argument("--record-dir", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    paths = [args.first, args.k3b_report, args.k3d_report, args.k3e_report]
    audit = verify_input_manifests(paths) if args.mode == "gemma" else None
    originals = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    fixture = (
        json.loads(args.fixture.read_text(encoding="utf-8"))
        if args.fixture is not None else None
    )
    result = run_matched_choice(
        originals, condition=args.condition, mode=args.mode,
        fixture=fixture, endpoint=args.endpoint,
        model=args.model, record_dir=args.record_dir,
        timeout=args.timeout,
    )
    result["source_files_sha256"] = {
        name: _sha(path.read_bytes()) for name, path in
        zip(("first", "k3b", "k3d", "k3e"), paths)
    }
    if audit is not None:
        result["original_manifest_audit"] = audit
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(f"SOUL matched choice {args.condition}: raw={result['raw_model_choice']} "
          f"validator={result['choice_semantically_valid']} out={args.out}")


if __name__ == "__main__":
    main()
