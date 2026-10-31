"""L18: source-owner S16 terminal original, captured at existing S49 closure.

This is a new immutable *Python S16 owner-created* JSONL event: the existing
ActionSupervisor terminal and S16 interpretation are inputs. It is NOT raw
Minecraft packets, an independent external Goal, or L10 authorization.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    parse_mineflayer_line,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_outcome import ActionOutcomeDisposition, ActionOutcomeInterpretation
from relay_self.l13_independent_goal_receipt import _ACTION_KEYS, _PRE_SCHEMA
from relay_self.provenance import Provenance


class L18TerminalOriginalRejected(ValueError):
    """A S16 owner event cannot be silently forged or overwritten."""


S16_FILE = "l18_s16_terminal_original.jsonl"
S16_INDEX_FILE = "l18_s16_terminal_source_index.json"


def build_s16_owner_original(
    *, terminal: ActionLifecycle,
    outcome: ActionOutcomeInterpretation,
    consequence: WorldConsequence,
    original_pre_probe: bytes,
    source_revision: int,
) -> bytes:
    """Serialize actual S16 terminal fields without reinterpreting World IO."""
    if (
        not isinstance(terminal, ActionLifecycle)
        or not isinstance(outcome, ActionOutcomeInterpretation)
        or not isinstance(consequence, WorldConsequence)
        or not isinstance(original_pre_probe, bytes)
        or type(source_revision) is not int or source_revision < 0
        or terminal.state is not ActionState.OUTCOME
        or not terminal.is_current_snapshot
        or outcome.disposition is not ActionOutcomeDisposition.OUTCOME
        or outcome.source_status != "executed"
        or consequence.status is not WorldConsequenceStatus.EXECUTED
        or consequence.before_observation is None
        or consequence.after_observation is None
        or consequence.dispatch_receipt is None
        or consequence.cleanup_receipt is None
        or not original_pre_probe.endswith(b"\n")
        or original_pre_probe.count(b"\n") != 1
        or not 0 < len(original_pre_probe) <= 1024 * 1024
    ):
        raise L18TerminalOriginalRejected("S16 executed owner terminal required")
    try:
        parsed = parse_mineflayer_line(original_pre_probe.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise L18TerminalOriginalRejected("pre Action raw source invalid") from exc
    before = consequence.before_observation
    after = consequence.after_observation
    if (
        not isinstance(parsed, MineflayerObservation)
        or parsed != before
        or parsed.kind != before.kind or parsed.kind != "probe"
        or terminal.action_id != outcome.action_id
        or outcome.action_id != consequence.action_id
        or outcome.session_id != consequence.session_id
        or before.session_id != outcome.session_id
        or after.session_id != outcome.session_id
        or before.seq >= after.seq
        or terminal.provenance != outcome.world_provenance
        or not isinstance(outcome.world_provenance, Provenance)
        or outcome.action_ref != "MOVE_BACKWARD"
        or consequence.dispatch_receipt.action_id != terminal.action_id
        or consequence.cleanup_receipt.action_id != f"{terminal.action_id}-s15-clear"
        or consequence.dispatch_receipt.result != "applied"
        or consequence.cleanup_receipt.result != "applied"
    ):
        raise L18TerminalOriginalRejected("original Present, World and S16 owner disagree")
    record = {
        "schema": _PRE_SCHEMA,
        "session_id": outcome.session_id,
        "action_id": outcome.action_id,
        "binding_id": outcome.binding_id,
        "action_ref": outcome.action_ref,
        "pre_probe_sha256": hashlib.sha256(original_pre_probe).hexdigest(),
        "before_seq": before.seq,
        "after_seq": after.seq,
        "source_revision": source_revision,
        "source_status": outcome.source_status,
        "disposition": outcome.disposition.value,
        "reason_code": outcome.reason_code,
        "world_source": outcome.world_provenance.source,
        "world_reference": outcome.world_provenance.reference,
    }
    if set(record) != _ACTION_KEYS:
        raise L18TerminalOriginalRejected("S16 original incompatible with L13")
    return (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_s16_owner_original(
    *, capture_root: Path,
    terminal: ActionLifecycle,
    outcome: ActionOutcomeInterpretation,
    consequence: WorldConsequence,
    source_revision: int = 0,
) -> dict[str, object]:
    """Write exactly once in the S49 terminal callback, never after report replay.

    S7 owns the original native received stream. Read its existing exact
    pre-probe line; do not regenerate the pre-Action JSON from a dataclass.
    """
    if (
        not isinstance(capture_root, Path)
        or not capture_root.is_absolute()
        or not capture_root.is_dir()
        or capture_root.is_symlink()
        or capture_root.resolve(strict=True) != capture_root
    ):
        raise L18TerminalOriginalRejected("fresh canonical physical capture root required")
    if consequence.before_observation is None:
        raise L18TerminalOriginalRejected("missing source pre Action probe")
    received_path = capture_root / "native_bridge_received_original.jsonl"
    if received_path.is_symlink() or not received_path.is_file():
        raise L18TerminalOriginalRejected("S7 original source unavailable")
    raw = received_path.read_bytes()
    if not 0 < len(raw) <= 16 * 1024 * 1024:
        raise L18TerminalOriginalRejected("S7 raw source size out of bounds")
    lines = raw.splitlines(keepends=True)
    before_seq = consequence.before_observation.seq
    if type(before_seq) is not int or not 0 <= before_seq < len(lines):
        raise L18TerminalOriginalRejected("pre Action seq not in S7 source")
    original = build_s16_owner_original(
        terminal=terminal, outcome=outcome, consequence=consequence,
        original_pre_probe=lines[before_seq], source_revision=source_revision,
    )
    output = capture_root / S16_FILE
    with output.open("xb") as handle:
        handle.write(original)
        handle.flush()
        os.fsync(handle.fileno())
    return {
        "schema": "L18_S49_S16_OWNER_ORIGINAL_INDEX_V1",
        "path": str(output),
        "sha256": hashlib.sha256(original).hexdigest(),
        "bytes": len(original),
        "session_id": outcome.session_id,
        "action_id": outcome.action_id,
        "pre_probe_sha256": hashlib.sha256(lines[before_seq]).hexdigest(),
        "source_revision_operator_declared": source_revision,
        "s16_owner_snapshot_from_existing_executor": True,
        "minecraft_tcp_packet_original": False,
        "independent_external_goal_original": False,
        "original_physical_source_authenticated": False,
        "qualified_real_l10_pairs": 0,
    }
