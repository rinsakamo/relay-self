"""#855 Offline DEV audit: actual Self-owned WAL + independently captured records.

Input JSON only describes observations; it does not authenticate a Paper
server event log or server-armed correlation marker. This program never
issues an Action, restarts a World, replays a WAL or updates Self state.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from relay_self.attack_world_join_dev import (
    AttackWorldJoinError,
    NativeIdentityWitness,
    ServerAttackTicket,
    ServerDamageEvent,
    ServerDeathEvent,
    attack_from_restored_wal,
    join_attack_world_dev,
)
from relay_self.physical_action_journal import PhysicalActionJournal, PhysicalJournalError


def audit_attack_world_join(wal_path: Path, record: dict) -> dict:
    """Return a DEV-only candidate association, not an authority claim."""
    if type(record) is not dict or set(record) != {
        "self_id", "action_id", "world_id", "branch_id",
        "native_identity", "server_attack_ticket",
        "server_damage_events", "server_death_events",
    }:
        raise AttackWorldJoinError("exact causal-record JSON fields required")
    if type(record["server_damage_events"]) is not list or type(
        record["server_death_events"]
    ) is not list:
        raise AttackWorldJoinError("server events must be JSON lists")
    journal = PhysicalActionJournal.restore(wal_path, self_id=record["self_id"])
    wal = attack_from_restored_wal(
        journal, self_id=record["self_id"], action_id=record["action_id"],
    )
    native = (
        None if record["native_identity"] is None
        else NativeIdentityWitness(**record["native_identity"])
    )
    ticket = (
        None if record["server_attack_ticket"] is None
        else ServerAttackTicket(**record["server_attack_ticket"])
    )
    damages = tuple(ServerDamageEvent(**ev) for ev in record["server_damage_events"])
    deaths = tuple(ServerDeathEvent(**ev) for ev in record["server_death_events"])
    outcome = join_attack_world_dev(
        wal, native, world_id=record["world_id"], branch_id=record["branch_id"],
        ticket=ticket, damage_events=damages, death_events=deaths,
    )
    return {
        **asdict(outcome), "status": outcome.status.value,
        "source_authentication": "NOT_VERIFIED_BY_OFFLINE_DEV",
        "provenance": "CALLER_SUPPLIED_RECORDS_PLUS_RESTORED_SELF_WAL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wal", type=Path, required=True)
    parser.add_argument("--join-record-json", type=Path, required=True)
    args = parser.parse_args()
    try:
        record = json.loads(args.join_record_json.read_text(encoding="utf-8"))
        output = audit_attack_world_join(args.wal, record)
    except (
        AttackWorldJoinError, PhysicalJournalError, OSError, ValueError,
        TypeError, KeyError,
    ) as exc:
        parser.exit(2, f"ATTACK_WORLD_DEV_JOIN_REFUSED: {exc}\n")
    print(json.dumps(output, sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
