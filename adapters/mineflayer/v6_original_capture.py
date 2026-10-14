"""S #537: prospective V6 three-stream original-byte capture adapter.

This is a passive recorder for a *future separately authorized* S51 World.
It never starts Java/Node/Minecraft or sends an Action/console command.
Only the existing S51 owner may write actual server stdin. Issuer entries
are self-reported, NOT server acknowledgements. Buffered correlation fields
in the issuer projection are filled only from a subsequent actual native
probe, and can never count as independent original server authority.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from adapters.mineflayer.python_protocol import MineflayerObservation

CAPTURE_SCHEMA = "S_V6_ORIGINAL_THREE_STREAM_CAPTURE_CANDIDATE_V1"
SERVER_NAME = "server_stdout_original.log"
ISSUER_NAME = "issuer_commands_original.jsonl"
NATIVE_NAME = "native_bridge_original.jsonl"
ORIGINAL_NAMES = (SERVER_NAME, ISSUER_NAME, NATIVE_NAME)
SERVER_LIMIT = 4 * 1024 * 1024
ISSUER_LIMIT = 256 * 1024
NATIVE_LIMIT = 16 * 1024 * 1024
PHASES = (
    ("food_install", "function relayself_v6:install"),
    ("start_install", "function relayself_v6_start:install"),
    ("first_native_probe", "PROBE_NONISSUED"),
    ("start_function", "function relayself_v6_start:start_trial"),
    ("read_start_attempt", "scoreboard players get #start_attempt rs_v6_tick"),
    ("read_start_gametime", "scoreboard players get #start_gametime rs_v6_tick"),
    ("food_function", "execute at RelaySelf run function relayself_v6:atomic_food"),
    ("read_food_attempt", "scoreboard players get #attempt rs_v6_tick"),
    ("read_food_before", "scoreboard players get #before rs_v6_tick"),
    ("read_food_after", "scoreboard players get #after rs_v6_tick"),
    ("read_food_success", "scoreboard players get #ok rs_v6_tick"),
    ("shutdown_request", "stop"),
)
SLOTS = ("WORLD_START_A", "WORLD_START_B", "WORLD_START_C", "WORLD_START_D")


class V6CaptureRejected(ValueError):
    """A source violation, replay, truncation or incomplete capture."""


def _check(ok: bool, message: str) -> None:
    if not ok:
        raise V6CaptureRejected(message)


def _valid_line(raw: bytes, *, jsonl: bool) -> None:
    _check(
        type(raw) is bytes and 0 < len(raw) <= 16384
        and raw.endswith(b"\n") and raw != b"\n"
        and b"\r" not in raw and b"\x00" not in raw
        and not raw.startswith(b"\xef\xbb\xbf"),
        "noncanonical raw source line; never normalize original bytes",
    )
    if jsonl:
        try:
            value = json.loads(raw)
        except (UnicodeError, ValueError) as exc:
            raise V6CaptureRejected("malformed native original JSONL") from exc
        _check(type(value) is dict, "native original JSONL must contain objects")


class V6OriginalCapture:
    """Exclusive source-bytes writer; exact original streams only, no launcher.

    The supplier must call on_server_stdout/on_native_stdout with the
    *unmodified bytes read from its owned actual streams*, and call
    note_issuer_attempt only when the EXISTING S51 owner attempts the exact
    server-console command. This component cannot prove supplier authenticity.
    """

    def __init__(
        self, root: Path, *, session: str, slot: str, nonce: str,
    ) -> None:
        _check(
            isinstance(root, Path) and not root.is_symlink()
            and not root.exists() and root.parent.is_dir()
            and not root.parent.is_symlink(),
            "fresh non-aliased capture directory required",
        )
        _check(type(session) is str and bool(session.strip()), "session required")
        _check(slot in SLOTS and type(slot) is str, "unregistered World slot")
        _check(
            type(nonce) is str and re.fullmatch(r"[0-9a-f]{32}", nonce) is not None,
            "noncanonical trial correlation nonce",
        )
        root.mkdir(mode=0o700)
        self.root, self.session, self.slot, self.nonce = root, session, slot, nonce
        self._handles = {name: (root / name).open("xb") for name in ORIGINAL_NAMES}
        self._digests = {name: hashlib.sha256() for name in ORIGINAL_NAMES}
        self._sizes = dict.fromkeys(ORIGINAL_NAMES, 0)
        self._phase = 0
        self._pending: list[tuple[str, str, int]] = []
        self._last_monotonic = -1
        self._native_seq = -1
        self._native_first_observation: tuple[int, str | None, str | None] | None = None
        self._first_probe: tuple[int, str] | None = None
        self._closed = False
        self._seal_result: dict[str, Any] | None = None

    def _write(self, name: str, raw: bytes, maximum: int) -> None:
        _check(not self._closed, "original capture already closed")
        _check(self._sizes[name] + len(raw) <= maximum,
               "original capture hard byte bound exceeded")
        out = self._handles[name]
        out.write(raw)
        out.flush()
        self._digests[name].update(raw)
        self._sizes[name] += len(raw)

    def on_server_stdout(self, raw: bytes) -> None:
        """Only invoke on an actual subprocess stdout.readline() result."""
        _valid_line(raw, jsonl=False)
        self._write(SERVER_NAME, raw, SERVER_LIMIT)

    def on_native_stdout(self, raw: bytes) -> None:
        """Only invoke on actual process.stdout.readline() BEFORE decoding."""
        _valid_line(raw, jsonl=True)
        data = json.loads(raw)
        _check(
            data.get("session_id") == self.session
            and type(data.get("seq")) is int
            and data["seq"] == self._native_seq + 1,
            "foreign/noncontiguous original native frame",
        )
        if data.get("type") == "observation" and self._native_first_observation is None:
            self._native_first_observation = (
                data["seq"], data.get("kind"), data.get("request_id"),
            )
        self._write(NATIVE_NAME, raw, NATIVE_LIMIT)
        self._native_seq = data["seq"]

    def note_issuer_attempt(self, *, phase: str, command: str) -> None:
        """Journal a *reported* write attempt, not a successful server effect."""
        _check(self._phase < len(PHASES), "issuer phase budget exhausted")
        _check(PHASES[self._phase] == (phase, command)
               and phase != "first_native_probe",
               "unexpected/duplicated/forced issuer command")
        tick = time.monotonic_ns()
        _check(tick > self._last_monotonic, "nonmonotone issuer host clock")
        self._last_monotonic = tick
        self._pending.append((phase, command, tick))
        self._phase += 1
        if self._first_probe is not None:
            self._flush_pending()

    def note_first_native_probe(self, probe: MineflayerObservation) -> None:
        """Record a genuinely received item-free probe, never a WAIT Action."""
        _check(self._phase == 2 and self._first_probe is None,
               "first L0 probe is out of original issuer order")
        _check(
            isinstance(probe, MineflayerObservation)
            and probe.session_id == self.session
            and probe.kind == "probe" and bool(probe.request_id)
            and probe.provenance.source == "mineflayer"
            and probe.seq <= self._native_seq
            and probe.snapshot.inventory == ()
            and not probe.snapshot.nearby_entities_coverage.truncated
            and probe.snapshot.nearby_entities_coverage.candidate_count
            == len(probe.snapshot.nearby_entities)
            and not any(e.name == "item" for e in probe.snapshot.nearby_entities),
            "unbound or non-item-free first L0 probe",
        )
        # The original stream includes spawn, health and other observations;
        # the first *probe* need not be the first observation.
        first_probe = None
        with (self.root / NATIVE_NAME).open("rb") as stream:
            for raw in stream:
                frame = json.loads(raw)
                if frame.get("type") == "observation" and frame.get("kind") == "probe":
                    first_probe = (frame.get("seq"), frame.get("request_id"))
                    break
        _check(first_probe == (probe.seq, probe.request_id),
               "first typed L0 probe not present in raw native original")
        tick = time.monotonic_ns()
        _check(tick > self._last_monotonic, "nonmonotone probe binding clock")
        self._last_monotonic = tick
        self._first_probe = (probe.seq, probe.request_id)
        self._pending.append(("first_native_probe", "PROBE_NONISSUED", tick))
        self._phase += 1
        self._flush_pending()

    def _flush_pending(self) -> None:
        _check(self._first_probe is not None, "original probe not established")
        seq, request = self._first_probe
        # This is an *issuer projection*: the earlier two install attempts
        # are retrospectively correlated, not tamper-proof historical frames.
        already = self._phase - len(self._pending)
        for i, (phase, command, host) in enumerate(self._pending, already):
            row = {
                "session_id": self.session, "seq": i,
                "phase": phase, "issuer_command": command,
                "host_monotonic_ns": host,
                "first_probe_native_seq": seq,
                "first_probe_request_id": request,
            }
            data = (json.dumps(row, sort_keys=True, separators=(",", ":"))
                    + "\n").encode("utf-8")
            self._write(ISSUER_NAME, data, ISSUER_LIMIT)
        self._pending.clear()

    def close(self) -> dict[str, Any]:
        """Persist incomplete evidence on failure; NEVER synthesize closure."""
        _check(not self._closed, "one closure per original capture")
        self._closed = True
        for handle in self._handles.values():
            handle.flush()
            handle.close()
        complete = self._phase == len(PHASES) and self._first_probe is not None
        # Rejected or incomplete originals stay untouched on disk. Missing
        # STOP/native ACK/original server output still requires R readback.
        result = {
            "classification": (
                "S_V6_THREE_ORIGINAL_STREAMS_WRITTEN_SOURCE_ONLY"
                if complete else "S_V6_ORIGINAL_STREAMS_PARTIAL_NOT_QUALIFIED"
            ),
            "schema": CAPTURE_SCHEMA,
            "original_dir": str(self.root),
            "world_start_slot": self.slot,
            "trial_nonce": self.nonce,
            "issuer_phases_logged": self._phase,
            "first_l0_probe": (
                {"seq": self._first_probe[0], "request_id": self._first_probe[1]}
                if self._first_probe else None
            ),
            "sha256": {k: v.hexdigest() for k, v in self._digests.items()},
            "sizes": dict(self._sizes),
            "claimant_sha_is_external_precommit": False,
            "server_stdout_original_origin_r_attested": False,
            "native_stop_ack_r_attested": False,
            "independent_command_exclusivity_attested": False,
            "real_server_gametime_effect_attested": False,
            "physical_execution_authorized": False,
            "science_g3": "NO_GO",
        }
        self._seal_result = result
        return result
