"""Read-only S1 Native stdin/WAL correlation; never an issue authority.

The two supplied hashes detect byte changes, not capture custody or a trusted
restart anchor. Native stdout remains independently decoded by the S1 auditor.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

from relay_self.i_lane_i4a_s1_native_source_audit_dev import (
    I4AS1NativeSourceHold,
    audit_i4a_original_s1_native_stdout,
)
from relay_self.i_lane_i4a_s1_source_capture_dev import I4AS1SourceCapture, I4AS1SourceHold, _raw
from relay_self.physical_action_journal import PhysicalActionJournal


@dataclass(frozen=True, slots=True)
class I4AS1CommandReadback:
    stdin_sha256: str
    child_commands: int
    classification: str = "I4A_S1_NATIVE_COMMAND_CORRELATION_CPU_OFFLINE_ONLY"
    restart_authenticated: bool = False
    physical_authorized: bool = False


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


_REQUEST = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\\Z")


def _require_original_place_heading(row: dict, command: dict) -> None:
    """WAL target/source geometry is not independent WorldBody clearance."""
    before, target = row["started_position"], row["target_position"]
    dx, dz = target["x"] - before["x"], target["z"] - before["z"]
    if not math.isfinite(dx) or not math.isfinite(dz) or (dx == 0 and dz == 0):
        raise ValueError("original target has no horizontal heading")
    # Independent numeric check against the original Mineflayer yaw convention.
    expected = math.atan2(-dx, -dz)
    if (
        abs(row["aim_yaw_rad"] - expected) > 1e-6
        or abs(command["yaw"] - expected) > 1e-6
        or command["pitch"] != 0.0
    ):
        raise ValueError("original PLACE target/yaw/pitch mismatch")


def audit_i4a_s1_native_commands(
    captured: I4AS1SourceCapture, *, native_stdout: Path,
    expected_native_stdout_sha256: str, native_stdin: Path,
    expected_native_stdin_sha256: str,
) -> I4AS1CommandReadback:
    """Match exact-once ordered MOVE child commands to the already audited WAL."""
    audit_i4a_original_s1_native_stdout(
        captured, native_stdout=native_stdout,
        expected_native_stdout_sha256=expected_native_stdout_sha256,
    )
    try:
        raw = _raw(native_stdin)
        digest = hashlib.sha256(raw).hexdigest()
        if (type(expected_native_stdin_sha256) is not str
                or digest != expected_native_stdin_sha256 or not raw.endswith(b"\n")):
            raise ValueError("stdin bytes or digest mismatch")
        commands = [json.loads(line, object_pairs_hook=_unique_object,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                    for line in raw.decode("utf-8").splitlines()]
        journal = PhysicalActionJournal.restore(Path(captured.path), self_id=captured.self_id)
        expected = []
        look_rows = {}
        for row in journal.records:
            look_rows[row["action_id"] + "-look"] = row
            parent = row["action_id"]
            expected.extend([(parent + "-look", "look"), (parent + "-start", "set_control"),
                             (parent + "-stop", "clear_controls")])
            if row.get("gait_ack_seq") is not None:
                # Sequence order, rather than assumed placement, is canonical.
                expected.append((parent + "-sneak", "set_control"))
        expected.sort(key=lambda pair: next(
            seq for row in journal.records for seq, suffix in (
                (row["effect_seqs"][0], "-look"), (row["effect_seqs"][1], "-start"),
                (row["effect_seqs"][2], "-stop"), (row.get("gait_ack_seq"), "-sneak"),
            ) if seq is not None and row["action_id"] + suffix == pair[0]))
        effects = []
        for index, command in enumerate(commands):
            if type(command) is not dict or command.get("type") not in {"effect", "observe", "shutdown"}:
                raise ValueError("unknown command")
            if command["type"] == "observe":
                if not (
                    set(command) == {"type"}
                    or (set(command) == {"type", "request_id"}
                        and type(command["request_id"]) is str
                        and _REQUEST.fullmatch(command["request_id"]) is not None)
                ):
                    raise ValueError("foreign observe command fields")
                continue
            if command["type"] == "shutdown":
                if set(command) != {"type"} or index != len(commands) - 1:
                    raise ValueError("foreign or premature shutdown command")
                continue
            action, effect = command.get("action_id"), command.get("effect")
            if effect == "look":
                if (set(command) != {"type", "action_id", "effect", "yaw", "pitch"}
                        or any(type(command[k]) not in (int, float) or not math.isfinite(command[k])
                               for k in ("yaw", "pitch"))):
                    raise ValueError("invalid look")
                source_row = look_rows.get(action)
                if source_row is None:
                    raise ValueError("unowned original LOOK")
                _require_original_place_heading(source_row, command)
            elif effect == "set_control":
                if (set(command) != {"type", "action_id", "effect", "control", "state"}
                        or command["state"] is not True
                        or command["control"] != ("sneak" if str(action).endswith("-sneak") else "forward")):
                    raise ValueError("invalid control")
            elif effect == "clear_controls":
                if set(command) != {"type", "action_id", "effect"}:
                    raise ValueError("invalid stop")
            else:
                raise ValueError("unexpected effect")
            effects.append((action, effect))
        if effects != expected:
            raise ValueError("missing, duplicate, reordered or foreign command")
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, I4AS1SourceHold) as exc:
        raise I4AS1NativeSourceHold("original Native stdin correlation failed") from exc
    return I4AS1CommandReadback(digest, len(effects))
