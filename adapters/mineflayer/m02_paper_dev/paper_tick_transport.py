"""#150 DEV: match Paper callback rows with delivery on the same Mineflayer stream.

Transport equality is NOT Paper server attestation, Self-side L0 execution,
true WAIT, or an S49 Action OUTCOME. No TPS/motor operations are exposed.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.m02_paper_dev.paper_tick_probe import (
    PaperTickProbeRejected,
    read_passive_paper_ticks,
)
from adapters.mineflayer.python_protocol import MineflayerPaperL0Shadow, MineflayerPaperTickSample


@dataclass(frozen=True, slots=True)
class PaperTickTransportMatch:
    session_id: str
    server_ticks: tuple[int, ...]
    paper_wire_delivery_matched: bool = True
    l0_checked_ticks: tuple[int, ...] = ()
    action_bound: bool = False
    native_source_authenticated: bool = False
    tps_change_admitted: bool = False


def join_paper_tick_transport(
    paper_log: str,
    messages: tuple[MineflayerPaperTickSample, ...],
    *,
    expected_world: str,
    expected_player: str,
    expected_session: str,
) -> PaperTickTransportMatch:
    """Require every logger tick to match a genuine typed bridge message.

    Genuine typed refers to bridge protocol validation, *not* cryptographic
    origin; a synthetic valid message does not become native testimony.
    """
    if not isinstance(expected_session, str) or not expected_session.strip():
        raise PaperTickProbeRejected("explicit Mineflayer session required")
    trace = read_passive_paper_ticks(
        paper_log, expected_world=expected_world,
        expected_player=expected_player,
    )
    if (type(messages) is not tuple
            or len(messages) != len(trace.samples)
            or not all(type(m) is MineflayerPaperTickSample for m in messages)):
        raise PaperTickProbeRejected("every Paper tick needs one typed wire message")

    last_seq = -1
    last_recv = -1
    for paper, wire in zip(trace.samples, messages):
        if (wire.session_id != expected_session
                or wire.seq <= last_seq
                or wire.index != paper.index
                or int(wire.server_tick) != paper.server_tick
                or int(wire.world_full_time) != paper.world_full_time
                or int(wire.wall_nanos) != paper.wall_nanos
                or wire.world != paper.world
                or wire.player != paper.player
                or int(wire.bridge_recv_monotonic_ns) <= last_recv):
            raise PaperTickProbeRejected("Paper log / bridge receiver mismatch")
        last_seq = wire.seq
        last_recv = int(wire.bridge_recv_monotonic_ns)
    return PaperTickTransportMatch(
        expected_session,
        tuple(row.server_tick for row in trace.samples),
    )


@dataclass(frozen=True, slots=True)
class PaperL0ShadowTransportMatch:
    """Exact pair count, but neither L0 freshness nor Action authorization."""

    session_id: str
    paired_server_ticks: tuple[int, ...]
    shadow_cache_evaluated_ticks: tuple[int, ...]
    unknown_or_uncovered_ticks: tuple[int, ...]
    l0_fresh_world_tick_attested: bool = False
    tps_change_admitted: bool = False


def join_paper_l0_shadow(
    paper_log: str,
    delivered: tuple[MineflayerPaperTickSample, ...],
    shadows: tuple[MineflayerPaperL0Shadow, ...],
    *,
    expected_world: str,
    expected_player: str,
    expected_session: str,
) -> PaperL0ShadowTransportMatch:
    """Pair Paper->bridge tick with immediate cache-only scan in same stream.

    No paper tick becomes a source-qualified L0 decision or rate permit.
    """
    transport = join_paper_tick_transport(
        paper_log, delivered, expected_world=expected_world,
        expected_player=expected_player, expected_session=expected_session,
    )
    if (
        type(shadows) is not tuple
        or len(shadows) != len(delivered)
        or not all(type(v) is MineflayerPaperL0Shadow for v in shadows)
    ):
        raise PaperTickProbeRejected("one cache-shadow result per Paper delivery required")
    prior_shadow_seq = -1
    unknown: list[int] = []
    for tick, sample, shadow in zip(transport.server_ticks, delivered, shadows):
        if (
            shadow.session_id != expected_session
            or shadow.seq != sample.seq + 1
            or shadow.seq <= prior_shadow_seq
            or shadow.paper_sample_index != sample.index
            or shadow.paper_server_tick != sample.server_tick
            or shadow.paper_world != sample.world
            or shadow.paper_player != sample.player
            or int(shadow.evaluation_duration_ns) < 0
        ):
            raise PaperTickProbeRejected("shadow scan not in same bridge receive turn")
        prior_shadow_seq = shadow.seq
        if not shadow.cached_body_observed or shadow.assessment == "UNKNOWN":
            unknown.append(tick)
    return PaperL0ShadowTransportMatch(
        expected_session, transport.server_ticks,
        transport.server_ticks, tuple(unknown),
    )
