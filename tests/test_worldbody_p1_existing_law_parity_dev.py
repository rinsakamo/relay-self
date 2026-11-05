"""Offline Java-vs-original-P1 numerical parity; no Paper, Self, or Action.

The original P1 Python module is deliberately NOT copied into this branch.
The separate CI checkout must be pinned to the exact #626 source commit.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

P1_HEAD = "0ab76b4e46efd914877e543a65de58b6cfc71326"
JAVA_SOURCE = Path(
    "adapters/mineflayer/worldbody_physics_dev/src/main/java/"
    "io/github/rinsakamo/worldbody/P1FatigueLaw.java"
)
CLASS = "io.github.rinsakamo.worldbody.P1FatigueLaw"


@pytest.fixture(scope="session")
def original_p1():
    root = Path(os.environ["P1_SOURCE_ROOT"]).resolve()
    sha = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    assert sha == P1_HEAD, "refuse different P1 owner source"
    file = root / "experiments/fatigue_p1.py"
    assert file.is_file(), "original P1 model absent"
    spec = importlib.util.spec_from_file_location("p1_original_pinned", file)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert module.FatigueProfile().move_per_block.value == 0.04
    assert module.FatigueProfile().wait_recovery_per_world_tick.value == 0.10
    return module


@pytest.fixture(scope="session")
def java_classes(tmp_path_factory):
    out = tmp_path_factory.mktemp("p1-java-classes")
    subprocess.run(
        ["javac", "--release", "21", "-d", str(out), str(JAVA_SOURCE)],
        check=True, text=True, capture_output=True,
    )
    return out


def scenario(*, enabled=True, initial=0.0, frames=(), capacity=1.0,
             move=(0.04, 1.0, 0.0), fight=(0.20, 1.0, 0.0),
             wait=(0.10, 1.0, 0.0), impairment=(0.70, 1.0, 0.0),
             min_eff=0.20, nominal=1.0, fight_eff=0.50,
             sensor=(1.0, 0.0, 0.1), start_tick=0):
    return locals()


def replay_java(classes, s):
    def rate(r):
        return ",".join(map(str, r))

    args = [
        "java", "-cp", str(classes), CLASS,
        str(s["enabled"]).lower(), str(s["capacity"]), str(s["initial"]),
        rate(s["move"]), rate(s["fight"]), rate(s["wait"]), rate(s["impairment"]),
        str(s["min_eff"]), str(s["nominal"]), str(s["fight_eff"]),
        *map(str, s["sensor"]), str(s["start_tick"]),
    ]
    for f in s["frames"]:
        args.append(",".join(map(str, (
            f[0], f[1], str(f[2]).lower(), f[3], *f[4:],
        ))))
    return subprocess.run(args, text=True, capture_output=True)


def replay_python(p1, s):
    cfg = p1.FatigueProfile(
        enabled=s["enabled"], initial=s["initial"], capacity=s["capacity"],
        move_per_block=p1.Rate(*s["move"]),
        fight_per_event=p1.Rate(*s["fight"]),
        wait_recovery_per_world_tick=p1.Rate(*s["wait"]),
        impairment_per_fraction=p1.Rate(*s["impairment"]),
        minimum_efficiency=s["min_eff"], nominal_move_limit_blocks=s["nominal"],
        minimum_fight_efficiency=s["fight_eff"],
    )
    sen = p1.FatigueSensor(*s["sensor"])
    state = p1.initial_state(cfg, "offline-p1-pinned", world_tick=s["start_tick"])
    rows = []
    for activity, distance, blocked, events, *tick_override in s["frames"]:
        tick = tick_override[0] if tick_override else state.world_tick + 1
        step = p1.advance(
            cfg, state,
            p1.FatigueFrame("offline-p1-pinned", tick, activity, distance, blocked, events),
        )
        state = step.after
        cap = step.capacity_after
        rows.append((
            state.world_tick, state.fatigue, step.accumulated, step.recovered,
            cap.efficiency, cap.max_move_blocks_per_world_tick,
            cap.fight_mechanically_possible, p1.observe(cfg, state, sen).reading,
        ))
    return rows


@pytest.mark.parametrize("s", [
    scenario(enabled=False, frames=(
        ("MOVE", 0.63, False, 0),
        ("FIGHT", 0.0, False, 1),
        ("WAIT", 0.0, False, 0),
    )),
    scenario(frames=(
        ("MOVE", 0.25, False, 0),
        ("MOVE", 1.0, False, 0),
        ("FIGHT", 0.0, False, 1),
        ("WAIT", 0.0, False, 0),
        ("WAIT", 0.0, False, 0),
    )),
    scenario(initial=0.8, frames=(
        ("MOVE", 0.0, True, 0),  # blocked MOVE must NOT recover
        ("MOVE", 0.25, True, 0),
        ("WAIT", 0.0, False, 0),
        ("FIGHT", 0.0, False, 0),
        ("FIGHT", 0.0, False, 1),
        ("WAIT", 0.0, False, 0),
    )),
    scenario(initial=0.98, frames=(
        ("FIGHT", 0.0, False, 1),
        *((("WAIT", 0.0, False, 0),) * 12),
    )),
    scenario(initial=1.0, impairment=(1.5, 1.0, 0.0),
             sensor=(0.0, 4.0, 0.05),
             frames=(("WAIT", 0.0, False, 0), ("WAIT", 0.0, False, 0))),
    scenario(initial=0.4, start_tick=40,
             move=(0.04, 2.0, 0.02), fight=(0.20, 0.7, 0.01),
             wait=(0.10, 0.5, 0.02), impairment=(0.70, 0.5, 0.1),
             min_eff=0.3, nominal=0.9, fight_eff=0.4,
             sensor=(0.83, 0.02, 0.01),
             frames=(
                 ("MOVE", 0.3, False, 0),
                 ("FIGHT", 0.0, False, 1),
                 ("WAIT", 0.0, False, 0),
             )),
])
def test_java_parity_with_exact_original_p1(original_p1, java_classes, s):
    actual = replay_java(java_classes, s)
    assert actual.returncode == 0, actual.stderr
    rows = [line.split(",") for line in actual.stdout.strip().splitlines()]
    expected = replay_python(original_p1, s)
    assert len(rows) == len(expected)
    for a, p in zip(rows, expected, strict=True):
        assert int(a[0]) == p[0]
        for i in (1, 2, 3, 4, 5, 7):
            assert float(a[i]) == pytest.approx(p[i], rel=1e-12, abs=1e-12)
        assert (a[6] == "true") is p[6]


@pytest.mark.parametrize("f", [
    ("WAIT", 0.0, True, 0),
    ("WAIT", 0.1, False, 0),
    ("MOVE", 0.0, False, 1),
    ("FIGHT", 0.1, False, 1),
    ("MOVE", -1.0, False, 0),
    ("MOVE", float("nan"), False, 0),
    ("REST", 0.0, False, 0),
    ("WAIT", 0.0, False, 0, 3),  # gap: expected World tick 1
])
def test_bad_shape_or_tick_fails_closed_on_both(original_p1, java_classes, f):
    s = scenario(initial=0.5, frames=(f,))
    with pytest.raises((original_p1.FatigueRejected, ValueError)):
        replay_python(original_p1, s)
    java = replay_java(java_classes, s)
    assert java.returncode != 0


def test_parity_does_not_claim_native_tick_source(original_p1):
    assert "Source authentication is outside this pure module" in (
        Path(original_p1.__file__).read_text()
    )
    assert "NOT wired into the Paper plugin" in JAVA_SOURCE.read_text()
    # A standalone replay frame is not an independently verified P1-B
    # SourceBoundTick or actual World recovery proof.
