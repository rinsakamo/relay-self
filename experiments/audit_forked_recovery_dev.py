"""#858 P0-C two-phase read-only fork recovery DEV audit.

prelaunch: BEFORE starting restored World, compare full archive+copy, load
Self A/B derived files, existing Self-owned WAL and independent ticketed
Paper/native event record. Never issues Minecraft actions.
postlaunch: AFTER restored World is running, read ONLY prelaunch decision
and fresh new-branch WorldBody observation; do not re-hash mutable World files.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from relay_self.attack_world_join_dev import (
    AttackWorldJoinError,
    NativeIdentityWitness,
    ServerAttackTicket,
    ServerDamageEvent,
    ServerDeathEvent,
    attack_from_restored_wal,
)
from relay_self.causal_recovery import WalState, project_physical_journal
from relay_self.forked_recovery_dev import (
    ForkRecoveryDevDecision,
    ForkRecoveryDevError,
    ForkRecoveryDevStatus,
    FreshForkObservation,
    SourceWorldCutWitness,
    joined_action_effect_dev,
    load_derived_cognitive_cut_dev,
    prepare_forked_recovery_dev,
    reproject_present_from_fresh_world_dev,
)
from relay_self.physical_action_journal import (
    PhysicalActionJournal,
    PhysicalJournalError,
)
from relay_self.world_checkpoint_dev import WorldCheckpointError


def _read(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not dict:
        raise ForkRecoveryDevError("JSON object required")
    return data


def _write_new(path: Path, decision: ForkRecoveryDevDecision) -> None:
    if path.exists() or path.is_symlink() or not path.parent.is_dir():
        raise ForkRecoveryDevError("new result path in preexisting parent required")
    body = {"schema": 1, "source_authentication": "DEV_UNVERIFIED",
            "decision": asdict(decision)}
    raw = (json.dumps(body, sort_keys=True, indent=2) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())


def _load_plan(path: Path) -> ForkRecoveryDevDecision:
    value = _read(path)
    if set(value) != {"schema", "source_authentication", "decision"}:
        raise ForkRecoveryDevError("invalid prelaunch plan evidence")
    if value["schema"] != 1 or value["source_authentication"] != "DEV_UNVERIFIED":
        raise ForkRecoveryDevError("foreign prelaunch plan")
    decision = value["decision"]
    expected = set(ForkRecoveryDevDecision.__dataclass_fields__)
    if type(decision) is not dict or set(decision) != expected:
        raise ForkRecoveryDevError("unexpected prelaunch decision fields")
    for field in (
        "historical_native_sessions", "included_action_ids",
        "remembered_postcut_action_ids", "retained_beliefs", "blockers", "next_steps",
    ):
        if type(decision[field]) is not list:
            raise ForkRecoveryDevError("invalid prelaunch list field")
        decision[field] = tuple(decision[field])
    decision["status"] = ForkRecoveryDevStatus(decision["status"])
    restored = ForkRecoveryDevDecision(**decision)
    if restored.physical_action_issue_authorized or restored.self_owner_restored:
        raise ForkRecoveryDevError("prelaunch plan cannot assert physical authority")
    return restored


def prelaunch(
    archive: Path, restored: Path, cut_path: Path,
    self_paths: list[Path], wal_path: Path, join_path: Path,
    output_path: Path,
) -> ForkRecoveryDevDecision:
    """Audit source branch event membership and copy BEFORE server starts."""
    if len(self_paths) < 2 or len(self_paths) != len(set(self_paths)):
        raise ForkRecoveryDevError("at least two distinct Self evidence paths required")
    source_cut = _read(cut_path)
    if type(source_cut.get("included_effect_event_ids")) is not list:
        raise ForkRecoveryDevError("cut membership must be a JSON array")
    source_cut["included_effect_event_ids"] = tuple(
        source_cut["included_effect_event_ids"]
    )
    cut = SourceWorldCutWitness(**source_cut)
    selves = tuple(load_derived_cognitive_cut_dev(p) for p in self_paths)
    event_input = _read(join_path)
    if set(event_input) != {
        "self_id", "action_id", "world_id", "branch_id", "native_identity",
        "server_attack_ticket", "server_damage_events", "server_death_events",
    }:
        raise ForkRecoveryDevError("P0-B join source record fields mismatch")
    journal = PhysicalActionJournal.restore(
        wal_path, self_id=event_input["self_id"],
    )
    wal = project_physical_journal(journal, self_id=event_input["self_id"])
    effects = ()
    if (event_input["server_attack_ticket"] is not None
            and event_input["native_identity"] is not None
            and len(event_input["server_damage_events"]) == 1
            and any(
                entry.action_id == event_input["action_id"]
                and entry.status is WalState.NATIVE_ATTACK_HURT_OBSERVED
                for entry in wal
            )):
        attack = attack_from_restored_wal(
            journal, self_id=event_input["self_id"],
            action_id=event_input["action_id"],
        )
        n = NativeIdentityWitness(**event_input["native_identity"])
        ticket = ServerAttackTicket(**event_input["server_attack_ticket"])
        damage = ServerDamageEvent(**event_input["server_damage_events"][0])
        if len(event_input["server_death_events"]) > 1:
            raise ForkRecoveryDevError("ambiguous server death events")
        death = (
            None if not event_input["server_death_events"] else
            ServerDeathEvent(**event_input["server_death_events"][0])
        )
        effects = (
            joined_action_effect_dev(
                attack, n, ticket=ticket, damage=damage, death=death,
            ),
        )
    result = prepare_forked_recovery_dev(
        archive, restored, cut=cut, selves=selves, wal=wal, effects=effects,
    )
    _write_new(output_path, result)
    return result


def postlaunch(
    plan_path: Path, fresh_path: Path, output_path: Path,
) -> ForkRecoveryDevDecision:
    plan = _load_plan(plan_path)
    fresh = FreshForkObservation(**_read(fresh_path))
    result = reproject_present_from_fresh_world_dev(plan, fresh)
    _write_new(output_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="phase", required=True)
    first = subs.add_parser("prelaunch")
    first.add_argument("--archive", type=Path, required=True)
    first.add_argument("--restored-world", type=Path, required=True)
    first.add_argument("--source-cut-json", type=Path, required=True)
    first.add_argument("--self-cut", type=Path, action="append", required=True)
    first.add_argument("--wal", type=Path, required=True)
    first.add_argument("--ticket-world-join-json", type=Path, required=True)
    first.add_argument("--output", type=Path, required=True)
    second = subs.add_parser("postlaunch")
    second.add_argument("--prelaunch-plan", type=Path, required=True)
    second.add_argument("--fresh-worldbody-json", type=Path, required=True)
    second.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.phase == "prelaunch":
            result = prelaunch(
                args.archive, args.restored_world, args.source_cut_json,
                args.self_cut, args.wal, args.ticket_world_join_json,
                args.output,
            )
        else:
            result = postlaunch(
                args.prelaunch_plan, args.fresh_worldbody_json, args.output,
            )
    except (
        OSError, ValueError, KeyError, TypeError,
        PhysicalJournalError, AttackWorldJoinError, ForkRecoveryDevError,
        WorldCheckpointError,
    ) as exc:
        parser.exit(2, f"P0C_RECOVERY_DEV_REFUSED: {exc}\n")
    print(json.dumps(asdict(result), sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
