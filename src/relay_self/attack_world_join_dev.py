"""#855 P0-B: read-only DEV join of ATTACK WAL and server damage/death evidence.

NEVER issues an Action or changes WAL, World, skill or Intent.
Native and server values must originate in *different real observation
streams*; this pure model cannot independently authenticate their origins.
A matching server attack event without a server-armed action ticket only
confirms an actor/target damage observation, not which L0 Action caused it.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum

from relay_self.physical_action_journal import PhysicalActionJournal


class AttackWorldJoinError(ValueError):
    """Malformed evidence or noncanonical native / server identity."""


class AttackWorldJoinStatus(str, Enum):
    HOLD_UNKNOWN = "HOLD_UNKNOWN"
    DEV_SERVER_DAMAGE_UNJOINED = "DEV_SERVER_DAMAGE_UNJOINED"
    DEV_ACTION_DAMAGE_CORRELATED = "DEV_ACTION_DAMAGE_CORRELATED"
    DEV_ACTION_DEATH_CORRELATED = "DEV_ACTION_DEATH_CORRELATED"


def _text(name: str, value: object) -> None:
    if type(value) is not str or not value.strip() or any(c.isspace() for c in value):
        raise AttackWorldJoinError(f"{name} requires a whitespace-free identity")


def _uint(name: str, value: object) -> None:
    if type(value) is not int or value < 0:
        raise AttackWorldJoinError(f"{name} must be nonnegative int")


def _uuid(name: str, value: object) -> None:
    _text(name, value)
    try:
        u = uuid.UUID(value)
    except ValueError as exc:
        raise AttackWorldJoinError(f"{name} must be a UUID") from exc
    if str(u) != value:
        raise AttackWorldJoinError(f"{name} must use canonical lowercase UUID")


@dataclass(frozen=True, slots=True)
class AttackWalEvidence:
    self_id: str
    action_id: str
    session_id: str
    native_target_ref: str
    native_probe_seq: int
    native_actor_entity_id: int
    native_hurt_seq: int
    native_ack_seq: int
    native_after_seq: int
    journal_sha256: str
    status: str = "NATIVE_ATTACK_HURT_OBSERVED"

    def __post_init__(self) -> None:
        for name in (
            "self_id", "action_id", "session_id", "native_target_ref",
            "journal_sha256",
        ):
            _text(name, getattr(self, name))
        if (not self.native_target_ref.startswith("entity:")
                or not self.native_target_ref.removeprefix("entity:").isdecimal()
                or str(int(self.native_target_ref.removeprefix("entity:")))
                != self.native_target_ref.removeprefix("entity:")):
            raise AttackWorldJoinError("native entity target must be canonical")
        for name in ("native_probe_seq", "native_actor_entity_id", "native_hurt_seq",
                     "native_ack_seq", "native_after_seq"):
            _uint(name, getattr(self, name))
        if (self.status != "NATIVE_ATTACK_HURT_OBSERVED"
                or not self.native_probe_seq < min(
                    self.native_ack_seq, self.native_hurt_seq,
                )
                or not max(self.native_ack_seq, self.native_hurt_seq) < self.native_after_seq):
            raise AttackWorldJoinError("terminal attributed ATTACK WAL required")
        if len(self.journal_sha256) != 64 or any(
            ch not in "0123456789abcdef" for ch in self.journal_sha256
        ):
            raise AttackWorldJoinError("noncanonical physical journal digest")


@dataclass(frozen=True, slots=True)
class NativeIdentityWitness:
    """Per-native-session mapping, not carried across World reboots."""

    self_id: str
    action_id: str
    session_id: str
    source_ref: str
    probe_seq: int
    runtime_target_entity_id: int
    runtime_actor_entity_id: int
    target_uuid: str
    actor_uuid: str

    def __post_init__(self) -> None:
        for name in ("self_id", "action_id", "session_id", "source_ref"):
            _text(name, getattr(self, name))
        for name in ("probe_seq", "runtime_target_entity_id", "runtime_actor_entity_id"):
            _uint(name, getattr(self, name))
        _uuid("target_uuid", self.target_uuid)
        _uuid("actor_uuid", self.actor_uuid)
        if self.runtime_actor_entity_id == self.runtime_target_entity_id:
            raise AttackWorldJoinError("attacker and victim cannot be same native ID")


@dataclass(frozen=True, slots=True)
class ServerAttackTicket:
    """DEV-only server acknowledgment of a one-shot Action correlation marker.

    Must be registered *before* the real physical Action, not synthesized
    afterward from a dead Zombie or native ACK. Server admission does not
    issue an attack; it only arms a one-shot observation correlation key.
    """

    world_id: str
    branch_id: str
    action_id: str
    native_session_id: str
    nonce: str
    actor_uuid: str
    target_uuid: str
    registered_at_tick: int
    server_ack_ref: str

    def __post_init__(self) -> None:
        for name in ("world_id", "branch_id", "action_id", "native_session_id",
                     "nonce", "server_ack_ref"):
            _text(name, getattr(self, name))
        _uuid("actor_uuid", self.actor_uuid)
        _uuid("target_uuid", self.target_uuid)
        _uint("registered_at_tick", self.registered_at_tick)


@dataclass(frozen=True, slots=True)
class ServerDamageEvent:
    world_id: str
    branch_id: str
    event_id: str
    tick: int
    victim_uuid: str
    attacker_uuid: str
    damage_cause: str
    health_before: float
    health_after: float
    server_source_ref: str
    ticket_nonce: str | None

    def __post_init__(self) -> None:
        for name in ("world_id", "branch_id", "event_id", "damage_cause",
                     "server_source_ref"):
            _text(name, getattr(self, name))
        _uuid("victim_uuid", self.victim_uuid)
        _uuid("attacker_uuid", self.attacker_uuid)
        _uint("damage tick", self.tick)
        if self.ticket_nonce is not None:
            _text("ticket_nonce", self.ticket_nonce)
        for h in (self.health_before, self.health_after):
            if type(h) not in (int, float) or not 0 <= h <= 2048:
                raise AttackWorldJoinError("invalid Health measurement")
        if self.health_after >= self.health_before:
            raise AttackWorldJoinError("damage event must show Health reduction")


@dataclass(frozen=True, slots=True)
class ServerDeathEvent:
    world_id: str
    branch_id: str
    event_id: str
    tick: int
    victim_uuid: str
    killer_uuid: str
    causing_damage_event_id: str | None
    server_source_ref: str

    def __post_init__(self) -> None:
        for name in ("world_id", "branch_id", "event_id", "server_source_ref"):
            _text(name, getattr(self, name))
        _uuid("victim_uuid", self.victim_uuid)
        _uuid("killer_uuid", self.killer_uuid)
        _uint("death tick", self.tick)
        if self.causing_damage_event_id is not None:
            _text("causing_damage_event_id", self.causing_damage_event_id)


@dataclass(frozen=True, slots=True)
class AttackWorldJoinDecision:
    status: AttackWorldJoinStatus
    parent_action_id: str
    target_uuid: str | None
    world_damage_event_id: str | None
    world_death_event_id: str | None
    sources: tuple[str, ...]
    reasons: tuple[str, ...]
    action_issue_authorized: bool = False
    exact_causality_attested: bool = False


def attack_from_restored_wal(
    journal: PhysicalActionJournal, *, self_id: str, action_id: str,
) -> AttackWalEvidence:
    """Read a previously restored canonical Self-owned WAL; never clear it."""
    if not isinstance(journal, PhysicalActionJournal):
        raise AttackWorldJoinError("restored PhysicalActionJournal required")
    _text("self_id", self_id)
    _text("action_id", action_id)
    if journal._body["self_id"] != self_id:
        raise AttackWorldJoinError("foreign physical WAL")
    matched = [r for r in journal.records if r["action_id"] == action_id]
    if len(matched) != 1 or matched[0]["capability"] != "ATTACK":
        raise AttackWorldJoinError("exact existing ATTACK WAL identity required")
    row = matched[0]
    if row["status"] != "NATIVE_ATTACK_HURT_OBSERVED":
        raise AttackWorldJoinError("unresolved physical ATTACK WAL not terminal")
    return AttackWalEvidence(
        self_id=self_id, action_id=action_id, session_id=row["session_id"],
        native_target_ref=row["target_ref"], native_probe_seq=row["probe_seq"],
        native_actor_entity_id=row["actor_entity_id"],
        native_hurt_seq=row["hurt_seq"], native_ack_seq=row["effect_seqs"][0],
        native_after_seq=row["after_seq"], journal_sha256=journal.digest,
    )


def join_attack_world_dev(
    wal: AttackWalEvidence,
    native: NativeIdentityWitness | None,
    *,
    world_id: str,
    branch_id: str,
    ticket: ServerAttackTicket | None,
    damage_events: tuple[ServerDamageEvent, ...],
    death_events: tuple[ServerDeathEvent, ...] = (),
) -> AttackWorldJoinDecision:
    """Pure read-only DEV correlation; NEVER attests production causal identity."""
    if not isinstance(wal, AttackWalEvidence):
        raise AttackWorldJoinError("typed ATTACK WAL required")
    _text("world_id", world_id)
    _text("branch_id", branch_id)
    if native is not None and not isinstance(native, NativeIdentityWitness):
        raise AttackWorldJoinError("typed native witness required")
    if ticket is not None and not isinstance(ticket, ServerAttackTicket):
        raise AttackWorldJoinError("typed server ticket required")
    if (type(damage_events) is not tuple or not all(
            isinstance(x, ServerDamageEvent) for x in damage_events)
            or type(death_events) is not tuple or not all(
                isinstance(x, ServerDeathEvent) for x in death_events)):
        raise AttackWorldJoinError("typed independent server event tuples required")
    if (len({x.event_id for x in damage_events}) != len(damage_events)
            or len({x.event_id for x in death_events}) != len(death_events)):
        raise AttackWorldJoinError("duplicated independent server event ID")
    reasons: list[str] = []
    sources = {f"wal:{wal.journal_sha256}"}
    def result(
        status: AttackWorldJoinStatus, damage: ServerDamageEvent | None = None,
        death: ServerDeathEvent | None = None,
    ) -> AttackWorldJoinDecision:
        return AttackWorldJoinDecision(
            status, wal.action_id, None if native is None else native.target_uuid,
            None if damage is None else damage.event_id,
            None if death is None else death.event_id,
            tuple(sorted(sources)), tuple(sorted(set(reasons))),
        )

    if native is None:
        reasons.append("native session Entity ID-to-UUID witness absent")
        return result(AttackWorldJoinStatus.HOLD_UNKNOWN)
    if (wal.self_id != native.self_id or wal.action_id != native.action_id
            or wal.session_id != native.session_id
            or wal.native_probe_seq != native.probe_seq
            or wal.native_target_ref != f"entity:{native.runtime_target_entity_id}"
            or wal.native_actor_entity_id != native.runtime_actor_entity_id):
        reasons.append("native ATTACK WAL and identity witness do not describe same session")
        return result(AttackWorldJoinStatus.HOLD_UNKNOWN)
    sources.add(native.source_ref)
    if native.target_uuid == native.actor_uuid:
        reasons.append("native attacker equals target UUID")
        return result(AttackWorldJoinStatus.HOLD_UNKNOWN)

    # A no-ticket server hit can inform Self about this actor+target, but
    # it cannot establish which particular L0 Action caused the hit.
    if ticket is not None:
        if (ticket.world_id != world_id or ticket.branch_id != branch_id
                or ticket.action_id != wal.action_id
                or ticket.native_session_id != native.session_id
                or ticket.target_uuid != native.target_uuid
                or ticket.actor_uuid != native.actor_uuid):
            reasons.append("server ticket does not bind same World/Action/actor/target")
            return result(AttackWorldJoinStatus.HOLD_UNKNOWN)
        sources.add(ticket.server_ack_ref)

    possible = [
        ev for ev in damage_events
        if ev.world_id == world_id and ev.branch_id == branch_id
        and ev.victim_uuid == native.target_uuid
        and ev.attacker_uuid == native.actor_uuid
        and ev.damage_cause == "ENTITY_ATTACK"
        and (ticket is None or (
            ev.ticket_nonce == ticket.nonce and ev.tick >= ticket.registered_at_tick
        ))
    ]
    if len(possible) != 1:
        reasons.append("no unique independent server Health reduction matching actor/target")
        return result(AttackWorldJoinStatus.HOLD_UNKNOWN)
    damage = possible[0]
    sources.add(damage.server_source_ref)
    if damage.server_source_ref == native.source_ref:
        reasons.append("server and native source must be independently recorded")
        return result(AttackWorldJoinStatus.HOLD_UNKNOWN)
    if ticket is None:
        reasons.append("server hit matches actor/target but no pre-issued Action ticket")
        return result(AttackWorldJoinStatus.DEV_SERVER_DAMAGE_UNJOINED, damage)
    deaths = [
        ev for ev in death_events
        if ev.world_id == world_id and ev.branch_id == branch_id
        and ev.victim_uuid == damage.victim_uuid
        and ev.killer_uuid == damage.attacker_uuid
        and ev.tick >= damage.tick
        and ev.causing_damage_event_id == damage.event_id
    ]
    if len(deaths) > 1:
        reasons.append("multiple death events attributed to one server damage event")
        return result(AttackWorldJoinStatus.HOLD_UNKNOWN)
    if len(deaths) == 1:
        if damage.health_after > 0:
            reasons.append("death attributed to damage that did not reach zero Health")
            return result(AttackWorldJoinStatus.HOLD_UNKNOWN)
        death = deaths[0]
        sources.add(death.server_source_ref)
        reasons.append("DEV only: matching ticket/event chain; provenance not independently authenticated")
        return result(AttackWorldJoinStatus.DEV_ACTION_DEATH_CORRELATED, damage, death)
    reasons.append("DEV only: matching ticket/event; no causally linked death established")
    return result(AttackWorldJoinStatus.DEV_ACTION_DAMAGE_CORRELATED, damage)
