"""T1h DEV-only S49 owner-local STOP handshake; no new physical issuer.

Node clear_controls ACK, Paper idle evidence and bridge shutdown are distinct.
A DEV STOP ACK is a bounded S49-owner receipt, NOT a R-qualified full-tick
World stop or qualification grant. No model, independent receiver or TPS writes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerEffectResult


class StopDevRejected(ValueError):
    """STOP evidence absent, out of order, duplicated or source-mismatched."""


@dataclass(frozen=True, slots=True)
class StopDevAck:
    stop_id: str
    session_id: str
    active_action_id: str | None
    clear_action_id: str
    clear_ack_seq: int
    marker_id: str
    world: str
    player: str
    first_idle_tick: int
    last_idle_tick: int
    observed_idle_ticks: int = 8
    classification: str = "S49_DEV_STOP_ACK_PAPER_IDLE_WINDOW"
    high_level_dev_stop_ack: bool = True
    full_tick_stillness_qualified: bool = False
    native_source_independently_authenticated: bool = False
    p1_qualified_wait: bool = False


def _id(name: str, value: object) -> str:
    if type(value) is not str or not value or len(value) > 128 or not all(
        c.isalnum() or c in "-_" for c in value
    ):
        raise StopDevRejected(f"invalid {name}")
    return value


def _row_tokens(line: str, prefix: str) -> dict[str, str]:
    fields = line.split(prefix, 1)[1].split()
    if not fields:
        raise StopDevRejected("empty Paper evidence")
    data: dict[str, str] = {}
    for token in fields:
        if token.count("=") != 1:
            raise StopDevRejected("invalid Paper token")
        k, v = token.split("=", 1)
        if not k or not v or k in data:
            raise StopDevRejected("duplicate/empty Paper field")
        data[k] = v
    return data


def _positive_int(row: dict[str, str], key: str) -> int:
    val = row.get(key, "")
    if not val.isdecimal() or (len(val) > 1 and val[0] == "0"):
        raise StopDevRejected(f"invalid Paper {key}")
    n = int(val)
    if n < 0 or n >= 2**63:
        raise StopDevRejected(f"out of range Paper {key}")
    return n


def _position(row: dict[str, str]) -> tuple[float, float, float]:
    try:
        values = tuple(float(row[k]) for k in ("x", "y", "z"))
    except (KeyError, ValueError) as exc:
        raise StopDevRejected("Paper pose absent") from exc
    if not all(math.isfinite(x) for x in values):
        raise StopDevRejected("nonfinite Paper pose")
    return values


def paper_stopped_after_marker(
    content: str, *, marker_id: str, world: str, player: str,
) -> tuple[int, int]:
    """Only 8 consecutive server-callback idle+stationary rows after marker.

    A sampled idle window does NOT prove no unobserved sub-tick activity.
    The original logger must be retained and its source handled independently.
    """
    _id("marker_id", marker_id)
    if not isinstance(content, str) or not content or len(content) > 4_000_000:
        raise StopDevRejected("bounded original Paper text required")
    # Marker is a Paper console command issued by the original S49 owner
    # only AFTER it received the matching native clear ACK.
    markers = [
        _row_tokens(x, "S_V8_DEV_SNAPSHOT ")
        for x in content.splitlines() if "S_V8_DEV_SNAPSHOT " in x
        and f"marker_id={marker_id} " in x
    ]
    if len(markers) != 1:
        raise StopDevRejected("unique post-clear Paper marker required")
    marker = markers[0]
    if marker.get("marker_id") != marker_id or marker.get("world") != world:
        raise StopDevRejected("foreign Paper stop marker")
    start_tick = _positive_int(marker, "server_tick")
    samples = [
        _row_tokens(x, "PAPER_DEV_MOTOR_SAMPLE ")
        for x in content.splitlines() if "PAPER_DEV_MOTOR_SAMPLE " in x
    ]
    following = []
    for sample in samples:
        tick = _positive_int(sample, "server_tick")
        if tick <= start_tick:
            continue
        if sample.get("world") != world or sample.get("player") != player:
            raise StopDevRejected("mixed Paper World/Player after STOP marker")
        following.append((tick, sample))
    if len(following) < 8:
        raise StopDevRejected("insufficient Paper post-clear callback samples")
    prior_tick = None
    prior_pose = None
    run: list[int] = []
    # Full bounded original interval; cannot select a lucky subset while
    # hiding earlier activity or gaps after the asserted STOP marker.
    for tick, row in following:
        if prior_tick is not None and tick != prior_tick + 1:
            raise StopDevRejected("gapped/repeated post-clear Paper tick")
        prior_tick = tick
        if any(row.get(key) != "false" for key in (
            "forward", "backward", "left", "right", "jump", "sneak", "sprint",
        )):
            run = []
            prior_pose = _position(row)
            continue
        pose = _position(row)
        if prior_pose is not None and pose == prior_pose:
            run.append(tick)
        else:
            run = []
        prior_pose = pose
        if len(run) >= 8:
            return run[-8], run[-1]
    raise StopDevRejected("no 8 consecutive motion-free Paper tick transitions")


class S49DevStopOwner:
    """One foreground S49 STOP owner; no network Action/reader of its own."""

    def __init__(self, session_id: str) -> None:
        self.session_id = _id("session_id", session_id)
        self.stop_id: str | None = None
        self.active_action_id: str | None = None
        self.clear_action_id: str | None = None
        self.clear_ack_seq: int | None = None
        self.ack: StopDevAck | None = None
        self.failed = False

    @property
    def requested(self) -> bool:
        return self.stop_id is not None

    @property
    def allows_action(self) -> bool:
        return not self.requested and not self.failed

    def request(self, stop_id: str, *, active_action_id: str | None = None) -> None:
        if self.requested or self.failed:
            raise StopDevRejected("STOP already latched, no duplicate owner request")
        self.stop_id = _id("stop_id", stop_id)
        if active_action_id is not None:
            self.active_action_id = _id("active_action_id", active_action_id)

    def accept_clear(
        self, receipt: MineflayerEffectResult, *, clear_action_id: str,
    ) -> None:
        if not self.requested or self.failed or self.clear_action_id is not None:
            raise StopDevRejected("STOP clear already consumed or not requested")
        self.clear_action_id = _id("clear_action_id", clear_action_id)
        if (
            not isinstance(receipt, MineflayerEffectResult)
            or receipt.session_id != self.session_id
            or receipt.action_id != self.clear_action_id
            or receipt.effect != "clear_controls"
            or receipt.result != "applied"
        ):
            self.failed = True
            raise StopDevRejected("no matching acknowledged original S49 clear")
        self.clear_ack_seq = receipt.seq

    def finalize(
        self, paper_log: str, *, marker_id: str, world: str, player: str,
    ) -> StopDevAck:
        if (
            not self.requested or self.failed or self.ack is not None
            or self.clear_ack_seq is None or self.clear_action_id is None
        ):
            raise StopDevRejected("STOP cannot ACK without original clear")
        try:
            first, last = paper_stopped_after_marker(
                paper_log, marker_id=marker_id, world=world, player=player,
            )
        except StopDevRejected:
            self.failed = True
            raise
        self.ack = StopDevAck(
            self.stop_id, self.session_id, self.active_action_id,
            self.clear_action_id, self.clear_ack_seq, marker_id,
            world, player, first, last,
        )
        return self.ack
