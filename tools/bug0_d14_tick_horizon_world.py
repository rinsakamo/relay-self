"""D14 one-World 10000 Paper-tick observation after existing original S49.

No invented zombie death, no extra S49 Actions, no model calls or learning.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
from functools import partial
from pathlib import Path

from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.s31a_real_server_ci import _correlated_observe
from tools.bug0_d4_oneworld import run
from tools.bug0_d6_multigen_world import _uuid
from tools.bug0_d6_natural_move_world import source_qualified_natural_move
from tools.bug0_d7f_natural_eat import after_real_natural_pickup_eat
from tools.bug0_d12_third_intent_rearm_world import second_food_then_third_rearm


class D14HorizonRejected(RuntimeError):
    """Missing original Paper tick, source scope, or single Self owner."""


def parse_endurance_marker(log: str, marker: str) -> str | None:
    found = [line for line in log.splitlines() if marker in line]
    if len(found) > 1:
        raise D14HorizonRejected("DUPLICATED_WORLD_TICK_MARKER")
    return found[0] if found else None


def _field(line: str, name: str) -> int:
    match = re.search(rf"(?:^| ){re.escape(name)}=(-?\d+)(?: |$)", line)
    if not match:
        raise D14HorizonRejected("MISSING_PAPER_FIELD_" + name)
    return int(match.group(1))



def qualified_early_terminal(start_line: str, terminal_line: str) -> dict:
    """Accept a genuine Paper death/disconnect as an EARLY stop, never 10k PASS."""
    start_tick = _field(start_line, "start_tick")
    tick = _field(terminal_line, "observed_tick")
    reason = terminal_line.split(" reason=", 1)[-1].split()[0]
    if (
        _uuid(start_line, "world") != _uuid(terminal_line, "world")
        or _field(terminal_line, "start_tick") != start_tick
        or _field(terminal_line, "scheduled_stop_tick") != start_tick + 10000
        or _field(terminal_line, "elapsed_ticks") != tick - start_tick
        or not start_tick <= tick < start_tick + 10000
        or reason not in ("SELF_DIED", "SELF_DISCONNECTED", "WORLD_SCOPE_LOST")
        or "horizon_reached=false" not in terminal_line
    ):
        raise D14HorizonRejected("INVALID_PAPER_EARLY_TERMINAL")
    return {
        "reason": reason,
        "world_uuid": _uuid(start_line, "world"),
        "start_tick": start_tick,
        "terminal_tick": tick,
        "elapsed_ticks": tick - start_tick,
        "source_original": terminal_line,
        "world_horizon_reached": False,
        "self_survived_to_horizon": False,
    }


async def observe_to_10000_world_ticks(
    session, server, owner: NormalSessionActionExecutor,
    report: dict, paper_log: Path, *,
    checkpoint_path: Path | None = None,
) -> None:
    """Bounded, incrementally parsed Paper event stream and optional native probes.

    The Paper tick log is the World clock. Native probes occur asynchronously,
    and are NEVER attributed to exactly the same tick as the Paper checkpoint.
    """
    if (
        os.environ.get("D14_10000_TICK_WORLD_ONLY") != "1"
        or report.get("d14_tick_horizon_optin") is not True
        or report.get("d14_tick_horizon_requested") != 10000
        or not isinstance(owner, NormalSessionActionExecutor)
        or owner.session_id != session.started.session_id
        or owner.supervisor.open_actions
    ):
        raise D14HorizonRejected("SINGLE_ORIGINAL_OWNER_AND_TICK_GRANT_REQUIRED")
    report["d14_tick_horizon_proven"] = False
    report["d14_stage"] = "WATCHING_WORLD_10000_TICKS"
    report["d14_self_continuous_action_policy_enabled"] = False
    report["d14_additional_native_actions"] = 0
    report["d14_heartbeat_observations"] = []
    report["d14_start_action_count"] = owner._count
    original_ids = frozenset(owner._dispatched)
    original_supervisor = owner.supervisor

    # Exclusive append-only derivative journal survives partial timeout or
    # runner cancellation, unlike the final full report saved on clean exit.
    if checkpoint_path is None:
        raise D14HorizonRejected("EXCLUSIVE_D14_CHECKPOINT_PATH_REQUIRED")
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    offset = 0
    pending = b""
    seen_ticks: set[int] = set()
    start_line: str | None = None
    final_line: str | None = None
    terminal_line: str | None = None
    started = time.monotonic()

    with checkpoint_path.open("x", encoding="utf8") as journal:
        def record(event: str, original: str, **extra) -> None:
            journal.write(json.dumps({
                "source": "D14_PAPER_WORLD_TICK_DERIVATIVE_V1",
                "event": event,
                "paper_original": original, **extra,
            }, ensure_ascii=False, sort_keys=True) + "\n")
            journal.flush()
            os.fsync(journal.fileno())

        while time.monotonic() - started < 900:
            if server.returncode is not None:
                raise D14HorizonRejected("PAPER_SERVER_EXITED_BEFORE_10000_TICKS")
            if paper_log.is_file():
                with paper_log.open("rb") as stream:
                    stream.seek(0, 2)
                    if stream.tell() < offset:
                        raise D14HorizonRejected("PAPER_ORIGINAL_LOG_TRUNCATED_IN_PLACE")
                    stream.seek(offset)
                    chunk = stream.read()
                    offset = stream.tell()
            else:
                chunk = b""
            if chunk:
                lines = (pending + chunk).split(b"\n")
                pending = lines.pop()
                latest_new_sample = None
                for source in lines:
                    line = source.decode("utf8", errors="replace").rstrip("\r")
                    if "RSELF_RESPAWN_FAULT" in line or "RSELF_NATURAL_DROP_FAULT" in line:
                        raise D14HorizonRejected("WORLD_SOURCE_FAULT")
                    if "RSELF_ENDURANCE_START world=" in line:
                        if start_line is not None:
                            raise D14HorizonRejected("DUPLICATED_WORLD_TICK_START")
                        start_line = line
                        record("START", line)
                    elif "RSELF_ENDURANCE_SAMPLE world=" in line:
                        if start_line is None:
                            raise D14HorizonRejected("SAMPLE_BEFORE_WORLD_HORIZON")
                        tick = _field(line, "tick")
                        elapsed = _field(line, "elapsed_ticks")
                        if (
                            tick in seen_ticks
                            or _uuid(line, "world") != _uuid(start_line, "world")
                            or elapsed != tick - _field(start_line, "start_tick")
                            or not 0 < elapsed < 10000
                            or elapsed % 200 != 0
                            or len(seen_ticks) + 1 != elapsed // 200
                        ):
                            raise D14HorizonRejected("PAPER_WORLD_HEARTBEAT_BAD_TICK")
                        seen_ticks.add(tick)
                        latest_new_sample = (line, tick, elapsed)
                        record("SAMPLE", line)
                    elif "RSELF_ENDURANCE_TERMINAL world=" in line:
                        if terminal_line is not None or start_line is None:
                            raise D14HorizonRejected("DUPLICATED_OR_UNSCOPED_TERMINAL")
                        terminal_line = line
                        record("TERMINAL", line)
                    elif "RSELF_ENDURANCE_LIMIT world=" in line:
                        if final_line is not None or start_line is None:
                            raise D14HorizonRejected("DUPLICATED_OR_UNSCOPED_LIMIT")
                        final_line = line
                        record("LIMIT", line)

                # Check death/disconnect BEFORE attempting to request a stale
                # native readback. Never wait for a limit erased by cleanup().
                if terminal_line is not None:
                    report["d14_early_termination"] = qualified_early_terminal(
                        start_line, terminal_line,
                    )
                    report["d14_stage"] = "EARLY_" + report[
                        "d14_early_termination"
                    ]["reason"]
                    raise D14HorizonRejected("EARLY_WORLD_TERMINAL_" + report[
                        "d14_early_termination"
                    ]["reason"])

                # A native probe is at most ONCE per batch of Paper samples.
                # No 49-probe backlog on a slow consumer or after LIMIT.
                if latest_new_sample is not None and final_line is None:
                    paper_line, paper_tick, elapsed = latest_new_sample
                    try:
                        view = await asyncio.wait_for(
                            _correlated_observe(
                                session, f"d14-world-tick-{paper_tick}-passive",
                            ),
                            timeout=9,
                        )
                    except Exception as exc:
                        # Do not keep waiting for 10000 ticks after a dead
                        # session. The Paper terminal will still be in originals.
                        report["d14_native_probe_error"] = (
                            f"{type(exc).__name__}: {exc}"
                        )
                        raise D14HorizonRejected("NATIVE_PROBE_NOT_AVAILABLE") from exc
                    if (
                        view.session_id != owner.session_id
                        or view.snapshot.health <= 0
                        or owner.supervisor.open_actions
                        or owner.supervisor is not original_supervisor
                        or owner._dispatched != original_ids
                        or owner._count != report["d14_start_action_count"]
                    ):
                        raise D14HorizonRejected("ORIGINAL_SELF_SOURCE_OR_ACTION_CHANGED")
                    sample = {
                        "paper_tick": paper_tick,
                        "elapsed_world_ticks": elapsed,
                        "generation": _field(paper_line, "generation"),
                        "native_seq": view.seq,
                        "native_request_id": view.request_id,
                        "native_food": view.snapshot.food,
                        "native_health": view.snapshot.health,
                        "native_oxygen": view.snapshot.oxygen_level,
                        "native_inventory_rotten": sum(
                            x.count for x in view.snapshot.inventory
                            if x.name == "rotten_flesh"
                        ),
                        "clock_correlation": "ASYNCHRONOUS_NOT_SAME_TICK",
                    }
                    report["d14_heartbeat_observations"].append(sample)
                    record("NATIVE_READBACK", paper_line, observation=sample)

                if final_line is not None:
                    break
            await asyncio.sleep(0.8)

        if start_line is None or final_line is None:
            raise D14HorizonRejected("EXACT_10000_WORLD_TICK_END_NOT_OBSERVED")
        start_tick = _field(start_line, "start_tick")
        stop_tick = _field(start_line, "stop_tick")
        observed_tick = _field(final_line, "observed_tick")
        if (
            stop_tick != start_tick + 10000
            or _field(final_line, "elapsed_ticks") != 10000
            or observed_tick != stop_tick
            or _field(final_line, "start_tick") != start_tick
            or _field(final_line, "end_tick") != stop_tick
            or _uuid(start_line, "world") != _uuid(final_line, "world")
            or len(seen_ticks) != 49
            or "stop_new_spawns=true no_forced_death=true" not in final_line
            or owner._count != report["d14_start_action_count"]
            or owner._dispatched != original_ids
            or owner.supervisor.open_actions
        ):
            raise D14HorizonRejected("TICK_LIMIT_OR_OWNER_CHANGED")
        report["d14_tick_horizon"] = {
            "world_uuid": _uuid(start_line, "world"),
            "start_tick": start_tick,
            "end_tick": observed_tick,
            "world_ticks": 10000,
            "final_generation": _field(final_line, "generation"),
            "final_living": final_line.split(" living=")[1].split()[0],
            "periodic_source_samples": len(seen_ticks),
            "native_snapshots": len(report["d14_heartbeat_observations"]),
            "original_s49_action_count": owner._count,
            "native_new_actions_issued_by_horizon": 0,
            "source_original_start": start_line,
            "source_original_end": final_line,
        }
        report["d14_tick_horizon_proven"] = True
        report["d14_stage"] = "PAPER_WORLD_TICK_LIMIT_REACHED"
        report["d14_l2_calls"] = 0
        report["d14_learning_updates"] = 0


def main() -> None:
    p = argparse.ArgumentParser()
    for arg in ("report", "server-log", "nonmotion-fence",
                "motion-fence", "d7-passive-controls"):
        p.add_argument("--" + arg, type=Path, required=True)
    args = p.parse_args()
    required = (
        "D14_10000_TICK_WORLD_ONLY",
        "D12_THIRD_INTENT_REARM_WORLD_ONLY",
        "D8_TWO_NATURAL_FOOD_CYCLES_WORLD_ONLY",
        "D7F_NATURAL_S49_S51_WORLD_ONLY",
        "D7_PASSIVE_CONTROLS_WORLD_ONLY",
    )
    if any(os.environ.get(key) != "1" for key in required):
        raise SystemExit("explicit D14 plus inherited D12/D8 DEV grants required")
    raise SystemExit(asyncio.run(run(
        args.report, args.server_log,
        post_respawn_dev=second_food_then_third_rearm,
        nonmotion_fence_path=args.nonmotion_fence,
        motion_fence_path=args.motion_fence,
        post_death_loot_move_dev=source_qualified_natural_move,
        d7_native_controls_path=args.d7_passive_controls,
        d7f_natural_eat_dev=after_real_natural_pickup_eat,
        d8_two_generation_food_dev=True,
        d12_third_intent_rearm_dev=True,
        d14_tick_endurance_dev=True,
        post_tick_horizon_dev=partial(
            observe_to_10000_world_ticks,
            checkpoint_path=args.report.with_name("d14_paper_world_events.jsonl"),
        ),
    )))


if __name__ == "__main__":
    main()
