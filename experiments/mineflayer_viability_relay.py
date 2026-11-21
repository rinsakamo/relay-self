from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from enum import Enum

MINEFLAYER_REPOSITORY = "PrismarineJS/mineflayer"
MINEFLAYER_REVISION = "91204b2a034f0663b39814771e236bcb7c8f26c8"


class MineflayerEvent(str, Enum):
    HEALTH = "health"
    BREATH = "breath"
    DEATH = "death"
    RESPAWN = "respawn"
    ENTITY_HURT = "entityHurt"


@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class HurtSource:
    entity_id: int
    position: Vec3


@dataclass(frozen=True)
class MineflayerObservation:
    tick: int
    health: float
    food: float
    oxygen_level: float
    position: Vec3
    events: tuple[MineflayerEvent, ...] = ()
    hurt_source: HurtSource | None = None

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError("tick must be non-negative")
        for name, value in (
            ("health", self.health),
            ("food", self.food),
            ("oxygen_level", self.oxygen_level),
        ):
            if value < 0:
                raise ValueError(f"{name} must be non-negative")

        has_hurt_event = MineflayerEvent.ENTITY_HURT in self.events
        if has_hurt_event != (self.hurt_source is not None):
            raise ValueError("entityHurt event and hurt_source must appear together")


@dataclass(frozen=True)
class ViabilityGradient:
    tick: int
    field: str
    delta: float


def health_gradient(
    previous: MineflayerObservation,
    current: MineflayerObservation,
) -> ViabilityGradient:
    if current.tick <= previous.tick:
        raise ValueError("current tick must follow previous tick")
    return ViabilityGradient(
        tick=current.tick,
        field="bot.health",
        delta=current.health - previous.health,
    )


def _observation_dict(frame: MineflayerObservation) -> dict[str, object]:
    hurt_source: dict[str, object] | None = None
    if frame.hurt_source is not None:
        hurt_source = {
            "entityId": frame.hurt_source.entity_id,
            "position": asdict(frame.hurt_source.position),
        }

    return {
        "tick": frame.tick,
        "health": frame.health,
        "food": frame.food,
        "oxygenLevel": frame.oxygen_level,
        "position": asdict(frame.position),
        "events": [event.value for event in frame.events],
        "hurtSource": hurt_source,
    }


def compile_cognition_payload(
    frames: tuple[MineflayerObservation, ...],
    *,
    include_gradient: bool,
) -> dict[str, object]:
    if not frames:
        raise ValueError("frames must not be empty")

    rows: list[dict[str, object]] = []
    previous: MineflayerObservation | None = None
    for frame in frames:
        row: dict[str, object] = {"observation": _observation_dict(frame)}
        if include_gradient and previous is not None:
            row["valueGradient"] = asdict(health_gradient(previous, frame))
        rows.append(row)
        previous = frame

    return {
        "source": {
            "repository": MINEFLAYER_REPOSITORY,
            "revision": MINEFLAYER_REVISION,
        },
        "frames": rows,
    }


def respawn_trace() -> tuple[MineflayerObservation, ...]:
    source = HurtSource(entity_id=41, position=Vec3(2.0, 64.0, 0.0))
    return (
        MineflayerObservation(
            tick=0,
            health=20.0,
            food=20.0,
            oxygen_level=20.0,
            position=Vec3(0.0, 64.0, 0.0),
        ),
        MineflayerObservation(
            tick=1,
            health=12.0,
            food=20.0,
            oxygen_level=20.0,
            position=Vec3(0.0, 64.0, 0.0),
            events=(MineflayerEvent.HEALTH, MineflayerEvent.ENTITY_HURT),
            hurt_source=source,
        ),
        MineflayerObservation(
            tick=2,
            health=0.0,
            food=20.0,
            oxygen_level=20.0,
            position=Vec3(0.0, 64.0, 0.0),
            events=(
                MineflayerEvent.HEALTH,
                MineflayerEvent.ENTITY_HURT,
                MineflayerEvent.DEATH,
            ),
            hurt_source=source,
        ),
        MineflayerObservation(
            tick=3,
            health=20.0,
            food=20.0,
            oxygen_level=20.0,
            position=Vec3(10.0, 64.0, 10.0),
            events=(MineflayerEvent.RESPAWN, MineflayerEvent.HEALTH),
        ),
    )


def build_ablation() -> dict[str, object]:
    frames = respawn_trace()
    return {
        "observationsOnly": compile_cognition_payload(frames, include_gradient=False),
        "withHealthGradient": compile_cognition_payload(frames, include_gradient=True),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit a Mineflayer-spec synthetic viability-relay fixture."
    )
    parser.add_argument(
        "--condition",
        choices=("observations", "gradient", "both"),
        default="both",
    )
    args = parser.parse_args()

    frames = respawn_trace()
    if args.condition == "observations":
        payload = compile_cognition_payload(frames, include_gradient=False)
    elif args.condition == "gradient":
        payload = compile_cognition_payload(frames, include_gradient=True)
    else:
        payload = build_ablation()

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
