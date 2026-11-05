"""Prospective DEV P1 model interoception from pre-REST Paper tick callbacks.

The original P1 *evaluator* is loaded from an exact, separate Git checkout.
Only a complete observed prefix through a one-shot native Paper FIGHT event
can inform the existing S49 L0 request. No future REST interval or result is
read. Slower recovery is an experimental PROFILE, not the original default
or evidence of Minecraft-native fatigue.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from adapters.mineflayer.s49_p1_paper_dev import (
    S49P1SourceRejected,
    _float,
    _int,
    _rows,
)
from tools.bug0_p1_sensor_threshold import sensitivity

P1_EXACT_COMMIT = "0ab76b4e46efd914877e543a65de58b6cfc71326"
EXPERIMENTAL_WAIT_RECOVERY = 0.002
EXPERIMENTAL_SENSOR_THRESHOLD = 0.05
SOURCE_KIND = "PAPER_PRE_DECISION_CALLBACK_P1_VIRTUAL_SENSOR_DEV"


def _p1_source(p1_checkout: Path) -> tuple[str, str]:
    """Return frozen git commit + original module SHA, rejecting shadowing."""
    if not p1_checkout.is_absolute() or not p1_checkout.is_dir():
        raise S49P1SourceRejected("absolute existing pinned P1 checkout required")
    head = subprocess.run(
        ["git", "-C", str(p1_checkout), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if head != P1_EXACT_COMMIT:
        raise S49P1SourceRejected("wrong original P1 commit")
    path = p1_checkout / "experiments" / "fatigue_p1.py"
    if not path.is_file() or path.is_symlink():
        raise S49P1SourceRejected("original P1 module not an ordinary file")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    sys.path.insert(0, str(p1_checkout))
    from experiments import fatigue_p1 as p1

    if Path(p1.__file__).resolve() != path.resolve():
        raise S49P1SourceRejected("shadowed original P1 module")
    return head, digest


def _prefix(log: str, *, nonce: str) -> dict[str, Any]:
    """Read all consecutive callback ticks already logged, never invent WAIT."""
    if not re.fullmatch(r"[a-z0-9]{12,32}", nonce):
        raise S49P1SourceRejected("invalid live source nonce")
    if (_rows(log, "SOURCE_FAULT") or _rows(log, "REST")
            or _rows(log, "CHOICE") or _rows(log, "STOP")):
        raise S49P1SourceRejected("stale/post-REST Paper source is not prospective")
    starts = _rows(log, "START")
    fights = _rows(log, "FIGHT")
    ticks = _rows(log, "TICK")
    if len(starts) != 1 or len(fights) != 1 or not 4 <= len(ticks) <= 480:
        raise S49P1SourceRejected("missing or duplicated live Paper FIGHT prefix")
    start, fight = starts[0], fights[0]
    world = start.get("world")
    player = start.get("player")
    if (
        not re.fullmatch(r"[0-9a-f-]{36}", world or "")
        or not re.fullmatch(r"[0-9a-f-]{36}", player or "")
        or not re.fullmatch(r"[0-9a-f-]{36}", fight.get("target", ""))
        or fight.get("attacker") != player
        or _float(fight, "damage") <= 0
        or any(row.get("world") != world or row.get("nonce") != nonce
               for row in (start, fight, *ticks))
        or start.get("coverage") != "SERVER_TICK_CALLBACK_NOT_FULL_TICK"
    ):
        raise S49P1SourceRejected("foreign original Paper player/World prefix")
    fight_tick = _int(fight, "tick")
    begun = _int(start, "tick")
    last = begun
    source_rows = []
    for index, row in enumerate(ticks, 1):
        tick = _int(row, "tick")
        if tick != last + 1 or _int(row, "index") != index:
            raise S49P1SourceRejected("gapped, duplicated or reordered Paper tick")
        last = tick
        counters = {k: _int(row, k) for k in (
            "move_events", "fight_events", "swing_events",
            "interact_events", "velocity_events", "teleport_events",
            "player_damage_events",
        )}
        if (
            any(v > 10000 for v in counters.values())
            or _float(row, "move_distance") != 0
            or any(row.get(k) not in ("true", "false")
                   for k in ("sprint", "sneak", "swimming"))
            or any(row[k] == "true" for k in ("sprint", "sneak", "swimming"))
            or not all(math.isfinite(_float(row, ax)) for ax in ("x", "y", "z"))
        ):
            raise S49P1SourceRejected("non-stationary/nonfinite model source prefix")
        source_rows.append((tick, counters))
    fights_in_callbacks = [
        (tick, counters) for tick, counters in source_rows
        if counters["fight_events"]
    ]
    if (
        len(fights_in_callbacks) != 1
        or fights_in_callbacks[0][1]["fight_events"] != 1
        or not fight_tick <= fights_in_callbacks[0][0] <= fight_tick + 1
        or last < fights_in_callbacks[0][0] + 2
    ):
        raise S49P1SourceRejected("missing/ambiguous FIGHT callback")
    # Only allow a single FIGHT callback with its own swing; afterwards
    # any motion/attack/swings/interacts/velocity/teleports/damage stops
    # this preview. Silence is at most DEV candidate WAIT.
    fight_callback = fights_in_callbacks[0][0]
    for tick, counters in source_rows:
        if tick == fight_callback:
            if (
                counters["move_events"] or counters["interact_events"]
                or counters["velocity_events"] or counters["teleport_events"]
                or counters["player_damage_events"]
                or counters["swing_events"] > 1
            ):
                raise S49P1SourceRejected("mixed/unsupported FIGHT activity")
        elif tick > fight_callback and any(counters.values()):
            raise S49P1SourceRejected("post-FIGHT activity cannot be model WAIT")
    return {
        "nonce": nonce,
        "paper_world": world,
        "paper_player_uuid": player,
        "source_start_tick": begun,
        "fight_event_tick": fight_tick,
        "fight_callback_tick": fight_callback,
        "source_last_tick": last,
        "callback_rows": len(source_rows),
        "fight_callback_count": 1,
        "prefix_rows": source_rows,
    }


def prospective_request(
    paper_log: str, *, nonce: str, session_id: str, probe_seq: int,
    p1_checkout: Path, sensor_policy: str = "nominal",
    experimental_wait_rate: float = EXPERIMENTAL_WAIT_RECOVERY,
) -> dict[str, Any]:
    """Use only a pre-decision Paper prefix to decide an L0 REST *request*."""
    if (
        not isinstance(session_id, str) or not session_id
        or session_id.replace("-", "")[:20] != nonce
        or type(probe_seq) is not int or probe_seq < 1
        or sensor_policy not in ("nominal", "margin")
        or type(experimental_wait_rate) is not float
        or experimental_wait_rate not in (0.001, EXPERIMENTAL_WAIT_RECOVERY)
    ):
        raise S49P1SourceRejected("foreign S49 native probe/session/policy")
    source = _prefix(paper_log, nonce=nonce)
    original_head, digest = _p1_source(p1_checkout)
    from experiments.fatigue_p1 import (
        FatigueFrame,
        FatigueProfile,
        FatigueSensor,
        Rate,
        advance,
        initial_state,
        observe,
    )

    # This alternate RATE is an explicit DEV hypothesis, not a silent change
    # to the original P1 default (0.10/tick).
    default = FatigueProfile(enabled=True)
    experimental = FatigueProfile(
        enabled=True,
        wait_recovery_per_world_tick=Rate(experimental_wait_rate),
    )
    if default.wait_recovery_per_world_tick.value != 0.1:
        raise S49P1SourceRejected("pinned P1 default recovery assumption changed")

    fight_callback = source["fight_callback_tick"]
    after_fight = [
        (tick, counts) for tick, counts in source["prefix_rows"]
        if tick >= fight_callback
    ]
    states = []
    for profile in (default, experimental):
        state = initial_state(profile, session_id, world_tick=fight_callback - 1)
        total_recovered = 0.0
        for tick, counts in after_fight:
            activity = "FIGHT" if counts["fight_events"] else "WAIT"
            frame = FatigueFrame(
                session_id, tick, activity,
                observed_fight_events=counts["fight_events"],
            )
            result = advance(profile, state, frame)
            state = result.after
            total_recovered += result.recovered
        states.append((profile, state, total_recovered))
    _, default_state, default_recovered = states[0]
    experimental_profile, experimental_state, experimental_recovered = states[1]
    sensor = FatigueSensor(quantum=0.01)
    observation = observe(experimental_profile, experimental_state, sensor)
    default_observation = observe(default, default_state, sensor)
    policy = sensitivity(
        float(observation.reading), quantum=0.01,
        threshold=EXPERIMENTAL_SENSOR_THRESHOLD, margin=0.025,
    )
    request = (
        policy.nominal_rest if sensor_policy == "nominal"
        else policy.safety_margin_rest
    ) and experimental_state.fatigue > 0
    return {
        "source_kind": SOURCE_KIND,
        "original_s49_session_id": session_id,
        "native_probe_seq": probe_seq,
        "paper_source_uuid": source["paper_world"],
        "paper_source_player_uuid": source["paper_player_uuid"],
        "paper_source_start_tick": source["source_start_tick"],
        "paper_fight_event_tick": source["fight_event_tick"],
        "paper_fight_callback_tick": fight_callback,
        "source_as_of_tick": source["source_last_tick"],
        "candidate_tick_rows_seen_before_decision": source["callback_rows"],
        "source_post_rest_lookahead_used": False,
        "original_p1_commit": original_head,
        "original_p1_module_sha256": digest,
        "original_p1_default_profile_sha256": default.sha256,
        "experimental_p1_profile_sha256": experimental_profile.sha256,
        "original_default_wait_recovery_per_tick": 0.1,
        "experimental_wait_recovery_per_tick": experimental_wait_rate,
        "model_default_fatigue_pre_decision": default_state.fatigue,
        "model_experimental_fatigue_pre_decision": experimental_state.fatigue,
        "model_default_recovery_pre_decision": default_recovered,
        "model_experimental_recovery_pre_decision": experimental_recovered,
        "model_experimental_sensor_reading": observation.reading,
        "model_default_sensor_reading": default_observation.reading,
        "experimental_sensor_threshold": EXPERIMENTAL_SENSOR_THRESHOLD,
        "sensitivity": policy.to_dict(),
        "sensor_decision_policy": sensor_policy,
        "nominal_rest_shadow": policy.nominal_rest,
        "uncertainty_guard_rest_shadow": policy.uncertainty_guard_rest,
        "safety_margin_rest_shadow": policy.safety_margin_rest,
        "request_rest": request,
        "reason": (
            "MODEL_FATIGUE_ABOVE_THRESHOLD_DEV_PROFILE"
            if request else "MODEL_FATIGUE_BELOW_MARGIN_OR_THRESHOLD"
        ),
        "original_P1_runtime_state_installed": False,
        "p1_real_fatigue_attested": False,
        "full_tick_activity_independently_attested": False,
        "r_source_attested": False,
        "new_action_issuer": False,
        "m_energy_credit": 0,
        "qualification_go": False,
        "science_run": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-log", type=Path, required=True)
    parser.add_argument("--p1-checkout", type=Path, required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--probe-seq", type=int, required=True)
    parser.add_argument("--experimental-wait-rate", type=float,
                        choices=[0.001, 0.002], default=0.002)
    parser.add_argument("--sensor-policy", choices=["nominal", "margin"],
                        default="nominal")
    args = parser.parse_args()
    nonce = args.session_id.replace("-", "")[:20]
    output = prospective_request(
        args.paper_log.read_text(encoding="utf-8"),
        nonce=nonce, session_id=args.session_id, probe_seq=args.probe_seq,
        p1_checkout=args.p1_checkout.resolve(),
        sensor_policy=args.sensor_policy,
        experimental_wait_rate=args.experimental_wait_rate,
    )
    print(json.dumps(output, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
