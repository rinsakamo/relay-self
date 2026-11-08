"""D12 R2 -> source-qualified read-only Experience view for long-run Learning.

This is NOT Learning.commit, Memory writing, model inference, or an S49 issuer.
The current D12/D8 original-world independent post audits remain the gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.bug0_d12_third_intent_rearm_post import audit_d12
from tools.bug0_d6_multigen_world import _tick, _uuid
from tools.bug0_d7e_staged_move_eat_post import native_integral_food


class D12ExperienceBridgeRejected(ValueError):
    """Cannot turn unsupported World source into learned personal experience."""


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _move_ids(rows: object) -> list[str]:
    if not isinstance(rows, list):
        raise D12ExperienceBridgeRejected("MISSING_ORIGINAL_MOVE_ACTIONS")
    ids: list[str] = []
    for row in rows:
        if (not isinstance(row, dict) or type(row.get("action_id")) is not str
                or not row["action_id"]):
            raise D12ExperienceBridgeRejected("MALFORMED_ORIGINAL_MOVE_ACTION")
        ids.append(row["action_id"])
    return ids


def _source_eat(
    receipt: object, *, session: str, generation: int, count: int,
    preceding_rotten: int, zombie_uuid: str, world: str, tick: int,
    attack_id: str, move_ids: list[str],
) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise D12ExperienceBridgeRejected("MISSING_ACTUAL_S51_EAT_RECEIPT")
    before = native_integral_food(receipt.get("food_before"))
    after = native_integral_food(receipt.get("food_after"))
    action_id = receipt.get("action_id")
    expected_before = preceding_rotten + count
    if (
        type(action_id) is not str or not action_id
        or receipt.get("session_id") != session
        or receipt.get("consumed_item") != "rotten_flesh"
        or type(count) is not int or count not in (1, 2)
        or receipt.get("count_before") != expected_before
        or receipt.get("count_after") != expected_before - 1
        or after <= before
        or type(attack_id) is not str or not attack_id
    ):
        raise D12ExperienceBridgeRejected("S51_EAT_RECEIPT_SOURCE_DISAGREEMENT")
    return {
        "experience_id": f"d12:{world}:{session}:food:{generation}:{action_id}",
        "event_kind": "OBSERVED_FOOD_CYCLE",
        "source_class": "PAPER_NATIVE_AND_S49_S51_INDEPENDENTLY_AUDITED",
        "world_uuid": world,
        "native_session_id": session,
        "intent_epoch": generation,
        "paper_zombie_uuid": zombie_uuid,
        "paper_death_tick": tick,
        "native_action_ids": {
            "attack": [attack_id], "move": move_ids, "eat": [action_id],
        },
        "observation": {
            "vanilla_rotten_dropped": count,
            "food_before": before,
            "food_after": after,
            "rotten_before_eat": expected_before,
            "rotten_after_eat": expected_before - 1,
            "native_eat_terminal": "S16_OUTCOME",
        },
        "prediction": None,
        "learned_rule": None,
        "inference": "OBSERVED_TRANSITION_NOT_CAUSAL_GENERALIZATION",
    }


def _project_pass(report: dict, original_log: str, audit: dict) -> list[dict[str, Any]]:
    """Only reached after audit_d12 proved BOTH physical food cycles and rearm."""
    if (
        audit.get("status") != "PASS_DEV"
        or audit.get("classification")
            != "D12_TWO_TRUE_MEALS_THIRD_REAL_WORLD_INTENT_REARM_PASS"
        or audit.get("two_real_food_cycles") is not True
        or audit.get("third_real_attack_or_eat") is not False
        or audit.get("third_spawn_after_exactly_600_world_ticks") is not True
        or audit.get("additional_physical_actions") != 0
        or report.get("learning_updated") is not False
        or report.get("real_model_calls") != 0
    ):
        raise D12ExperienceBridgeRejected("D12_INDEPENDENT_SOURCE_NOT_QUALIFIED")
    g2 = report.get("d8_second_generation")
    rearm = report.get("d12_third_rearm")
    if not isinstance(g2, dict) or not isinstance(rearm, dict):
        raise D12ExperienceBridgeRejected("MISSING_GENERATION_LINEAGE")
    sid = report.get("session_id")
    if type(sid) is not str or not sid or rearm.get("session_id") != sid:
        raise D12ExperienceBridgeRejected("SESSION_LINEAGE_INVALID")
    first = report.get("initial_paper")
    second = report.get("paper_respawn")
    third = report.get("d12_third_paper_spawn")
    if any(type(v) is not str or v not in original_log for v in (first, second, third)):
        raise D12ExperienceBridgeRejected("PAPER_ORIGINALS_MISSING")
    world = _uuid(first, "world")
    if any(_uuid(v, "world") != world for v in (second, third)):
        raise D12ExperienceBridgeRejected("MULTIPLE_WORLDS_NOT_ONE_SELF")
    z1, z2, z3 = (_uuid(line, "entity") for line in (first, second, third))
    if len({z1, z2, z3}) != 3:
        raise D12ExperienceBridgeRejected("REUSED_ZOMBIE_UUID")
    first_attacks = report.get("s49_actions")
    if not isinstance(first_attacks, list) or len(first_attacks) != 1:
        raise D12ExperienceBridgeRejected("FIRST_ATTACK_NOT_SINGLE_SOURCE")
    first_attack = first_attacks[0]
    if not isinstance(first_attack, dict):
        raise D12ExperienceBridgeRejected("FIRST_ATTACK_SOURCE_MISSING")
    first_count = report.get("real_rotten_flesh_count")
    second_count = g2.get("real_rotten_flesh_count")
    first_receipt = report.get("d7f_eat_outcome")
    second_receipt = g2.get("d7f_eat_outcome")
    if type(first_count) is not int or type(second_count) is not int:
        raise D12ExperienceBridgeRejected("ACTUAL_DROPS_NOT_IN_SOURCE")
    e1 = _source_eat(
        first_receipt, session=sid, generation=1, count=first_count,
        preceding_rotten=0, world=world, zombie_uuid=z1,
        tick=_tick(report["paper_respawn_death"]),
        attack_id=first_attack.get("action_id"),
        move_ids=_move_ids(report.get("d6_original_s49_move_actions")),
    )
    e2 = _source_eat(
        second_receipt, session=sid, generation=2, count=second_count,
        preceding_rotten=first_count - 1, world=world, zombie_uuid=z2,
        tick=g2.get("death_tick"),
        attack_id=report.get("d8_original_second_attack_action_id"),
        move_ids=_move_ids(g2.get("d6_original_s49_move_actions")),
    )
    old_actions = e1["native_action_ids"]
    new_actions = e2["native_action_ids"]
    consumed = [
        *old_actions["attack"], *old_actions["move"], *old_actions["eat"],
        *new_actions["attack"], *new_actions["move"], *new_actions["eat"],
    ]
    if (len(consumed) != len(set(consumed))
            or rearm.get("prior_original_action_count") != len(consumed)
            or rearm.get("after_rearm_original_action_count") != len(consumed)
            or rearm.get("prior_second_s51_action_id") != second_receipt["action_id"]
            or rearm.get("original_s49_epoch") != 3
            or rearm.get("third_physical_action_count") != 0):
        raise D12ExperienceBridgeRejected("ORIGINAL_S49_ACTION_HISTORY_MISMATCH")
    third_tick = _tick(third)
    prior_tick = g2.get("death_tick")
    if (
        type(prior_tick) is not int
        or third_tick != prior_tick + 600
        or rearm.get("paper_spawn_tick") != third_tick
        or rearm.get("new_intent_id") == rearm.get("completed_intent_id")
        or rearm.get("completed_intent_id")
            != report.get("d8_intent_rearm", {}).get("next_intent")
    ):
        raise D12ExperienceBridgeRejected("THIRD_WORLD_INTENT_NOT_SOURCE_QUALIFIED")
    e3 = {
        "experience_id": (
            f"d12:{world}:{sid}:intent:3:{rearm['new_intent_id']}"
        ),
        "event_kind": "OBSERVED_WORLD_RESPAWN_AND_INTENT_REARM",
        "source_class": "PAPER_NATIVE_AND_ORIGINAL_INTENT_AUDITED",
        "world_uuid": world,
        "native_session_id": sid,
        "intent_epoch": 3,
        "paper_zombie_uuid": z3,
        "paper_spawn_tick": third_tick,
        "preceding_paper_death_tick": prior_tick,
        "native_zombie_entity_id": rearm["third_zombie_native_id"],
        "native_source_seq": rearm["native_source_seq"],
        "source_request_id": rearm["native_request_id"],
        "completed_intent_id": rearm["completed_intent_id"],
        "committed_intent_id": rearm["new_intent_id"],
        "prior_consumed_s51_eat_action_id": second_receipt["action_id"],
        "observation": {
            "world_respawn_delay_ticks": 600,
            "retained_original_s49_action_count": len(consumed),
            "new_original_s49_actions": 0,
            "third_attack": "NOT_ISSUED",
            "third_pickup": "NOT_OBSERVED",
            "third_eat": "NOT_ISSUED",
        },
        "prediction": None,
        "learned_rule": None,
        "inference": "INTENT_TRANSITION_NOT_FOOD_CYCLE_OR_LEARNING",
    }
    return [e1, e2, e3]


def project_d12(
    report: dict, original_log: str, *, nonmotion_path: Path,
    motion_path: Path, s50_jsonl: str, source_sha256: dict[str, str],
) -> dict[str, Any]:
    """Trusted path: independently evaluate D8+D12 before any projection."""
    audited = audit_d12(
        report, original_log, nonmotion_path=nonmotion_path,
        motion_path=motion_path, s50_jsonl=s50_jsonl,
    )
    if audited["status"] == "NOT_EXERCISED":
        return {
            "classification": "DEV_D12_SOURCE_NOT_EXERCISED_READ_ONLY",
            "source_status": "NOT_EXERCISED",
            "source_audit": audited["classification"],
            "source_sha256": source_sha256,
            "events": [],
            "new_physical_actions": 0,
            "memory_writes": 0, "learning_updates": 0, "l2_calls": 0,
            "skill_installs": 0,
            "note": "A natural zero or incomplete second food cycle is not two meals.",
        }
    episodes = _project_pass(report, original_log, audited)
    return {
        "classification": "DEV_D12_THREE_EPOCH_EXPERIENCE_PROJECTION",
        "source_status": "PASS_DEV",
        "source_audit": audited["classification"],
        "source_sha256": source_sha256,
        "world_uuid": episodes[0]["world_uuid"],
        "native_session_id": episodes[0]["native_session_id"],
        "events": episodes,
        "observed_food_cycles": 2, "retained_action_count": len(
            episodes[0]["native_action_ids"]["attack"]
            + episodes[0]["native_action_ids"]["move"]
            + episodes[0]["native_action_ids"]["eat"]
            + episodes[1]["native_action_ids"]["attack"]
            + episodes[1]["native_action_ids"]["move"]
            + episodes[1]["native_action_ids"]["eat"]
        ),
        "third_intent_committed": True,
        "third_food_cycle_observed": False,
        "new_physical_actions": 0,
        "memory_writes": 0, "learning_updates": 0, "l2_calls": 0,
        "skill_installs": 0,
        "qual": "NO_GO", "science": "NOT_RUN",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "report", "server-log", "nonmotion-fence", "motion-fence",
        "s50-sidecar", "out",
    ):
        parser.add_argument("--" + name, required=True, type=Path)
    a = parser.parse_args()
    srcs = {
        "report": a.report, "server-log": a.server_log,
        "nonmotion-fence": a.nonmotion_fence, "motion-fence": a.motion_fence,
        "s50-sidecar": a.s50_sidecar,
    }
    raw = {name: path.read_bytes() for name, path in srcs.items()}
    result = project_d12(
        json.loads(raw["report"]), raw["server-log"].decode("utf-8"),
        nonmotion_path=a.nonmotion_fence, motion_path=a.motion_fence,
        s50_jsonl=raw["s50-sidecar"].decode("utf-8"),
        source_sha256={name: _digest(data) for name, data in raw.items()},
    )
    # Reject concurrent source modification during audit, rather than
    # treating a post-hoc digest as evidence of the bytes actually audited.
    if any(_digest(path.read_bytes()) != _digest(raw[name])
           for name, path in srcs.items()):
        raise D12ExperienceBridgeRejected("PHYSICAL_SOURCE_CHANGED_DURING_PROJECTION")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(result["classification"], "events=", len(result["events"]))


if __name__ == "__main__":
    main()
