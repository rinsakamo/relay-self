"""D14 Defense-F1: source-bound *candidate* for original-S49 defense.

A native Health decrease while one real zombie is in range is a
correlation, NOT proof that the zombie caused the damage. This pure
function never issues an Action, grants authority, or relaxes the
original physical STOP and persistent PREPARE fences.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from adapters.mineflayer.python_protocol import MineflayerObservation

MAX_DAMAGE_WITNESS_SEQ_LAG = 64
MAX_PREVIOUS_ZOMBIE_DISTANCE = 4.0
MAX_CURRENT_ATTACK_DISTANCE = 2.8
MAX_PAIR_ZOMBIE_AXIS_DELTA = 2.0
MAX_PAIR_SELF_AXIS_DELTA = 0.9
# Explicit conservative passive-nonhostile allowlist. Unknown and hostile
# entities remain a refusal; this is NOT general multi-target attack.
F2_PASSIVE_BYSTANDER_NAMES = frozenset({
    "sheep", "cow", "pig", "chicken", "rabbit",
})
F2_SOURCE = "NATIVE_HEALTH_DROP_SINGLE_ZOMBIE_KNOWN_BYSTANDERS_CAUSE_UNATTESTED"
F1_SOURCE = "NATIVE_SELF_HEALTH_DROP_NEAR_SAME_ZOMBIE_CAUSE_UNATTESTED"


@dataclass(frozen=True, slots=True)
class NativeDamageDefenseCandidate:
    target_entity_id: int
    witness: MineflayerObservation
    admitted_probe_seq: int
    health_loss: float
    source: str = F1_SOURCE


def evaluate_native_damage_defense(
    previous: MineflayerObservation,
    current: MineflayerObservation,
    witness: MineflayerObservation | None,
    *, allow_known_bystanders: bool = False,
) -> tuple[NativeDamageDefenseCandidate | None, str]:
    """Return a bounded, typed hit-response candidate and refusal reason.

    Fresh previous/current probes MUST show exactly one same-ID zombie.
    A recent native probe must independently show Self had more Health.
    A less-stationary target is permitted here than in R9, but the
    sole original S49 issuer still applies all other authorizations.
    """
    if type(allow_known_bystanders) is not bool:
        return None, "UNTYPED_BYSTANDER_SCOPE"
    if not all(isinstance(x, MineflayerObservation) for x in (previous, current)):
        return None, "UNTYPED_CURRENT_NATIVE_SOURCE"
    if witness is None or not isinstance(witness, MineflayerObservation):
        return None, "NO_TYPED_HEALTH_LOSS_WITNESS"
    if (
        any(x.kind != "probe" or not x.request_id or
            x.provenance.source != "mineflayer" for x in (witness, previous, current))
        or len({witness.session_id, previous.session_id, current.session_id}) != 1
        or not witness.seq <= previous.seq < current.seq <= previous.seq + 32
        or current.seq - witness.seq > MAX_DAMAGE_WITNESS_SEQ_LAG
        or witness.request_id == current.request_id
        or previous.request_id == current.request_id
    ):
        return None, "STALE_OR_FOREIGN_HEALTH_WITNESS"
    targets = []
    for probe in (previous, current):
        view = probe.snapshot
        cover = view.nearby_entities_coverage
        if (
            view.health <= 0 or view.oxygen_level is None
            or view.oxygen_level <= 0
            or cover.truncated
            or cover.candidate_count != len(view.nearby_entities)
            or not 1 <= cover.candidate_count <= cover.max_entities
        ):
            return None, "BODY_OXYGEN_OR_TARGET_COVERAGE_UNSAFE"
        if not allow_known_bystanders and cover.candidate_count != 1:
            return None, "BODY_OXYGEN_OR_TARGET_COVERAGE_UNSAFE"
        zombies = [e for e in view.nearby_entities if e.name == "zombie"]
        if len(zombies) != 1:
            return None, "NOT_EXACTLY_ONE_VISIBLE_ZOMBIE"
        if allow_known_bystanders and any(
            (e.name not in F2_PASSIVE_BYSTANDER_NAMES
             or e.entity_type != "mob"
             or e.entity_id == zombies[0].entity_id)
            for e in view.nearby_entities if e is not zombies[0]
        ):
            return None, "UNKNOWN_OR_HOSTILE_BYSTANDER_UNSAFE"
        targets.append(zombies[0])
    if not witness.snapshot.health > current.snapshot.health:
        return None, "NO_RECENT_NATIVE_SELF_HEALTH_LOSS"
    loss = witness.snapshot.health - current.snapshot.health
    if not isfinite(loss) or loss > 20:
        return None, "INVALID_NATIVE_HEALTH_DELTA"
    before, now = targets
    if (
        before.name != "zombie" or now.name != "zombie"
        or before.entity_id != now.entity_id
        or not 0.1 <= before.distance <= MAX_PREVIOUS_ZOMBIE_DISTANCE
        or not 0.1 <= now.distance <= MAX_CURRENT_ATTACK_DISTANCE
    ):
        return None, "NO_SAME_CLOSE_NATIVE_ZOMBIE"
    if any(
        abs(getattr(before.position, axis) -
            getattr(now.position, axis)) > MAX_PAIR_ZOMBIE_AXIS_DELTA
        or abs(getattr(previous.snapshot.position, axis) -
               getattr(current.snapshot.position, axis)) > MAX_PAIR_SELF_AXIS_DELTA
        for axis in ("x", "y", "z")
    ):
        return None, "EXCESSIVE_TARGET_OR_BODY_DISPLACEMENT"
    return NativeDamageDefenseCandidate(
        target_entity_id=now.entity_id, witness=witness,
        admitted_probe_seq=current.seq, health_loss=loss,
        source=F2_SOURCE if allow_known_bystanders else F1_SOURCE,
    ), (
        "F2_SINGLE_ZOMBIE_KNOWN_BYSTANDERS_REACTIVE_CANDIDATE"
        if allow_known_bystanders else "REACTIVE_NATIVE_HEALTH_LOSS_CANDIDATE"
    )


def require_native_damage_defense(
    previous: MineflayerObservation,
    current: MineflayerObservation,
    target: int,
    candidate: NativeDamageDefenseCandidate,
) -> None:
    """Revalidate evidence inside the original issuer, not just the L0 caller."""
    from adapters.mineflayer.normal_action import NormalActionRejected

    if not isinstance(candidate, NativeDamageDefenseCandidate):
        raise NormalActionRejected("untyped reactive defense source")
    if candidate.source not in (F1_SOURCE, F2_SOURCE):
        raise NormalActionRejected("unrecognized native damage defense source")
    computed, reason = evaluate_native_damage_defense(
        previous, current, candidate.witness,
        allow_known_bystanders=(candidate.source == F2_SOURCE),
    )
    if (
        computed is None or computed != candidate
        or candidate.target_entity_id != target
        or candidate.admitted_probe_seq != current.seq
    ):
        raise NormalActionRejected(f"reactive native defense source refused: {reason}")
