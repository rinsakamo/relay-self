"""S51 genuine survival-mode Mineflayer EAT and nutrition witnesses.

This is an opt-in disposable Mojang 1.21.8 qualification. Explicit operator
first gives bread and hunger under Minecraft server authority. The Self then
chooses available food from native World evidence and exercises one already
ISSUED Action with distinct native equip/consume IDs. No automatic food gathering.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from adapters.mineflayer.eat_execution import IssuedEatingExecutor
from adapters.mineflayer.s31a_real_server_ci import (
    MINECRAFT_VERSION,
    MINEFLAYER_VERSION,
    S31ABlocked,
    _command,
    _correlated_observe,
    _fetch_official_server,
    _ready_server,
    _shutdown_server,
    _write_config,
)
from adapters.mineflayer.s34_native_world_cognition_ci import _new_session
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.eat_hunger import EatCursor, EatStatus
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


class S51PhysicalFailure(RuntimeError):
    """Real observed appetite, consumption or Action outcome was insufficient."""


def p(ref: str) -> Provenance:
    return Provenance("s51-explicit-operator", ref)


async def qualify(report_path: Path, server_log: Path) -> int:
    report: dict[str, Any] = {
        "milestone": "S51", "status": "BLOCKED", "stage": "START",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "world_food_supply": "OPERATOR_GIVEN",
        "food_acquisition_autonomous": False,
        "automatic_goal_selection": False,
        "real_model_calls": 0,
    }
    server = collector = session = temp = None
    rc = 2
    try:
        if os.environ.get("S51_REAL_SERVER_CI") != "1" or os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("explicit real-survival qualification environment required")
        temp = tempfile.TemporaryDirectory(prefix="relay-self-s51-")
        root = Path(temp.name)
        report["stage"] = "OFFICIAL_WORLD_PROVISION"
        report.update(await asyncio.to_thread(_fetch_official_server, root / "minecraft.jar"))
        _write_config(root)
        server, collector, _ = await _ready_server(
            root, root / "minecraft.jar", server_log,
        )
        session = await _new_session()
        sid = session.started.session_id
        report["session_id"] = sid
        report["stage"] = "EXTERNAL_SURVIVAL_AND_FOOD_STAGING"
        assert server.stdin is not None
        for cmd in (
            "gamemode survival RelaySelf",
            "give RelaySelf minecraft:bread 3",
            "effect give RelaySelf minecraft:hunger 25 20 true",
        ):
            _command(server, cmd)
            await server.stdin.drain()
        cursor = EatCursor(sid, hunger_threshold=14.0)
        before = choice = None
        for attempt in range(16):
            await asyncio.sleep(2)
            reading = await _correlated_observe(
                session, f"s51-hunger-native:{attempt:02d}",
            )
            if (
                reading.snapshot.food < 14.0
                and any(
                    item.name == "bread" and item.count > 0
                    for item in reading.snapshot.inventory
                )
            ):
                before = reading
                choice = cursor.choose(reading)
                break
        report["last_food_observed"] = reading.snapshot.food
        report["inventory_item_names"] = [
            item.name for item in reading.snapshot.inventory
        ]
        if (
            before is None
            or choice is None or choice.status is not EatStatus.CANDIDATE
            or choice.item_name != "bread"
        ):
            raise S51PhysicalFailure("actual native hunger + inventory gate not reached")
        _command(server, "effect clear RelaySelf minecraft:hunger")
        await server.stdin.drain()
        report["before"] = {
            "food": before.snapshot.food,
            "bread_count": sum(
                x.count for x in before.snapshot.inventory if x.name == "bread"
            ),
            "probe_seq": before.seq,
            "item_name": choice.item_name,
        }
        intent = IntentCommitment()
        intent.commit(
            "eat-when-hungry", objective="eat bread when hungry", at_ns=1,
            provenance=p("committed"),
        )
        skill = SkillExecution.start(
            "s51-eat-skill", skill_id="eat", intent_commitment=intent,
            at_ns=2, provenance=p("skill"),
        )
        proposed = ActionLifecycle.propose(
            "s51-eat-bread", skill_execution=skill, intent_commitment=intent,
            at_ns=3, provenance=p("proposed"),
        )
        authorized = proposed.authorize(
            at_ns=4, authority="s51-independent-eat-authorization",
            provenance=p("authorized"),
        )
        supervisor = ActionSupervisor()
        issued = supervisor.issue(
            authorized, at_ns=5, deadline_ns=200, provenance=p("issued"),
        )
        report["stage"] = "GENUINE_TWO_NATIVE_FOOD_EFFECTS"
        result = await IssuedEatingExecutor().execute(
            session, supervisor, issued, choice, before,
        )
        if (
            result.terminal.state is not ActionState.OUTCOME
            or result.outcome.food_after <= result.outcome.food_before
            or result.outcome.count_after >= result.outcome.count_before
            or supervisor.open_actions
        ):
            raise S51PhysicalFailure("no real independent native food+stock effects")
        report["after"] = {
            "food": result.outcome.food_after,
            "bread_count": result.outcome.count_after,
            "after_seq": result.outcome.after_probe_seq,
            "action_id": result.outcome.action_id,
            "terminal": result.terminal.state.value,
        }
        report["status"] = "PASS"
        report["classification"] = "REAL_SURVIVAL_HUNGER_EAT_NATIVE_FOOD_DELTA_QUALIFIED"
        report["stage"] = "CLOSED"
        rc = 0
    except (S31ABlocked, OSError) as exc:
        report["status"] = "BLOCKED"
        report["error"] = f"{type(exc).__name__}: {exc}"
        rc = 2
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(f"S51 FAIL: {exc}", file=sys.stderr)
        rc = 1
    finally:
        if session is not None:
            try:
                report["node_exit"] = await session.shutdown(timeout_s=10)
            except Exception as exc:
                report["node_cleanup_error"] = str(exc)
                await session.terminate()
        try:
            await _shutdown_server(server, collector)
        except Exception as exc:
            report["server_cleanup_error"] = str(exc)
            report["status"] = "FAIL"
            rc = 1
        if server is not None:
            report["server_exit"] = server.returncode
        if temp is not None:
            temp.cleanup()
        if report["status"] == "PASS" and report.get("server_exit") != 0:
            report["status"] = "FAIL"
            report["error"] = "Minecraft server teardown failed"
            rc = 1
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n")
        print("S51_REPORT="+json.dumps(report, sort_keys=True))
    return rc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    args = parser.parse_args()
    return asyncio.run(qualify(args.report, args.server_log))


if __name__ == "__main__":
    raise SystemExit(main())
