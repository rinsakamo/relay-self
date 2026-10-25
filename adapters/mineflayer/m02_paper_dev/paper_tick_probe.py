"""#150 T1 offline reader of opt-in Paper tick callback samples.

This reader does not authenticate a server log, align Mineflayer's physics
clock, attest L0 checks, or authorize TPS changes. It intentionally cannot
construct the T0 rate-policy TickWindow or an S49 action outcome.
"""
from __future__ import annotations

from dataclasses import dataclass


class PaperTickProbeRejected(ValueError):
    """Paper's passive callback sequence is incomplete or out of scope."""


_PREFIX = "PAPER_DEV_TIME_SAMPLE "
_FIELDS = frozenset({
    "index", "server_tick", "world_full_time", "wall_nanos", "world",
    "player", "source", "l0_checked", "action_bound",
})
_SOURCE = "PAPER_SCHEDULER_CALLBACK_ONLY"


@dataclass(frozen=True, slots=True)
class PaperTickSample:
    index: int
    server_tick: int
    world_full_time: int
    wall_nanos: int
    world: str
    player: str


@dataclass(frozen=True, slots=True)
class PassivePaperTickTrace:
    samples: tuple[PaperTickSample, ...]
    effective_tps: float
    source_class: str = _SOURCE
    l0_checked: bool = False
    action_bound: bool = False
    qualified: bool = False

    @property
    def paper_ticks(self) -> tuple[int, ...]:
        return tuple(x.server_tick for x in self.samples)


def _positive_integer(fields: dict[str, str], key: str, *, allow_zero: bool = True) -> int:
    raw = fields[key]
    if not raw.isascii() or not raw.isdecimal():
        raise PaperTickProbeRejected(f"invalid {key}")
    number = int(raw)
    if number < (0 if allow_zero else 1) or number > 2**63 - 1:
        raise PaperTickProbeRejected(f"out-of-range {key}")
    return number


def read_passive_paper_ticks(
    content: str, *, expected_world: str, expected_player: str,
    max_rows: int = 256,
) -> PassivePaperTickTrace:
    """Read consecutive callback *samples*, never evidence of an L0 pass.

    Server/plugin provenance must be independently proven by the caller.
    The first and last sample do not attest unobserved bounding intervals.
    """
    if (not isinstance(content, str) or not isinstance(expected_world, str)
        or not expected_world.strip() or not isinstance(expected_player, str)
        or not expected_player.strip() or type(max_rows) is not int
        or not 2 <= max_rows <= 256):
        raise PaperTickProbeRejected("invalid passive tick probe scope")
    rows: list[PaperTickSample] = []
    for line in content.splitlines():
        if _PREFIX not in line:
            continue
        if line.count(_PREFIX) != 1:
            raise PaperTickProbeRejected("ambiguous tick row prefix")
        suffix = line.split(_PREFIX, 1)[1]
        fields: dict[str, str] = {}
        for pair in suffix.split():
            if pair.count("=") != 1:
                raise PaperTickProbeRejected("malformed sample field")
            key, value = pair.split("=", 1)
            if key in fields or not value:
                raise PaperTickProbeRejected("duplicate/empty sample field")
            fields[key] = value
        if fields.keys() != _FIELDS:
            raise PaperTickProbeRejected("missing/extra tick sample field")
        if (fields["source"] != _SOURCE or fields["l0_checked"] != "false"
            or fields["action_bound"] != "false"
            or fields["world"] != expected_world
            or fields["player"] != expected_player):
            raise PaperTickProbeRejected("foreign or misrepresented passive sample")
        rows.append(PaperTickSample(
            _positive_integer(fields, "index", allow_zero=False),
            _positive_integer(fields, "server_tick"),
            _positive_integer(fields, "world_full_time"),
            _positive_integer(fields, "wall_nanos"),
            fields["world"], fields["player"],
        ))
        if len(rows) > max_rows:
            raise PaperTickProbeRejected("tick probe exceeds bounded scope")
    if len(rows) < 2:
        raise PaperTickProbeRejected("two native callback samples required")
    for previous, current in zip(rows, rows[1:]):
        if not (current.index == previous.index + 1
                and current.server_tick == previous.server_tick + 1
                and current.world_full_time == previous.world_full_time + 1
                and current.wall_nanos > previous.wall_nanos):
            raise PaperTickProbeRejected("gapped, repeated or reordered tick samples")
    if rows[0].index != 1:
        raise PaperTickProbeRejected("first tick row absent; partial probe")
    elapsed = rows[-1].wall_nanos - rows[0].wall_nanos
    return PassivePaperTickTrace(
        tuple(rows), (len(rows) - 1) * 1_000_000_000 / elapsed,
    )
