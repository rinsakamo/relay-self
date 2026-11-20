"""Operator-only native observation intake. No action or Self memory authority.

The existing native protocol does not expose the authoritative terrain, Paper
clock, or body geometry needed to qualify a real route.  In particular a
well-formed native probe is not a source-qualified World snapshot.
"""
from __future__ import annotations

from dataclasses import asdict

from adapters.mineflayer.python_protocol import MineflayerObservation


def inspect_native_probe(observation: MineflayerObservation, *,
                         expected_session: str, expected_request_id: str,
                         previous_seq: int) -> dict:
    """Preserve available original probe fields and fail closed on missing sources.

    This is an intake adapter, not an authentication mechanism. Caller-provided
    expectations are not evidence of Owner identity or World generation.
    """
    def unknown(code: str, **evidence: object) -> dict:
        return {"status": "UNKNOWN", "reason_code": code, "evidence": evidence}

    if not isinstance(observation, MineflayerObservation):
        return unknown("NATIVE_PROBE_UNAVAILABLE")
    if (type(expected_session) is not str or not expected_session
            or observation.session_id != expected_session):
        return unknown("NATIVE_SESSION_MISMATCH")
    if (observation.kind != "probe" or type(expected_request_id) is not str
            or not expected_request_id or observation.request_id != expected_request_id):
        return unknown("NATIVE_REQUEST_MISMATCH")
    if type(previous_seq) is not int or previous_seq < 0 or observation.seq <= previous_seq:
        return unknown("NATIVE_SEQUENCE_NOT_MONOTONIC")
    snapshot = observation.snapshot
    return unknown(
        "SOURCE_SNAPSHOT_INCOMPLETE",
        source="mineflayer_native_probe", session_id=observation.session_id,
        sequence=observation.seq, request_id=observation.request_id,
        position=asdict(snapshot.position),
        nearby_entities=[asdict(entity) for entity in snapshot.nearby_entities],
        nearby_entities_coverage=asdict(snapshot.nearby_entities_coverage),
        unavailable=["world_uuid", "dimension", "world_generation", "paper_tick",
                     "observation_time", "self_identity", "body_aabb", "pose",
                     "grounded", "control_state", "loaded_chunks", "block_states",
                     "collision_shapes", "complete_dynamic_occupancy", "atomicity"],
    )


async def capture_native_probe(session, *, expected_session: str, previous_seq: int,
                               timeout_s: float = 5.0) -> dict:
    """Request one read-only probe on an exclusively consumed native session.

    Does not start a process or issue physical actions. The caller must own the
    session and its receive stream; a request ID and matching session alone do
    not establish that ownership.
    """
    import asyncio
    import math
    import uuid

    if (type(timeout_s) not in (int, float) or not math.isfinite(timeout_s)
            or not 0 < timeout_s <= 30 or type(expected_session) is not str
            or not expected_session or type(previous_seq) is not int or previous_seq < 0):
        return {"status": "UNKNOWN", "reason_code": "INVALID_CAPTURE_REQUEST", "evidence": {}}
    try:
        if session.started.session_id != expected_session:
            return {"status": "UNKNOWN", "reason_code": "NATIVE_SESSION_MISMATCH", "evidence": {}}
        request_id = "stage27l-" + uuid.uuid4().hex
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_s
        await asyncio.wait_for(session.send_observe(request_id), timeout_s)
        for _ in range(256):
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            entry = await asyncio.wait_for(session.receive(), remaining)
            if entry.session_id != expected_session:
                return {"status": "UNKNOWN", "reason_code": "NATIVE_SESSION_MISMATCH", "evidence": {}}
            if isinstance(entry, MineflayerObservation) and entry.kind == "probe":
                return inspect_native_probe(entry, expected_session=expected_session,
                                            expected_request_id=request_id, previous_seq=previous_seq)
    except (TimeoutError, OSError, AttributeError, RuntimeError):
        pass
    return {"status": "UNKNOWN", "reason_code": "NATIVE_CAPTURE_FAILED", "evidence": {}}
