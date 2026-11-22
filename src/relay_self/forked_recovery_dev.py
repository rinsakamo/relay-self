"""#858 P0-C read-only DEV recovery of forked Minecraft World + Self A/B.

This is a *scoped historical-event cut*, NOT global tick equivalence,
atomic World/WAL restoration, native replay authorization, or a new owner.
The World cut and independently derived Self cut are DEV evidence claims.
Actual fresh WorldBody facts must be supplied after loading the new fork.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from relay_self.attack_world_join_dev import (
    AttackWalEvidence,
    AttackWorldJoinStatus,
    NativeIdentityWitness,
    ServerAttackTicket,
    ServerDamageEvent,
    ServerDeathEvent,
    join_attack_world_dev,
)
from relay_self.causal_recovery import (
    ActionClaim,
    BeliefRecord,
    ReceivedMessage,
    SelfCheckpoint,
    SentMessage,
    WalReceipt,
    WalState,
)
from relay_self.world_checkpoint_dev import (
    verify_restored_world,
    verify_world_checkpoint,
)


class ForkRecoveryDevError(ValueError):
    """Malformed or unsupported offline DEV World/Self evidence."""


class ForkRecoveryDevStatus(str, Enum):
    REJECT_WORLD_CUT = "REJECT_WORLD_CUT"
    HOLD_PHYSICAL_RECONCILIATION = "HOLD_PHYSICAL_RECONCILIATION"
    NEEDS_FRESH_WORLD_BODY = "NEEDS_FRESH_WORLD_BODY"
    PRESENT_REPROJECTED_DEV = "PRESENT_REPROJECTED_DEV"


def _name(value: object, label: str) -> None:
    if type(value) is not str or not value.strip():
        raise ForkRecoveryDevError(f"{label} must be nonempty text")


def _names(value: tuple[str, ...], label: str) -> None:
    if type(value) is not tuple or not all(type(v) is str and v for v in value):
        raise ForkRecoveryDevError(f"{label} requires a tuple of identities")
    if len(value) != len(set(value)):
        raise ForkRecoveryDevError(f"{label} has duplicate identities")


@dataclass(frozen=True, slots=True)
class SourceWorldCutWitness:
    """Explicit *scoped* external state + event membership, not a full WAL cut."""

    world_id: str
    source_branch_id: str
    checkpoint_id: str
    target_uuid: str
    target_alive_at_capture: bool | None
    included_effect_event_ids: tuple[str, ...]
    source_ref: str

    def __post_init__(self) -> None:
        for label in (
            "world_id", "source_branch_id", "checkpoint_id",
            "target_uuid", "source_ref",
        ):
            _name(getattr(self, label), label)
        if (self.target_alive_at_capture is not None
                and type(self.target_alive_at_capture) is not bool):
            raise ForkRecoveryDevError("target state is boolean or UNKNOWN")
        _names(self.included_effect_event_ids, "cut event membership")


@dataclass(frozen=True, slots=True)
class JoinedActionEffect:
    """A DEV-correlated *source-branch* event, never a fork-side event."""

    world_id: str
    source_branch_id: str
    event_id: str
    damage_event_id: str
    action_id: str
    actor_self_id: str
    native_session_id: str
    native_target_ref: str
    wal_journal_sha256: str
    target_uuid: str
    target_alive_after: bool | None
    join_status: AttackWorldJoinStatus
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for label in (
            "world_id", "source_branch_id", "event_id", "damage_event_id",
            "action_id", "actor_self_id", "native_session_id",
            "native_target_ref", "wal_journal_sha256", "target_uuid",
        ):
            _name(getattr(self, label), label)
        _names(self.source_refs, "effect source refs")
        if self.join_status not in (
            AttackWorldJoinStatus.DEV_ACTION_DAMAGE_CORRELATED,
            AttackWorldJoinStatus.DEV_ACTION_DEATH_CORRELATED,
        ):
            raise ForkRecoveryDevError("Action effect requires server ticket DEV join")
        if (self.target_alive_after is not None
                and type(self.target_alive_after) is not bool):
            raise ForkRecoveryDevError("effect target alive must be boolean/UNKNOWN")


def joined_action_effect_dev(
    wal: AttackWalEvidence, native: NativeIdentityWitness, *,
    ticket: ServerAttackTicket,
    damage: ServerDamageEvent,
    death: ServerDeathEvent | None = None,
) -> JoinedActionEffect:
    """Reevaluate original ticket/native/server evidence instead of trusting prose."""
    if not isinstance(wal, AttackWalEvidence) or not isinstance(
        native, NativeIdentityWitness
    ) or not isinstance(ticket, ServerAttackTicket) or not isinstance(
        damage, ServerDamageEvent
    ):
        raise ForkRecoveryDevError("typed independent ATTACK join evidence required")
    if death is not None and not isinstance(death, ServerDeathEvent):
        raise ForkRecoveryDevError("typed server death event required")
    joined = join_attack_world_dev(
        wal, native, world_id=ticket.world_id, branch_id=ticket.branch_id,
        ticket=ticket, damage_events=(damage,), death_events=(() if death is None else (death,)),
    )
    if joined.status not in (
        AttackWorldJoinStatus.DEV_ACTION_DAMAGE_CORRELATED,
        AttackWorldJoinStatus.DEV_ACTION_DEATH_CORRELATED,
    ):
        raise ForkRecoveryDevError("source Action has no ticket-linked World effect")
    if death is not None and joined.status is not AttackWorldJoinStatus.DEV_ACTION_DEATH_CORRELATED:
        raise ForkRecoveryDevError("death does not directly link to server damage")
    return JoinedActionEffect(
        world_id=ticket.world_id, source_branch_id=ticket.branch_id,
        event_id=death.event_id if death is not None else damage.event_id,
        damage_event_id=damage.event_id, action_id=wal.action_id,
        actor_self_id=wal.self_id, native_session_id=wal.session_id,
        native_target_ref=wal.native_target_ref,
        wal_journal_sha256=wal.journal_sha256,
        target_uuid=native.target_uuid,
        target_alive_after=False if death is not None else
        True if damage.health_after > 0 else None,
        join_status=joined.status, source_refs=joined.sources,
    )


@dataclass(frozen=True, slots=True)
class DerivedCognitiveCut:
    """Persisted *derived* DEV cognition, never a restored real Self owner."""

    checkpoint: SelfCheckpoint
    source_ref: str
    evidence_class: str  # SIMULATED or OBSERVATION_DERIVED

    def __post_init__(self) -> None:
        if not isinstance(self.checkpoint, SelfCheckpoint):
            raise ForkRecoveryDevError("typed existing SelfCheckpoint required")
        _name(self.source_ref, "cognitive source")
        if self.evidence_class not in {"SIMULATED", "OBSERVATION_DERIVED"}:
            raise ForkRecoveryDevError("derivation provenance required")


def write_derived_cognitive_cut_dev(path: Path, cut: DerivedCognitiveCut) -> None:
    """Write a NEW Self-specific derivative, never replace real cognition/memory."""
    if not isinstance(cut, DerivedCognitiveCut):
        raise ForkRecoveryDevError("typed cognitive cut required")
    path = Path(path)
    if path.exists() or path.is_symlink() or not path.parent.is_dir():
        raise ForkRecoveryDevError("new cognitive evidence path required")
    body = {
        "schema": 1, "evidence_class": cut.evidence_class,
        "source_ref": cut.source_ref, "checkpoint": asdict(cut.checkpoint),
    }
    data = (json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        # Do not delete incomplete evidence automatically.
        raise


def load_derived_cognitive_cut_dev(path: Path) -> DerivedCognitiveCut:
    """Parse only this evidence format; reject foreign/extra fields."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ForkRecoveryDevError("cognitive derivative file not available")
    try:
        data = json.loads(path.read_bytes())
        if type(data) is not dict or set(data) != {
            "schema", "evidence_class", "source_ref", "checkpoint",
        } or data["schema"] != 1:
            raise ValueError("unexpected cognitive evidence schema")
        raw = data["checkpoint"]
        if type(raw) is not dict or set(raw) != {
            "checkpoint_id", "self_id", "world_id", "branch_id",
            "tick", "claims", "beliefs", "sent", "received",
        }:
            raise ValueError("unexpected SelfCheckpoint schema")
        claim = tuple(ActionClaim(**v) for v in raw["claims"])
        belief = tuple(BeliefRecord(**v) for v in raw["beliefs"])
        sent = tuple(SentMessage(**v) for v in raw["sent"])
        received = tuple(ReceivedMessage(**v) for v in raw["received"])
        checkpoint = SelfCheckpoint(
            checkpoint_id=raw["checkpoint_id"], self_id=raw["self_id"],
            world_id=raw["world_id"], branch_id=raw["branch_id"],
            tick=raw["tick"], claims=claim, beliefs=belief,
            sent=sent, received=received,
        )
        return DerivedCognitiveCut(checkpoint, data["source_ref"], data["evidence_class"])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ForkRecoveryDevError("malformed cognitive evidence file") from exc


@dataclass(frozen=True, slots=True)
class FreshForkObservation:
    """First fresh WorldBody source in NEW branch; absence may be UNKNOWN."""

    world_id: str
    new_branch_id: str
    native_session_id: str
    target_uuid: str
    observed_target_alive: bool | None
    source_ref: str
    runtime_target_entity_id: int | None = None

    def __post_init__(self) -> None:
        for label in (
            "world_id", "new_branch_id", "native_session_id", "target_uuid",
            "source_ref",
        ):
            _name(getattr(self, label), label)
        if (self.observed_target_alive is not None
                and type(self.observed_target_alive) is not bool):
            raise ForkRecoveryDevError("fresh physical state must be boolean/UNKNOWN")
        if (self.runtime_target_entity_id is not None
                and (type(self.runtime_target_entity_id) is not int
                     or self.runtime_target_entity_id < 0)):
            raise ForkRecoveryDevError("new session target ID invalid")
        if self.observed_target_alive is True and self.runtime_target_entity_id is None:
            raise ForkRecoveryDevError("live target requires new session native ID")


@dataclass(frozen=True, slots=True)
class ForkRecoveryDevDecision:
    status: ForkRecoveryDevStatus
    source_checkpoint_id: str
    world_id: str
    source_branch_id: str
    new_branch_id: str
    target_uuid: str
    source_target_alive: bool | None
    historical_native_sessions: tuple[str, ...]
    included_action_ids: tuple[str, ...]
    remembered_postcut_action_ids: tuple[str, ...]
    retained_beliefs: tuple[str, ...]
    blockers: tuple[str, ...]
    next_steps: tuple[str, ...]
    present_target_alive: bool | None = None
    present_source_ref: str | None = None
    physical_action_issue_authorized: bool = False
    self_owner_restored: bool = False


def prepare_forked_recovery_dev(
    archive: Path, restored_world: Path, *,
    cut: SourceWorldCutWitness,
    selves: tuple[DerivedCognitiveCut, ...],
    wal: tuple[WalReceipt, ...],
    effects: tuple[JoinedActionEffect, ...],
) -> ForkRecoveryDevDecision:
    """Prelaunch read-only file verification + historical causal cut.

    The declared World tick is not compared to Paper event ticks or the
    synthetic C98/C105 labels. Event membership comes from the explicit
    DEV source-cut witness, not numeric clock coincidence.
    """
    if not isinstance(cut, SourceWorldCutWitness):
        raise ForkRecoveryDevError("typed World cut witness required")
    if (type(selves) is not tuple or not selves or not all(
            isinstance(x, DerivedCognitiveCut) for x in selves)
            or type(wal) is not tuple or not all(isinstance(x, WalReceipt) for x in wal)
            or type(effects) is not tuple or not all(
                isinstance(x, JoinedActionEffect) for x in effects)):
        raise ForkRecoveryDevError("typed independent Self/WAL/effect tuples required")
    manifest = verify_world_checkpoint(archive)
    receipt = verify_restored_world(archive, restored_world)
    source_id = manifest["checkpoint_id"]
    source_branch = manifest["branch_id"]
    fork = receipt["new_branch_id"]
    world_id = manifest["world_id"]
    reject: list[str] = []
    hold: list[str] = []
    if (cut.world_id != world_id or cut.source_branch_id != source_branch
            or cut.checkpoint_id != source_id):
        reject.append("World cut witness differs from verified source archive")
    if cut.target_alive_at_capture is None:
        hold.append("physical World source-cut target remains UNKNOWN")
    known = {c.checkpoint.self_id: c.checkpoint for c in selves}
    if len(known) != len(selves):
        reject.append("duplicate Self cognitive snapshots")
    for self_cut in selves:
        cp = self_cut.checkpoint
        if cp.world_id != world_id or cp.branch_id != source_branch:
            reject.append(f"Self {cp.self_id} belongs to foreign source branch")
    event_ids = {e.event_id for e in effects}
    if len(event_ids) != len(effects):
        reject.append("duplicate independently joined World effect")
    action_ids = {e.action_id for e in effects}
    if len(action_ids) != len(effects):
        reject.append("one Action appears as multiple effects")
    if set(cut.included_effect_event_ids) - event_ids:
        hold.append("World cut claims effect ID without joined server event")
    for ev in effects:
        if (ev.world_id != world_id or ev.source_branch_id != source_branch
                or ev.target_uuid != cut.target_uuid):
            reject.append(f"World effect {ev.event_id} belongs to foreign source")
        if (ev.event_id in cut.included_effect_event_ids
                and ev.target_alive_after is not None
                and ev.target_alive_after != cut.target_alive_at_capture):
            reject.append("World capture target disagrees with included effect")
        if (ev.event_id not in cut.included_effect_event_ids
                and ev.target_alive_after is False
                and cut.target_alive_at_capture is False):
            hold.append("source cut excludes lethal event while target already dead")
    wal_by_action = {row.action_id: row for row in wal}
    if len(wal_by_action) != len(wal):
        reject.append("duplicate physical Action across per-Self WALs")
    effect_by_action = {e.action_id: e for e in effects}
    remembered: list[str] = []
    for self_cut in selves:
        cp = self_cut.checkpoint
        for claim in cp.claims:
            row = wal_by_action.get(claim.action_id)
            effect = effect_by_action.get(claim.action_id)
            if row is None or row.self_id != cp.self_id:
                hold.append(f"Action {claim.action_id} has no matching Self-owned WAL")
            elif row.status is not WalState.NATIVE_ATTACK_HURT_OBSERVED:
                hold.append(f"Action {claim.action_id} has no terminal native ATTACK hurt")
            elif row.native_target_ref != claim.native_target_ref:
                hold.append(f"Action {claim.action_id} uses stale native target")
            if (effect is None or effect.actor_self_id != cp.self_id
                    or effect.target_uuid != claim.expected_target_uuid
                    or effect.native_target_ref != claim.native_target_ref
                    or row is not None and (
                        effect.native_session_id != row.native_session_id
                        or effect.wal_journal_sha256 != row.journal_sha256
                    )):
                hold.append(f"Action {claim.action_id} lacks correlated source-branch effect")
            elif effect.event_id not in cut.included_effect_event_ids:
                remembered.append(claim.action_id)
        for message in cp.received:
            sender = known.get(message.sender_self_id)
            if sender is None or not any(
                m.message_id == message.message_id and m.tick <= message.tick
                for m in sender.sent
            ):
                hold.append(f"receive {message.message_id} not present in sender cut")
    for row in wal:
        if row.self_id not in known:
            hold.append(f"WAL {row.action_id} references unknown Self")
        if row.status is WalState.PREPARED_UNRESOLVED:
            hold.append(f"WAL {row.action_id} unresolved; never reissue")
        if row.action_id not in effect_by_action:
            hold.append(f"WAL {row.action_id} lacks independent source event")
    for effect in effects:
        actor = known.get(effect.actor_self_id)
        if actor is None or not any(x.action_id == effect.action_id for x in actor.claims):
            hold.append(f"effect {effect.event_id} not tied to owner cognitive claim")
    beliefs = tuple(sorted(
        f"{cp.self_id}:{b.target_uuid}:{b.observed_tick}:"
        f"{'ALIVE' if b.perceived_alive else 'DEAD'}"
        for cp in known.values() for b in cp.beliefs
    ))
    if reject:
        status = ForkRecoveryDevStatus.REJECT_WORLD_CUT
        steps = ("SELECT_DIFFERENT_SOURCE_CUT", "NO_PHYSICAL_ACTION_REISSUE")
    elif hold:
        status = ForkRecoveryDevStatus.HOLD_PHYSICAL_RECONCILIATION
        steps = ("RECONCILE_SOURCE_WAL_AND_CUT", "NO_PHYSICAL_ACTION_REISSUE")
    else:
        status = ForkRecoveryDevStatus.NEEDS_FRESH_WORLD_BODY
        steps = (
            "LOAD_FORKED_WORLD_WITH_NEW_HISTORY_ID",
            "OBTAIN_NEW_NATIVE_SESSION_AND_WORLD_BODY_OBSERVATION",
            "PROJECT_PRESENT_FROM_FRESH_OBSERVATION_NOT_MEMORY",
            "NO_PHYSICAL_ACTION_REISSUE",
        )
    included = tuple(sorted(
        e.action_id for e in effects
        if e.event_id in cut.included_effect_event_ids
    ))
    return ForkRecoveryDevDecision(
        status=status, source_checkpoint_id=source_id,
        world_id=world_id, source_branch_id=source_branch,
        new_branch_id=fork, target_uuid=cut.target_uuid,
        source_target_alive=cut.target_alive_at_capture,
        historical_native_sessions=tuple(sorted(set(row.native_session_id for row in wal))),
        included_action_ids=included,
        remembered_postcut_action_ids=tuple(sorted(set(remembered))),
        retained_beliefs=beliefs, blockers=tuple(sorted(set(reject + hold))),
        next_steps=steps,
    )


def reproject_present_from_fresh_world_dev(
    prepared: ForkRecoveryDevDecision,
    fresh: FreshForkObservation,
) -> ForkRecoveryDevDecision:
    """Pure post-launch re-projection; never unfreezes an old action/target."""
    if not isinstance(prepared, ForkRecoveryDevDecision) or not isinstance(
        fresh, FreshForkObservation
    ):
        raise ForkRecoveryDevError("typed fork plan and fresh WorldBody required")
    if prepared.status is not ForkRecoveryDevStatus.NEEDS_FRESH_WORLD_BODY:
        return prepared  # never override prior hold/reject through an observation
    if (fresh.world_id != prepared.world_id
            or fresh.new_branch_id != prepared.new_branch_id
            or fresh.target_uuid != prepared.target_uuid
            or fresh.native_session_id in prepared.historical_native_sessions):
        return _reproject_hold(prepared, "fresh WorldBody branch/session/UUID mismatch")
    if fresh.observed_target_alive is None:
        return prepared  # no new physical truth from absence/unknown coverage
    if (prepared.source_target_alive is not None
            and fresh.observed_target_alive != prepared.source_target_alive):
        return _reproject_hold(prepared, "restored target differs from witnessed cut")
    return ForkRecoveryDevDecision(
        status=ForkRecoveryDevStatus.PRESENT_REPROJECTED_DEV,
        source_checkpoint_id=prepared.source_checkpoint_id,
        world_id=prepared.world_id,
        source_branch_id=prepared.source_branch_id,
        new_branch_id=prepared.new_branch_id,
        target_uuid=prepared.target_uuid,
        source_target_alive=prepared.source_target_alive,
        historical_native_sessions=prepared.historical_native_sessions,
        included_action_ids=prepared.included_action_ids,
        remembered_postcut_action_ids=prepared.remembered_postcut_action_ids,
        retained_beliefs=prepared.retained_beliefs,
        blockers=(),
        next_steps=(
            "MAKE_FRESH_SCHEMA_PROJECTION_FROM_WORLD_BODY",
            "RECHECK_GOALS_AND_INTENTS_WITH_EXISTING_OWNERS",
            "NO_PHYSICAL_ACTION_REISSUE",
        ),
        present_target_alive=fresh.observed_target_alive,
        present_source_ref=fresh.source_ref,
    )


def _reproject_hold(prepared: ForkRecoveryDevDecision, blocker: str) -> ForkRecoveryDevDecision:
    return ForkRecoveryDevDecision(
        status=ForkRecoveryDevStatus.HOLD_PHYSICAL_RECONCILIATION,
        source_checkpoint_id=prepared.source_checkpoint_id,
        world_id=prepared.world_id,
        source_branch_id=prepared.source_branch_id,
        new_branch_id=prepared.new_branch_id,
        target_uuid=prepared.target_uuid,
        source_target_alive=prepared.source_target_alive,
        historical_native_sessions=prepared.historical_native_sessions,
        included_action_ids=prepared.included_action_ids,
        remembered_postcut_action_ids=prepared.remembered_postcut_action_ids,
        retained_beliefs=prepared.retained_beliefs,
        blockers=(blocker,),
        next_steps=("REOBSERVE_FORK_IDENTITY_AND_TARGET", "NO_PHYSICAL_ACTION_REISSUE"),
    )
