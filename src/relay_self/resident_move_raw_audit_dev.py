"""#904 Stage23b: independently reread original Mineflayer stdout MOVE transcript.

The owned Node stdout capture is the original JSONL source bytes, not
reconstructed dataclass/asdict output. This source join is independent of
the in-memory issuer's validation, but is NOT a Paper server-side
Action-specific causation receipt or authentication against forged Node IO.
Never infer it existed for pre-Stage23b real trials.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
    parse_mineflayer_line,
)
from experiments.cognitive_physical_move_issue_dev import ResidentMoveDevReceipt
from relay_self.physical_action_journal import PhysicalActionJournal


class ResidentMoveRawAuditError(ValueError):
    """Loss, spoof, mismatched native identity, stale probe or WAL source."""


def _tick(probe: MineflayerObservation) -> int:
    clock = probe.snapshot.time
    if clock is None:
        raise ResidentMoveRawAuditError("raw MOVE probe World tick missing")
    return clock.day * 24000 + clock.time_of_day


def _place(probe: MineflayerObservation) -> dict[str, float]:
    p = probe.snapshot.position
    return {"x": p.x, "y": p.y, "z": p.z}


def _dist(a: MineflayerObservation, b: MineflayerObservation) -> float:
    p, q = a.snapshot.position, b.snapshot.position
    return math.dist((p.x, p.y, p.z), (q.x, q.y, q.z))


def readback_owned_move_native_source(
    *,
    raw_path: Path,
    journal_path: Path,
    self_id: str,
    action_id: str,
    current_probe: MineflayerObservation,
    receipt: ResidentMoveDevReceipt,
) -> dict[str, object]:
    """Strict full-source replay of one already-terminal original MOVE.

    This verifier reads original captured stdout *bytes* from a frozen file.
    Its caller must have attached that file to the EXACT owned native
    process before B's two preparatory probes and frozen it after the MOVE.
    A path by itself is NOT proof of that process ownership.
    """
    if (
        type(self_id) is not str or not self_id
        or type(action_id) is not str or not action_id
        or not isinstance(current_probe, MineflayerObservation)
        or not isinstance(receipt, ResidentMoveDevReceipt)
    ):
        raise ResidentMoveRawAuditError("original MOVE source/owner malformed")
    source = Path(raw_path).read_bytes()
    if (
        not source or len(source) > 8_000_000
        or not source.endswith(b"\n") or b"\r" in source
    ):
        raise ResidentMoveRawAuditError("raw native transcript incomplete or oversized")
    try:
        lines = [x.decode("utf-8") for x in source.splitlines()]
        parsed = [parse_mineflayer_line(x) for x in lines]
    except (UnicodeDecodeError, ValueError) as exc:
        raise ResidentMoveRawAuditError("raw native transcript decode failed") from exc
    if not parsed or not all(
        x.session_id == current_probe.session_id for x in parsed
    ) or not all(
        b.seq == a.seq + 1 for a, b in zip(parsed, parsed[1:])
    ):
        raise ResidentMoveRawAuditError("raw native source session/seq not continuous")
    before = [x for x in parsed if x == current_probe]
    if len(before) != 1:
        raise ResidentMoveRawAuditError("original selected B probe absent/duplicated")

    def one_child(effect: str, child_id: str) -> MineflayerEffectResult:
        matches = [
            x for x in parsed
            if isinstance(x, MineflayerEffectResult)
            and x.action_id == child_id
        ]
        if (
            len(matches) != 1
            or matches[0].effect != effect
            or matches[0].result != "applied"
            or matches[0].error is not None
        ):
            raise ResidentMoveRawAuditError("MOVE source child ACK absent/forged")
        return matches[0]

    start = one_child("set_control", action_id + "-start")
    stop = one_child("clear_controls", action_id + "-stop")
    if start != receipt.start_ack or stop != receipt.stop_ack:
        raise ResidentMoveRawAuditError("source ACK differs from original MOVE issuer")

    stops = [
        x for x in parsed
        if isinstance(x, MineflayerObservation)
        and x.kind == "probe"
        and x.request_id is not None
        and x.request_id.startswith("p0d-move-stop-")
    ]
    if (
        not stops or len(stops) > 256
        or tuple(stops) != receipt.all_stop_probes
        or stops[0] != receipt.initial_stop_probe
        or stops[-1] != receipt.settled_probe
        or receipt.first_stable_probe not in stops
    ):
        raise ResidentMoveRawAuditError("one or more raw STOP probes missing/modified")
    if not current_probe.seq < start.seq < stop.seq < stops[0].seq:
        raise ResidentMoveRawAuditError("source start/STOP/probe order incorrect")
    if (
        len({x.request_id for x in stops}) != len(stops)
        or any(
            not a.seq < b.seq or not _tick(a) <= _tick(b)
            for a, b in zip(stops, stops[1:])
        )
        or _tick(stops[-1]) - _tick(stops[0]) > 200
    ):
        raise ResidentMoveRawAuditError("native STOP probe sequence/clock regressed")
    initial, first, settled = (
        receipt.initial_stop_probe,
        receipt.first_stable_probe,
        receipt.settled_probe,
    )
    # Recompute the original settling algorithm from ALL captured probes,
    # including intermediate drift; do not trust a success-only terminal
    # summary's asserted choice of first/stable/settled samples.
    reached_first = False
    baseline = initial
    recomputed: tuple[MineflayerObservation, MineflayerObservation] | None = None
    for sample in stops[1:]:
        if not reached_first:
            if _tick(sample) - _tick(initial) >= 8:
                baseline = sample
                reached_first = True
            continue
        if _tick(sample) - _tick(baseline) < 8:
            continue
        if _dist(baseline, sample) <= 0.06:
            recomputed = (baseline, sample)
            break
        baseline = sample
    if recomputed != (first, settled) or stops[-1] != settled:
        raise ResidentMoveRawAuditError("raw intermediate STOP drift changes terminal verdict")
    if (
        not 8 <= _tick(first) - _tick(initial) <= 200
        or not 8 <= _tick(settled) - _tick(first) <= 200
        or _dist(first, settled) > 0.06
        or not 0.1 <= _dist(current_probe, settled) <= 8.0
        or abs(_dist(current_probe, settled) - receipt.displacement_m) > 1e-6
    ):
        raise ResidentMoveRawAuditError("raw STOP 8+8 ticks/drift/displacement failed")

    persisted = PhysicalActionJournal.restore(journal_path, self_id=self_id)
    records = persisted.records
    if not records or persisted.unresolved or persisted.digest != receipt.journal_sha256:
        raise ResidentMoveRawAuditError("original canonical WAL not settled/matched")
    row = records[-1]
    if (
        row["status"] != "NATIVE_MOVE_SETTLED"
        or row["capability"] != "MOVE"
        or row["action_id"] != action_id
        or row["session_id"] != current_probe.session_id
        or row["probe_seq"] != current_probe.seq
        or row["probe_request_id"] != current_probe.request_id
        or row["effect_seqs"] != [start.seq, stop.seq]
        or row["initial_stop_seq"] != initial.seq
        or row["first_stable_seq"] != first.seq
        or row["after_seq"] != settled.seq
        or row["initial_stop_tick"] != _tick(initial)
        or row["first_stable_tick"] != _tick(first)
        or row["settled_tick"] != _tick(settled)
        or abs(row["displacement_m"] - receipt.displacement_m) > 1e-6
    ):
        raise ResidentMoveRawAuditError("original WAL and native stdout source diverged")
    if (
        math.dist(
            tuple(row["started_position"][k] for k in ("x", "y", "z")),
            tuple(_place(current_probe)[k] for k in ("x", "y", "z")),
        ) > 1e-7
        or math.dist(
            tuple(row["settled_position"][k] for k in ("x", "y", "z")),
            tuple(_place(settled)[k] for k in ("x", "y", "z")),
        ) > 1e-7
    ):
        raise ResidentMoveRawAuditError("native source coordinates differ from original WAL")
    return {
        "schema": 1,
        "classification": "OWNED_NATIVE_MOVE_RAW_SOURCE_READBACK_DEV",
        "original_self_id": self_id,
        "original_native_session": current_probe.session_id,
        "original_action_id": action_id,
        "source_file": str(raw_path),
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "source_byte_length": len(source),
        "source_line_count": len(parsed),
        "canonical_wal_digest": persisted.digest,
        "native_start_ack": {
            "session_id": start.session_id, "seq": start.seq,
            "action_id": start.action_id, "effect": start.effect,
            "result": start.result, "error": start.error,
        },
        "native_stop_ack": {
            "session_id": stop.session_id, "seq": stop.seq,
            "action_id": stop.action_id, "effect": stop.effect,
            "result": stop.result, "error": stop.error,
        },
        "selected_probe": {
            "seq": current_probe.seq, "request_id": current_probe.request_id,
            "tick": _tick(current_probe), "position": _place(current_probe),
        },
        "all_stop_probes": [
            {
                "seq": x.seq, "request_id": x.request_id,
                "tick": _tick(x), "position": _place(x),
            }
            for x in stops
        ],
        "initial_stop_seq": initial.seq,
        "first_stable_seq": first.seq,
        "settled_seq": settled.seq,
        "native_net_displacement_m": receipt.displacement_m,
        "paper_action_id_causal_ticket": False,
        "autonomous_l1_skill_selection": False,
    }
