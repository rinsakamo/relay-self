"""Read-only counterfactual Defense-F1 replay of immutable R12 W3 stdout.

This is NOT a new World, new Self Action, independent damage-cause audit
or retrospective conversion of an original FAIL/DEATH into survival.
No original evidence, fence, report, manifest or Session is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    MineflayerStreamDecoder,
)
from adapters.mineflayer.s49_reactive_defense import (
    evaluate_native_damage_defense,
)
from adapters.mineflayer.self_world_stage_w3_capture import audit_w3_sealed_stdout
from tools.bug0_d14_natural_life import admissible_natural_attack

F1_NATIVE_REQUEST = re.compile(r"d14-r4-([0-9]{3})-(pre|fresh)\Z")


class F1ReplayRejected(ValueError):
    """The archived original W3 cannot support source-bounded replay."""


def replay_w3_f1(
    evidence_dir: Path, *,
    expected_session: str, expected_w3_sha256: str,
) -> dict[str, Any]:
    if (
        not isinstance(evidence_dir, Path) or not evidence_dir.is_dir()
        or evidence_dir.is_symlink()
        or not isinstance(expected_session, str) or not expected_session
        or not isinstance(expected_w3_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_w3_sha256) is None
    ):
        raise F1ReplayRejected("F1_VALID_ORIGINAL_EVIDENCE_AND_SHA_REQUIRED")
    try:
        receipt = audit_w3_sealed_stdout(evidence_dir)
    except Exception as exc:
        raise F1ReplayRejected("F1_W3_ORIGINAL_NOT_COMPLETE") from exc
    if receipt.get("session_id") != expected_session:
        raise F1ReplayRejected("F1_ORIGINAL_SESSION_NOT_MATCHED")
    raw = (evidence_dir / "w3-node-stdout.raw.jsonl").read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != expected_w3_sha256:
        raise F1ReplayRejected("F1_W3_ORIGINAL_SHA_MISMATCH")
    decoder = MineflayerStreamDecoder()
    pairs: dict[int, dict[str, MineflayerObservation]] = {}
    for raw_line in raw.splitlines(keepends=True):
        frame = decoder.decode(raw_line.decode("utf8"))
        if not isinstance(frame, MineflayerObservation):
            continue
        if frame.kind != "probe" or frame.request_id is None:
            continue
        match = F1_NATIVE_REQUEST.fullmatch(frame.request_id)
        if match is None:
            continue
        cycle = int(match.group(1))
        role = match.group(2)
        pair = pairs.setdefault(cycle, {})
        if role in pair:
            raise F1ReplayRejected("F1_DUPLICATED_NATIVE_PROBE_REQUEST")
        pair[role] = frame
    if not pairs:
        raise F1ReplayRejected("F1_NO_ORIGINAL_R12_NATIVE_DECISIONS")
    last_native = None
    records = []
    reasons: Counter[str] = Counter()
    diagnostic_counts: Counter[str] = Counter()
    complete = 0
    reactive_candidates = 0
    stationary_r9_candidates = 0
    earlier_seq = -1
    for cycle in sorted(pairs):
        pair = pairs[cycle]
        if "pre" not in pair or "fresh" not in pair:
            records.append({
                "cycle": cycle, "paired": False,
                "interpretation": "SOURCE_ONLY_UNPAIRED_NOT_ACTION",
            })
            continue
        before, after = pair["pre"], pair["fresh"]
        if before.seq <= earlier_seq or after.seq <= before.seq:
            raise F1ReplayRejected("F1_REORDERED_OR_REPLAYED_NATIVE_SOURCE")
        earlier_seq = after.seq
        complete += 1
        candidate = None
        rejected = []
        for witness in (before, last_native):
            proposal, reason = evaluate_native_damage_defense(
                before, after, witness,
            )
            if proposal is not None:
                candidate = proposal
                break
            rejected.append(reason)
        views = (before.snapshot, after.snapshot)
        zombies = [[e for e in view.nearby_entities if e.name == "zombie"] for view in views]
        failures = []
        if any(view.oxygen_level is None for view in views):
            failures.append("OXYGEN_UNKNOWN")
        if any(view.oxygen_level is not None and view.oxygen_level <= 0 for view in views):
            failures.append("OXYGEN_ZERO")
        if any(view.health <= 0 for view in views):
            failures.append("SELF_NOT_ALIVE")
        if any(view.nearby_entities_coverage.truncated for view in views):
            failures.append("COVERAGE_TRUNCATED")
        if any(view.nearby_entities_coverage.candidate_count != 1 or
               len(view.nearby_entities) != 1 for view in views):
            failures.append("NOT_EXACTLY_ONE_TOTAL_ENTITY")
        if any(len(group) != 1 for group in zombies):
            failures.append("NOT_EXACTLY_ONE_VISIBLE_ZOMBIE")
        if all(len(group) == 1 for group in zombies):
            old, new = zombies[0][0], zombies[1][0]
            if old.entity_id != new.entity_id:
                failures.append("ZOMBIE_ID_CHANGED")
            if not 0.1 <= old.distance <= 4.0 or not 0.1 <= new.distance <= 2.8:
                failures.append("ZOMBIE_OUT_OF_RANGE")
            if any(abs(getattr(old.position, axis) - getattr(new.position, axis)) > 2.0
                   for axis in ("x", "y", "z")):
                failures.append("ZOMBIE_DISPLACEMENT")
        if any(abs(getattr(views[0].position, axis) -
                   getattr(views[1].position, axis)) > 0.9 for axis in ("x", "y", "z")):
            failures.append("SELF_DISPLACEMENT")
        if not any(w is not None and w.session_id == after.session_id and
                   w.seq <= before.seq < after.seq <= before.seq + 32 and
                   after.seq - w.seq <= 64 and w.snapshot.health > after.snapshot.health
                   for w in (before, last_native)):
            failures.append("NO_RECENT_HEALTH_LOSS_WITNESS")
        diagnostic_counts.update(failures)
        def position(value):
            return {axis: getattr(value, axis) for axis in ("x", "y", "z")}
        stationary = admissible_natural_attack(before, after)
        if stationary is not None:
            stationary_r9_candidates += 1
        if candidate is not None:
            reactive_candidates += 1
        reason = (
            "REACTIVE_NATIVE_HEALTH_LOSS_CANDIDATE"
            if candidate is not None else "/".join(rejected)
        )
        reasons[reason] += 1
        records.append({
            "cycle": cycle, "paired": True,
            "previous_request_id": before.request_id,
            "fresh_request_id": after.request_id,
            "all_diagnostic_failures": failures,
            "native_self_positions": [position(view.position) for view in views],
            "native_zombies": [[{
                "id": entity.entity_id, "distance": entity.distance,
                "position": position(entity.position),
            } for entity in group] for group in zombies],
            "nearby_entity_counts": [view.nearby_entities_coverage.candidate_count for view in views],
            "previous_seq": before.seq, "fresh_seq": after.seq,
            "native_health_previous": before.snapshot.health,
            "native_health_current": after.snapshot.health,
            "native_oxygen_previous": before.snapshot.oxygen_level,
            "native_oxygen_current": after.snapshot.oxygen_level,
            "r9_stationary_target_candidate": stationary,
            "f1_reactive_target_candidate": (
                candidate.target_entity_id if candidate else None
            ),
            "f1_candidate_reason": reason,
            "f1_candidate_health_loss": (
                candidate.health_loss if candidate else None
            ),
            "f1_witness_seq": (
                candidate.witness.seq if candidate else None
            ),
            "native_damage_causally_assigned_to_zombie": False,
            "actual_physical_action_from_this_replay": False,
        })
        last_native = after
    return {
        "status": "SOURCE_ONLY_COUNTERFACTUAL_NOT_REAL_WORLD",
        "scope": "ORIGINAL_W3_STDOUT_DECISION_REPLAY_NOT_PAPER_DAMAGE_CAUSE",
        "original_w3_sha256": sha, "original_session_id": expected_session,
        "w3_complete_node_stdout": True,
        "r12_complete_native_decision_pairs": complete,
        "r9_stationary_pair_candidates": stationary_r9_candidates,
        "f1_health_loss_reactive_candidates": reactive_candidates,
        "decision_refusal_reasons": dict(sorted(reasons.items())),
        "overlapping_diagnostic_counts": dict(sorted(diagnostic_counts.items())),
        "decision_rows": records,
        "original_action_issued_or_outcome_proven_by_replay": False,
        "original_world_24000_survival_proven_by_replay": False,
        "original_dead_self_resurrected": False,
        "zombie_causality_attested": False,
        "new_physical_authority": False,
        "new_world_created": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--expected-session-id", required=True)
    parser.add_argument("--expected-w3-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    root = options.evidence_dir.resolve(strict=True)
    output = options.output
    if (
        output.exists() or output.is_symlink()
        or not output.is_absolute()
        or not output.parent.is_dir() or output.parent.is_symlink()
        or root == output.parent or root in output.parents
    ):
        parser.error("F1 requires exclusive new derived output outside original evidence")
    result = replay_w3_f1(
        root, expected_session=options.expected_session_id,
        expected_w3_sha256=options.expected_w3_sha256,
    )
    with output.open("x", encoding="utf8") as dst:
        json.dump(result, dst, sort_keys=True, indent=2, ensure_ascii=False)
        dst.write("\n")
        dst.flush()
        os.fsync(dst.fileno())


if __name__ == "__main__":
    main()
