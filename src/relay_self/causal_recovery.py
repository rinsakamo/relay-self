"""#851 Offline-only causal cut reconciliation for World + multiple Self snapshots.

No Minecraft save/restore, grant, native issue, semantic owner mutation, or
automatic checkpoint selection happens here. The caller must independently
authenticate World manifests, source joins and actual journal files. Type-safe
source references are NOT signatures and a candidate is NEVER issue permission.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.physical_action_journal import PhysicalActionJournal


class RecoveryContractError(ValueError):
    """Malformed, ambiguous or duplicate recovery input."""


class RecoveryVerdict(str, Enum):
    REJECT_CHECKPOINT = "REJECT_CHECKPOINT"
    HOLD_PHYSICAL_RECONCILIATION = "HOLD_PHYSICAL_RECONCILIATION"
    CANDIDATE_REOBSERVE = "CANDIDATE_REOBSERVE"


class WalState(str, Enum):
    PREPARED_UNRESOLVED = "PREPARED_UNRESOLVED"
    NATIVE_EAT_OUTCOME = "NATIVE_EAT_OUTCOME"
    NATIVE_ATTACK_HURT_OBSERVED = "NATIVE_ATTACK_HURT_OBSERVED"


def _text(name: str, value: object) -> None:
    if type(value) is not str or not value.strip():
        raise RecoveryContractError(f"{name} must be nonblank text")


def _tick(name: str, value: object) -> None:
    if type(value) is not int or value < 0:
        raise RecoveryContractError(f"{name} must be a nonnegative tick")


def _typed_tuple(name: str, value: object, item_type: type) -> None:
    if type(value) is not tuple or not all(type(x) is item_type for x in value):
        raise RecoveryContractError(f"{name} must be a tuple of {item_type.__name__}")


@dataclass(frozen=True, slots=True)
class WorldEntityState:
    entity_uuid: str
    alive: bool

    def __post_init__(self) -> None:
        _text("entity_uuid", self.entity_uuid)
        if type(self.alive) is not bool:
            raise RecoveryContractError("entity alive must be bool")


@dataclass(frozen=True, slots=True)
class WorldCheckpoint:
    checkpoint_id: str
    world_id: str
    branch_id: str
    tick: int
    atomic_capture_attested: bool
    event_coverage_through_tick: int | None
    entity_states: tuple[WorldEntityState, ...] = ()

    def __post_init__(self) -> None:
        for name in ("checkpoint_id", "world_id", "branch_id"):
            _text(name, getattr(self, name))
        _tick("world tick", self.tick)
        if type(self.atomic_capture_attested) is not bool:
            raise RecoveryContractError("atomic capture needs explicit attestation status")
        if self.event_coverage_through_tick is not None:
            _tick("event coverage tick", self.event_coverage_through_tick)
        _typed_tuple("entity_states", self.entity_states, WorldEntityState)
        ids = [e.entity_uuid for e in self.entity_states]
        if len(set(ids)) != len(ids):
            raise RecoveryContractError("duplicate World checkpoint entity UUID")


@dataclass(frozen=True, slots=True)
class WorldEvent:
    """External effect fact; not a self-asserted physical consequence.

    Native and server refs are distinct attestation *inputs*. The evaluator
    only checks joins, never authenticates their contents or Minecraft ticks.
    """

    event_id: str
    world_id: str
    branch_id: str
    tick: int
    actor_self_id: str | None
    action_id: str | None
    native_session_id: str | None
    target_uuid: str | None
    entity_alive_after: bool | None
    native_source_ref: str | None
    server_source_ref: str
    native_target_ref: str | None = None

    def __post_init__(self) -> None:
        for name in ("event_id", "world_id", "branch_id", "server_source_ref"):
            _text(name, getattr(self, name))
        _tick("World event tick", self.tick)
        if self.action_id is not None:
            for name in ("actor_self_id", "native_session_id", "native_source_ref"):
                _text(name, getattr(self, name))
            _text("action_id", self.action_id)
            _text("World-event native Target", self.native_target_ref)
        elif any(getattr(self, name) is not None for name in (
            "actor_self_id", "native_session_id", "native_source_ref",
            "native_target_ref",
        )):
            raise RecoveryContractError("unattributed World event cannot claim an actor")
        if self.target_uuid is not None:
            _text("target_uuid", self.target_uuid)
        if self.entity_alive_after is not None and (
            type(self.entity_alive_after) is not bool or self.target_uuid is None
        ):
            raise RecoveryContractError("entity state change requires UUID and bool")


@dataclass(frozen=True, slots=True)
class ActionClaim:
    action_id: str
    native_target_ref: str
    expected_target_uuid: str | None
    claimed_tick: int

    def __post_init__(self) -> None:
        _text("action ID", self.action_id)
        _text("native target ref", self.native_target_ref)
        if self.expected_target_uuid is not None:
            _text("target UUID", self.expected_target_uuid)
        _tick("claimed action tick", self.claimed_tick)


@dataclass(frozen=True, slots=True)
class BeliefRecord:
    target_uuid: str
    observed_tick: int
    perceived_alive: bool
    evidence_ref: str

    def __post_init__(self) -> None:
        _text("belief target UUID", self.target_uuid)
        _tick("belief observed tick", self.observed_tick)
        _text("belief provenance", self.evidence_ref)
        if type(self.perceived_alive) is not bool:
            raise RecoveryContractError("belief must retain typed observation")


@dataclass(frozen=True, slots=True)
class SentMessage:
    message_id: str
    tick: int

    def __post_init__(self) -> None:
        _text("message ID", self.message_id)
        _tick("message send tick", self.tick)


@dataclass(frozen=True, slots=True)
class ReceivedMessage:
    sender_self_id: str
    message_id: str
    tick: int

    def __post_init__(self) -> None:
        _text("sender Self", self.sender_self_id)
        _text("message ID", self.message_id)
        _tick("receive tick", self.tick)


@dataclass(frozen=True, slots=True)
class SelfCheckpoint:
    checkpoint_id: str
    self_id: str
    world_id: str
    branch_id: str
    tick: int
    claims: tuple[ActionClaim, ...] = ()
    beliefs: tuple[BeliefRecord, ...] = ()
    sent: tuple[SentMessage, ...] = ()
    received: tuple[ReceivedMessage, ...] = ()

    def __post_init__(self) -> None:
        for name in ("checkpoint_id", "self_id", "world_id", "branch_id"):
            _text(name, getattr(self, name))
        _tick("Self checkpoint tick", self.tick)
        for name, kind in (
            ("claims", ActionClaim), ("beliefs", BeliefRecord),
            ("sent", SentMessage), ("received", ReceivedMessage),
        ):
            _typed_tuple(name, getattr(self, name), kind)
        if len({a.action_id for a in self.claims}) != len(self.claims):
            raise RecoveryContractError("repeated claimed Action ID")
        if len({m.message_id for m in self.sent}) != len(self.sent):
            raise RecoveryContractError("repeated sent message ID")
        for item in (*self.claims, *self.beliefs, *self.sent, *self.received):
            event_tick = (item.claimed_tick if isinstance(item, ActionClaim)
                          else item.observed_tick if isinstance(item, BeliefRecord)
                          else item.tick)
            if event_tick > self.tick:
                raise RecoveryContractError("Self checkpoint contains future local event")


@dataclass(frozen=True, slots=True)
class WalReceipt:
    self_id: str
    action_id: str
    native_session_id: str
    native_target_ref: str
    status: WalState
    journal_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "self_id", "action_id", "native_session_id",
            "native_target_ref", "journal_sha256",
        ):
            _text(name, getattr(self, name))
        if not isinstance(self.status, WalState):
            raise RecoveryContractError("unrecognized physical WAL status")


@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    verdict: RecoveryVerdict
    checkpoint_id: str
    physical_blockers: tuple[str, ...]
    belief_conflicts: tuple[str, ...]
    next_steps: tuple[str, ...]
    action_issue_authorized: bool = False


def project_physical_journal(
    journal: PhysicalActionJournal, *, self_id: str
) -> tuple[WalReceipt, ...]:
    """Read-only projection from a previously restored Self-owned v1 WAL.

    The caller must use PhysicalActionJournal.restore against the real file;
    this projection never clears an unresolved Action or revalidates a backup.
    """
    if not isinstance(journal, PhysicalActionJournal):
        raise RecoveryContractError("previously restored physical journal required")
    _text("Self identity", self_id)
    if journal._body["self_id"] != self_id:
        raise RecoveryContractError("foreign Self physical WAL")
    return tuple(
        WalReceipt(
            self_id=self_id, action_id=row["action_id"],
            native_session_id=row["session_id"],
            native_target_ref=row["target_ref"],
            status=WalState(row["status"]), journal_sha256=journal.digest,
        )
        for row in journal.records
    )


def assess_reconstruction(
    world: WorldCheckpoint,
    selves: tuple[SelfCheckpoint, ...],
    wal: tuple[WalReceipt, ...],
    events: tuple[WorldEvent, ...],
) -> RecoveryDecision:
    """Build a *candidate* causal cut; no writes, IO, repair, replay or grant."""
    if not isinstance(world, WorldCheckpoint):
        raise RecoveryContractError("typed World checkpoint required")
    _typed_tuple("selves", selves, SelfCheckpoint)
    _typed_tuple("WAL receipts", wal, WalReceipt)
    _typed_tuple("World events", events, WorldEvent)
    if not selves or len({x.self_id for x in selves}) != len(selves):
        raise RecoveryContractError("one checkpoint per distinct Self required")
    if len({x.action_id for x in wal}) != len(wal):
        raise RecoveryContractError("physical Action identity reused across Self WALs")
    if len({x.event_id for x in events}) != len(events):
        raise RecoveryContractError("duplicate World event identity")

    reject: list[str] = []
    hold: list[str] = []
    epistemic: list[str] = []
    known = {s.self_id: s for s in selves}
    wal_by_id = {row.action_id: row for row in wal}
    event_by_action: dict[str, WorldEvent] = {}
    for e in events:
        if e.world_id != world.world_id or e.branch_id != world.branch_id:
            reject.append(f"event {e.event_id} belongs to another World branch")
        if e.action_id is not None:
            if e.action_id in event_by_action:
                reject.append(f"Action {e.action_id} has multiple alleged World effects")
            event_by_action[e.action_id] = e
        if e.tick > world.tick:
            hold.append(f"World event {e.event_id} lies after restored checkpoint")

    if not world.atomic_capture_attested:
        reject.append("World checkpoint capture is not attested consistent")
    if (world.event_coverage_through_tick is None
            or world.event_coverage_through_tick < world.tick):
        hold.append("independent World effect coverage is incomplete at checkpoint tick")
    for s in selves:
        if s.world_id != world.world_id or s.branch_id != world.branch_id:
            reject.append(f"Self {s.self_id} belongs to another World branch")
        if s.tick > world.tick:
            hold.append(f"Self {s.self_id} carries cognition newer than restored World")
        for claim in s.claims:
            row = wal_by_id.get(claim.action_id)
            if row is None or row.self_id != s.self_id:
                hold.append(f"Self {s.self_id} claimed Action {claim.action_id} lacks its WAL")
            elif row.native_target_ref != claim.native_target_ref:
                hold.append(f"Action {claim.action_id} has stale native Target")
            if (claim.native_target_ref.startswith("entity:")
                    and claim.expected_target_uuid is None):
                hold.append(f"Action {claim.action_id} lacks native Entity ID to UUID join")
            effect = event_by_action.get(claim.action_id)
            if effect is None:
                hold.append(f"Action {claim.action_id} lacks independent World effect join")
            elif (effect.actor_self_id != s.self_id
                  or effect.target_uuid != claim.expected_target_uuid
                  or effect.tick > world.tick):
                hold.append(f"Action {claim.action_id} World actor/UUID/cut mismatch")
        for msg in s.received:
            sender = known.get(msg.sender_self_id)
            if sender is None or not any(
                sent.message_id == msg.message_id and sent.tick <= msg.tick
                for sent in sender.sent
            ):
                hold.append(f"receive {msg.message_id} absent from sender causal cut")

    for row in wal:
        if row.self_id not in known:
            hold.append(f"WAL Action {row.action_id} refers to absent Self")
        if row.status is WalState.PREPARED_UNRESOLVED:
            hold.append(f"WAL Action {row.action_id} is PREPARED_UNRESOLVED")
        effect = event_by_action.get(row.action_id)
        if effect is None:
            hold.append(f"WAL Action {row.action_id} has no independent World effect")
        elif (effect.actor_self_id != row.self_id
              or effect.native_session_id != row.native_session_id
              or effect.native_target_ref != row.native_target_ref
              or (row.native_target_ref.startswith("entity:")
                  and not effect.target_uuid)
              or effect.tick > world.tick
              or not effect.native_source_ref or not effect.server_source_ref):
            hold.append(f"WAL Action {row.action_id} lacks matched actor/session/cut/source")

    for effect in events:
        if effect.action_id and effect.actor_self_id in known:
            if effect.action_id not in wal_by_id:
                hold.append(f"World Action {effect.action_id} has no Self-owned WAL")

    # Compare cognition to independent *historical* World state only where
    # a same-entity, same-tick fact exists. A false belief is not a torn World.
    history: dict[tuple[str, int], bool] = {}
    latest: dict[str, tuple[int, bool]] = {}
    for effect in sorted(events, key=lambda e: e.tick):
        if effect.tick <= world.tick and effect.entity_alive_after is not None:
            assert effect.target_uuid is not None
            key = (effect.target_uuid, effect.tick)
            if key in history and history[key] != effect.entity_alive_after:
                reject.append(f"contradictory World events for UUID {effect.target_uuid}")
            history[key] = effect.entity_alive_after
            latest[effect.target_uuid] = (effect.tick, effect.entity_alive_after)
    for state in world.entity_states:
        if state.entity_uuid in latest and latest[state.entity_uuid][1] != state.alive:
            reject.append(f"World final state disagrees with last traced event: {state.entity_uuid}")
    for s in selves:
        for b in s.beliefs:
            observed = history.get((b.target_uuid, b.observed_tick))
            if observed is not None and observed != b.perceived_alive:
                epistemic.append(
                    f"Self {s.self_id} belief for {b.target_uuid} at tick "
                    f"{b.observed_tick} needs epistemic review"
                )

    # Reject only inconsistent physical checkpoint/branch. Lack of a join
    # is HOLD, not a false causal proof. An epistemic conflict is a warning.
    if reject:
        status = RecoveryVerdict.REJECT_CHECKPOINT
        steps = ("SELECT_OTHER_WORLD_CHECKPOINT", "KEEP_PHYSICAL_ISSUE_DISABLED")
    elif hold:
        status = RecoveryVerdict.HOLD_PHYSICAL_RECONCILIATION
        steps = ("RECONCILE_WORLD_WAL_AND_MESSAGE_CUT", "KEEP_PHYSICAL_ISSUE_DISABLED")
    else:
        status = RecoveryVerdict.CANDIDATE_REOBSERVE
        steps = (
            "REIDENTIFY_WORLD_AND_TARGETS",
            "FRESH_WORLD_BODY_SCHEMA_OBSERVATION",
            "REPROJECT_PRESENT_AND_RECHECK_INTENTS",
            "INDEPENDENT_PHYSICAL_OWNER_FENCING_REQUIRED",
        )
    return RecoveryDecision(
        verdict=status, checkpoint_id=world.checkpoint_id,
        physical_blockers=tuple(sorted(set(reject + hold))),
        belief_conflicts=tuple(sorted(set(epistemic))),
        next_steps=steps,
        action_issue_authorized=False,
    )
