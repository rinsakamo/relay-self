"""Read-only Paper-main-thread MOVE position witness, independent of Mineflayer.

P0M sidecar is not a motor issuer or an authenticated Paper process owner.
No fallback to Mineflayer positions or client time if its raw trace is absent.
"""
from __future__ import annotations

import asyncio
import hashlib
import math
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.python_protocol import MineflayerPosition

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_KEYS = {
    "boot_id", "nonce", "world_uuid", "actor_uuid", "action_id",
    "native_session_id", "arm_tick", "stop_mark_tick", "source",
}
_ARM_KEYS = {"boot_id", "nonce", "world_uuid", "actor_uuid", "action_id",
             "native_session_id", "arm_tick", "source"}


class PaperMoveWitnessError(ValueError):
    """Foreign, incomplete or insufficient Paper tick-position evidence."""


def _uuid(name: str, raw: str) -> str:
    try:
        if type(raw) is not str or str(uuid.UUID(raw)) != raw:
            raise ValueError(raw)
    except (TypeError, AttributeError, ValueError) as exc:
        raise PaperMoveWitnessError(f"noncanonical {name}") from exc
    return raw


def _token(name: str, raw: str) -> str:
    if type(raw) is not str or _TOKEN.fullmatch(raw) is None:
        raise PaperMoveWitnessError(f"invalid {name}")
    return raw


def _properties(raw: bytes, *, trace: bool) -> tuple[dict[str, str], tuple[tuple[int, MineflayerPosition], ...]]:
    if type(raw) is not bytes or len(raw) > 16384:
        raise PaperMoveWitnessError("invalid or oversized Paper proof")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise PaperMoveWitnessError("non-UTF8 Paper proof") from exc
    values: dict[str, str] = {}
    samples: list[tuple[int, MineflayerPosition]] = []
    for line in lines:
        k, sep, v = line.partition("=")
        if not sep:
            raise PaperMoveWitnessError("non-field Paper proof line")
        if k == "sample" and trace:
            parts = v.split(",")
            if (len(parts) != 4 or not parts[0].isdecimal()
                    or len(parts[0]) > 10):
                raise PaperMoveWitnessError("malformed Paper sample")
            try:
                n = int(parts[0])
                xyz = [float(c) for c in parts[1:]]
                if any(not math.isfinite(x) for x in xyz):
                    raise ValueError("nonfinite sample")
                pos = MineflayerPosition(*xyz)
            except (ValueError, OverflowError) as exc:
                raise PaperMoveWitnessError("invalid Paper position") from exc
            samples.append((n, pos))
            if len(samples) > 128:
                raise PaperMoveWitnessError("unbounded Paper sample window")
        elif k in (_KEYS if trace else _ARM_KEYS) and k not in values:
            values[k] = _token(k, v)
        else:
            raise PaperMoveWitnessError("unknown, duplicate or misplaced Paper field")
    if set(values) != (_KEYS if trace else _ARM_KEYS):
        raise PaperMoveWitnessError("missing Paper provenance fields")
    for k in ("boot_id", "nonce", "world_uuid", "actor_uuid"):
        _uuid(k, values[k])
    if values["source"] != "PAPER_MAIN_THREAD":
        raise PaperMoveWitnessError("not main-thread Paper evidence")
    for k in ("arm_tick", "stop_mark_tick") if trace else ("arm_tick",):
        v = values[k]
        if not v.isdecimal() or len(v) > 10 or str(int(v)) != v:
            raise PaperMoveWitnessError("invalid Paper tick")
    return values, tuple(samples)


def _point_distance(a: MineflayerPosition, b: MineflayerPosition) -> float:
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


def _horizontal(a: MineflayerPosition, b: MineflayerPosition) -> float:
    return math.hypot(a.x - b.x, a.z - b.z)


@dataclass(frozen=True, slots=True)
class PaperMoveStopProof:
    boot_id: str
    world_uuid: str
    actor_uuid: str
    action_id: str
    native_session_id: str
    arm_tick: int
    stop_mark_tick: int
    stable_start_tick: int
    stable_end_tick: int
    paper_start_position: MineflayerPosition
    paper_stop_position: MineflayerPosition
    paper_final_position: MineflayerPosition
    paper_targetward_progress_m: float
    paper_residual_max_m: float
    raw_sha256: str
    source: str = "PAPER_MAIN_THREAD"
    paper_position_stable_8_ticks: bool = True
    physical_arrival_attested: bool = False
    native_stop_ack_attributed: bool = False  # host callback is a causal bridge, not server receipt


def qualify_paper_move_trace(
    raw: bytes, *, nonce: str, world_uuid: str, actor_uuid: str,
    action_id: str, native_session_id: str, native_start: MineflayerPosition,
    native_target: MineflayerPosition,
    paper_owned_log: bytes,
) -> PaperMoveStopProof:
    """Independently check Paper arm/marker/position across >=16 ticks.

    A host-side marker after a native STOP ACK is a local observational join,
    NOT a server-side authenticated action ACK or Minecraft-wide settling.
    """
    f, samples = _properties(raw, trace=True)
    if any((
        f["nonce"] != _uuid("expected nonce", nonce),
        f["world_uuid"] != _uuid("expected world UUID", world_uuid),
        f["actor_uuid"] != _uuid("expected actor UUID", actor_uuid),
        f["action_id"] != _token("expected action", action_id),
        f["native_session_id"] != _token("expected native session", native_session_id),
        not isinstance(native_start, MineflayerPosition),
        not isinstance(native_target, MineflayerPosition),
        type(paper_owned_log) is not bytes,
    )):
        raise PaperMoveWitnessError("Paper witness foreign to selected original MOVE")
    arm = int(f["arm_tick"])
    stop = int(f["stop_mark_tick"])
    if stop <= arm or not 0 < stop - arm <= 100:
        raise PaperMoveWitnessError("Paper MOVE arm/STOP tick order not evidenced")
    if (
        len(samples) < 17
        or samples[0][0] != arm
        or samples[-1][0] != stop + 16
        or any(b[0] != a[0] + 1 for a, b in zip(samples, samples[1:]))
    ):
        raise PaperMoveWitnessError("missing consecutive Paper tick/position samples")
    indexed = dict(samples)
    if not all(n in indexed for n in range(stop, stop + 17)):
        raise PaperMoveWitnessError("Paper STOP sample interval incomplete")
    p0 = indexed[arm]
    marked = indexed[stop]
    if _point_distance(p0, native_start) > .20:
        raise PaperMoveWitnessError("Paper start and native start positions inconsistent")
    progress = _horizontal(p0, native_target) - _horizontal(marked, native_target)
    if progress < .25:
        raise PaperMoveWitnessError("Paper did not independently show targetward progress")
    baseline = indexed[stop + 8]
    residual = max(
        _point_distance(baseline, indexed[t]) for t in range(stop + 8, stop + 17)
    )
    if residual > .06:
        raise PaperMoveWitnessError("Paper body not stable for 8 full ticks")
    ready = f"P0M_READY boot={f['boot_id']} source=PAPER_MAIN_THREAD"
    armed = (
        f"P0M_ARM nonce={nonce} boot={f['boot_id']} action={action_id}"
        f" actor={actor_uuid} world={world_uuid} tick={arm}"
    )
    marker = f"P0M_STOP_MARK nonce={nonce} boot={f['boot_id']} tick={stop}"
    done = (
        f"P0M_COMPLETE nonce={nonce} boot={f['boot_id']}"
        f" tick={samples[-1][0]} source=PAPER_MAIN_THREAD"
    )
    log = paper_owned_log.decode("utf-8", errors="replace").splitlines()
    indices = [
        next((i for i, line in enumerate(log) if value in line), None)
        for value in (ready, armed, marker, done)
    ]
    if None in indices or indices != sorted(indices):
        raise PaperMoveWitnessError("Paper positions not joined to same owned log")
    return PaperMoveStopProof(
        f["boot_id"], world_uuid, actor_uuid, action_id, native_session_id,
        arm, stop, stop + 8, stop + 16, p0, marked, indexed[stop + 16],
        progress, residual, hashlib.sha256(raw).hexdigest(),
    )


def _write_request(path: Path, fields: dict[str, str]) -> None:
    """Publish a complete fsynced request, never half-written .arm/.mark."""
    if path.is_symlink() or path.parent.is_symlink() or not path.parent.is_dir():
        raise PaperMoveWitnessError("Paper request directory unavailable")
    data = "".join(f"{k}={fields[k]}\n" for k in sorted(fields)).encode()
    staging = path.with_name(path.name + ".tmp")
    fd = os.open(
        staging, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600,
    )
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # Atomic publication with no overwrite; Java polls only .arm/.mark.
        os.link(staging, path, follow_symlinks=False)
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        staging.unlink(missing_ok=True)


class PaperMoveWitnessSession:
    """Asynchronous local DEV spool; no Paper command or physical Action emitted."""

    def __init__(
        self, spool: Path, *, world_uuid: str, actor_uuid: str,
        action_id: str, native_session_id: str,
        native_start: MineflayerPosition, native_target: MineflayerPosition,
        read_owned_log,
    ) -> None:
        self.spool = Path(spool)
        self.world_uuid = _uuid("world UUID", world_uuid)
        self.actor_uuid = _uuid("actor UUID", actor_uuid)
        self.action_id = _token("action ID", action_id)
        self.native_session_id = _token("native session", native_session_id)
        self.native_start = native_start
        self.native_target = native_target
        self.read_owned_log = read_owned_log
        self.nonce = str(uuid.uuid4())
        self.armed = False
        self.marked = False
        self.proof: PaperMoveStopProof | None = None
        if any(
            not (self.spool / sub).is_dir() or (self.spool / sub).is_symlink()
            for sub in ("requests", "acks", "complete")
        ):
            raise PaperMoveWitnessError("P0M plugin spool not enabled")

    async def _await(self, path: Path, seconds: float) -> bytes:
        deadline = asyncio.get_running_loop().time() + seconds
        while asyncio.get_running_loop().time() < deadline:
            if path.is_symlink():
                raise PaperMoveWitnessError("Paper witness symlink")
            if path.is_file():
                raw = path.read_bytes()
                if len(raw) > 16384:
                    raise PaperMoveWitnessError("oversized Paper witness")
                return raw
            await asyncio.sleep(.025)
        raise PaperMoveWitnessError("Paper MOVE witness timed out")

    async def arm(self, seconds: float = 3.0) -> None:
        if self.armed:
            raise PaperMoveWitnessError("Paper MOVE observer already armed")
        _write_request(self.spool / "requests" / (self.nonce + ".arm"), {
            "nonce": self.nonce, "world_uuid": self.world_uuid,
            "actor_uuid": self.actor_uuid, "action_id": self.action_id,
            "native_session_id": self.native_session_id,
        })
        raw = await self._await(self.spool / "acks" / (self.nonce + ".armed"), seconds)
        f, samples = _properties(raw, trace=False)
        if samples or any((
            f["nonce"] != self.nonce,
            f["world_uuid"] != self.world_uuid,
            f["actor_uuid"] != self.actor_uuid,
            f["action_id"] != self.action_id,
            f["native_session_id"] != self.native_session_id,
        )):
            raise PaperMoveWitnessError("foreign Paper arm receipt")
        self.armed = True

    async def mark_stop_after_ack(self, seconds: float = 3.0) -> None:
        if not self.armed or self.marked:
            raise PaperMoveWitnessError("Paper STOP marker requires original arm")
        _write_request(self.spool / "requests" / (self.nonce + ".mark"), {
            "nonce": self.nonce, "action_id": self.action_id,
        })
        self.marked = True
        # The plugin continues main-thread observation after this marker.

    async def finish(self, seconds: float = 6.0) -> PaperMoveStopProof:
        if not self.armed or not self.marked or self.proof is not None:
            raise PaperMoveWitnessError("Paper MOVE witness lifecycle incomplete")
        raw = await self._await(self.spool / "complete" / (self.nonce + ".trace"), seconds)
        proof = qualify_paper_move_trace(
            raw, nonce=self.nonce, world_uuid=self.world_uuid,
            actor_uuid=self.actor_uuid, action_id=self.action_id,
            native_session_id=self.native_session_id,
            native_start=self.native_start, native_target=self.native_target,
            paper_owned_log=self.read_owned_log(),
        )
        self.proof = proof
        return proof
