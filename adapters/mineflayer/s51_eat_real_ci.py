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
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.b0_ground_runner import acquire_staged_ground_flesh
from adapters.mineflayer.b0_rsee import (
    B0_CONFIRM,
    B0RSEEInputs,
    B0RSEERejected,
    verify_b0_rsee,
)
from adapters.mineflayer.eat_execution import IssuedEatingExecutor
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from adapters.mineflayer.s31a_real_server_ci import (
    BOT_USERNAME,
    MINECRAFT_VERSION,
    MINEFLAYER_VERSION,
    SERVER_HOST,
    SERVER_PORT,
    S31ABlocked,
    _await_spawn,
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


async def qualify(
    report_path: Path, server_log: Path, *,
    food_item: str = "bread", food_source: str = "inventory",
    rsee: B0RSEEInputs | None = None, confirmation: str | None = None,
    preflight_only: bool = False,
) -> int:
    if food_item not in ("bread", "rotten_flesh"):
        raise ValueError("only operator-staged bread or rotten_flesh allowed")
    if food_source not in ("inventory", "ground", "none"):
        raise ValueError("unsupported source")
    if food_source in ("ground", "none") and food_item != "rotten_flesh":
        raise ValueError("ground/none B0 mode requires rotten_flesh")
    count_field = "bread_count" if food_item == "bread" else "rotten_flesh_count"
    report: dict[str, Any] = {
        "milestone": "S51", "status": "BLOCKED", "stage": "START",
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "world_food_supply": (
            "OPERATOR_SUMMONED_SINGLE_GROUND_ITEM"
            if food_source == "ground" else "NO_FOOD_PROVISIONED"
            if food_source == "none" else "OPERATOR_GIVEN"
        ),
        "food_source": food_source,
        "ground_pickup": "NOT_RUN",
        "food_item": food_item,
        "zombie_drop_observed": False,
        "m_energy_credited": False,
        "food_acquisition_autonomous": False,
        "automatic_goal_selection": False,
        "real_model_calls": 0,
    }
    server = collector = session = temp = None
    rc = 2
    try:
        if os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("Node substitution forbidden")
        if preflight_only:
            # Safe preflight: no Java, Node, Minecraft, network or Action.
            # External RSEE source and World/Node bytes remain the authority.
            if food_item != "rotten_flesh" or rsee is None:
                raise S31ABlocked("B0 offline preflight requires full RSEE inputs")
            report["stage"] = "RSEE_READONLY_PREFLIGHT"
            report["rsee_preflight"] = await asyncio.to_thread(
                verify_b0_rsee, rsee,
            )
            report["status"] = "PASS"
            report["classification"] = "B0_RSEE_READONLY_PREFLIGHT_ONLY"
            report["physical_execution_authorized"] = False
            report["stage"] = "CLOSED"
            rc = 0
            return rc
        if os.environ.get("S51_REAL_SERVER_CI") != "1":
            raise S31ABlocked("explicit real-survival qualification environment required")
        if food_item == "rotten_flesh":
            # Not a permission token: physical permission is external and
            # per-run. Never use the legacy unqualified-download B0 path.
            if rsee is None or confirmation != B0_CONFIRM:
                raise S31ABlocked("B0 requires pinned RSEE and new one-shot operator confirmation")
            report["stage"] = "RSEE_ORIGINAL_READONLY_PRELAUNCH_GATE"
            attestation = await asyncio.to_thread(verify_b0_rsee, rsee)
            report["rsee_preflight"] = attestation
        elif rsee is not None:
            raise S31ABlocked("RSEE B0 mode only supports rotten_flesh")
        temp = tempfile.TemporaryDirectory(prefix="relay-self-s51-")
        root = Path(temp.name)
        if rsee is not None:
            report["stage"] = "RSEE_DISPOSABLE_SNAPSHOT_COPY"
            clone = root / "s31a-ephemeral"
            shutil.copytree(rsee.snapshot, clone)
            _write_config(root)
            props = root / "server.properties"
            props.write_text(
                props.read_text(encoding="utf-8") + "level-seed=575\n",
                encoding="utf-8",
            )
            report["stage"] = "RSEE_RECHECK_SOURCE_AND_CLONE_BEFORE_JAVA"
            copied = await asyncio.to_thread(
                verify_b0_rsee, rsee, snapshot_copy=clone,
            )
            if (
                copied["manifest_sha256"] != attestation["manifest_sha256"]
                or copied["initial_evidence_sha256"]
                != attestation["initial_evidence_sha256"]
            ):
                raise B0RSEERejected("disposable World differs from source")
            jar = rsee.jar
            report["world_source"] = "RSEE_583_PINNED_STOPPED_WORLD_CLONED"
        else:
            report["stage"] = "OFFICIAL_WORLD_PROVISION"
            report.update(await asyncio.to_thread(
                _fetch_official_server, root / "minecraft.jar",
            ))
            _write_config(root)
            jar = root / "minecraft.jar"
        server, collector, _ = await _ready_server(root, jar, server_log)
        if rsee is None:
            session = await _new_session()
        else:
            # Reuse the verified R-owned bridge and external npm root; S does
            # not patch the bridge or create a second dependency installation.
            old_root = os.environ.get("RELAYSELF_RSEE_NODE_RUNTIME_ROOT")
            os.environ["RELAYSELF_RSEE_NODE_RUNTIME_ROOT"] = str(
                rsee.node_runtime_root,
            )
            try:
                session = await MineflayerProcessSession.launch(
                    MineflayerLaunchConfig(
                        host=SERVER_HOST, port=SERVER_PORT,
                        username=BOT_USERNAME, version=MINECRAFT_VERSION,
                    ),
                    bridge_path=rsee.checkout / "adapters/mineflayer/bridge.mjs",
                    startup_timeout_s=12,
                )
            finally:
                if old_root is None:
                    os.environ.pop("RELAYSELF_RSEE_NODE_RUNTIME_ROOT", None)
                else:
                    os.environ["RELAYSELF_RSEE_NODE_RUNTIME_ROOT"] = old_root
            await _await_spawn(session)
        sid = session.started.session_id
        report["session_id"] = sid
        ledger = B0EnergyLedger(sid)
        report["metabolism"] = {
            "source": "M0_617_BYTE_IDENTICAL",
            "unit": "simulated_experimental_energy",
            "initial_energy": ledger.body.energy,
            "basal_cost_per_decision": ledger.config.basal_cost,
            "food_energy_per_verified_item": ledger.config.food_energy,
        }
        report["stage"] = "EXTERNAL_SURVIVAL_AND_FOOD_STAGING"
        assert server.stdin is not None
        _command(server, "gamemode survival RelaySelf")
        await server.stdin.drain()
        if food_source == "ground":
            report["stage"] = "ISSUED_SEEK_GROUND_PICKUP"
            report["ground_pickup"] = await acquire_staged_ground_flesh(
                session, server, energy_ledger=ledger,
            )
        elif food_source == "inventory":
            _command(server, f"give RelaySelf minecraft:{food_item} 3")
            await server.stdin.drain()
        if food_source == "none":
            # No food at all: the M0 body must irrevocably exhaust itself
            # under native observations, without inventing WAIT Actions.
            report["stage"] = "NATIVE_NO_FOOD_WAIT_TO_M0_TERMINAL"
            report["starvation_trace"] = []
            for epoch in range(64):
                probe = await _correlated_observe(
                    session, f"b0-nofood-native:{epoch:02d}",
                )
                coverage = probe.snapshot.nearby_entities_coverage
                if (
                    coverage.truncated
                    or coverage.candidate_count != len(probe.snapshot.nearby_entities)
                    or any(item.count > 0 for item in probe.snapshot.inventory)
                    or any(e.name == "item" for e in probe.snapshot.nearby_entities)
                ):
                    raise S51PhysicalFailure("no-food World condition not independently observed")
                decision = ledger.decide(probe)
                if decision.kind != "WAIT":
                    raise S51PhysicalFailure("no-food designed L0 did not WAIT")
                transition = ledger.step("WAIT")
                report["starvation_trace"].append({
                    "epoch": epoch,
                    "probe_seq": probe.seq,
                    "action": "WAIT_NON_ISSUANCE",
                    "issued_action": False,
                    "energy_after": transition.after.energy,
                    "metabolic_tick": transition.after.tick,
                    "terminal_now": transition.terminal_now,
                })
                if transition.terminal_now:
                    break
            else:
                raise S51PhysicalFailure("M0 terminal did not occur within 64 WAIT decisions")
            report["status"] = "PASS"
            report["classification"] = "B0_RSEE_NOFOOD_NATIVE_WAIT_TERMINAL_ENGINEERING_ONLY"
            report["m_energy_credited"] = False
            report["m_terminal"] = True
            report["metabolism_terminal"] = {
                "energy": ledger.body.energy,
                "tick": ledger.body.tick,
                "meals": ledger.body.meals,
                "irreversible": ledger.body.terminal,
            }
            report["next_l0"] = "DENIED_IRREVERSIBLE_STARVATION"
            report["stage"] = "CLOSED"
            rc = 0
        else:
            _command(server, "effect give RelaySelf minecraft:hunger 25 20 true")
            await server.stdin.drain()
            cursor = EatCursor(sid, hunger_threshold=14.0)
            before = choice = None
            for attempt in range(16):
                await asyncio.sleep(2)
                reading = await _correlated_observe(
                    session, f"s51-hunger-native:{attempt:02d}",
                )
                decision = ledger.decide(reading)
                if (
                    decision.kind == "EAT"
                    and decision.eat_choice is not None
                    and decision.eat_choice.item_name == food_item
                ):
                    before = reading
                    choice = cursor.choose(reading)
                    break
                if ledger.step("WAIT").terminal_now:
                    raise S51PhysicalFailure("M0 irreversible starvation during WAIT")
            report["last_food_observed"] = reading.snapshot.food
            report["inventory_item_names"] = [
                item.name for item in reading.snapshot.inventory
            ]
            if (
                before is None
                or choice is None or choice.status is not EatStatus.CANDIDATE
                or choice.item_name != food_item
            ):
                raise S51PhysicalFailure("actual native hunger + inventory gate not reached")
            _command(server, "effect clear RelaySelf minecraft:hunger")
            await server.stdin.drain()
            report["before"] = {
                "food": before.snapshot.food,
                "food_item": food_item,
                count_field: sum(
                    x.count for x in before.snapshot.inventory if x.name == food_item
                ),
                "probe_seq": before.seq,
                "item_name": choice.item_name,
            }
            intent = IntentCommitment()
            intent.commit(
                "eat-when-hungry", objective=f"eat {food_item} when hungry", at_ns=1,
                provenance=p("committed"),
            )
            skill = SkillExecution.start(
                "s51-eat-skill", skill_id="eat", intent_commitment=intent,
                at_ns=2, provenance=p("skill"),
            )
            proposed = ActionLifecycle.propose(
                f"s51-eat-{food_item}", skill_execution=skill, intent_commitment=intent,
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
            # Only the verified S51 terminal may supply M0 credit.
            transition = ledger.step("WAIT", eating=result)
            report["m_energy_credited"] = ledger.credit_count == 1
            report["metabolism_after_eat"] = {
                "energy": ledger.body.energy,
                "tick": ledger.body.tick,
                "meals": ledger.body.meals,
                "intake": transition.intake,
                "expenditure": transition.expenditure,
                "terminal": transition.terminal_now,
                "credited_action_id": result.outcome.action_id,
            }
            if transition.terminal_now:
                raise S51PhysicalFailure("M0 terminal after native consumption")
            fresh = await _correlated_observe(session, "b0-next-l0-native")
            next_l0 = ledger.decide(fresh)
            report["next_l0"] = {
                "probe_seq": next_l0.probe_seq,
                "kind": next_l0.kind,
                "energy_sensor_reading": next_l0.sensor_reading,
                "metabolic_tick": next_l0.body_tick,
                "issued_action": False,
            }
            report["after"] = {
                "food": result.outcome.food_after,
                "food_item": food_item,
                "item_count_delta": result.outcome.count_before - result.outcome.count_after,
                count_field: result.outcome.count_after,
                "after_seq": result.outcome.after_probe_seq,
                "action_id": result.outcome.action_id,
                "terminal": result.terminal.state.value,
            }
            report["status"] = "PASS"
            report["classification"] = (
                "B0_GROUND_EAT_M0_NEXT_L0_ENGINEERING_ONLY"
                if food_source == "ground"
                else "B0_STAGED_EAT_M0_NEXT_L0_ENGINEERING_ONLY"
                if food_item == "rotten_flesh"
                else "REAL_SURVIVAL_HUNGER_EAT_NATIVE_FOOD_DELTA_QUALIFIED"
            )
            report["stage"] = "CLOSED"
            rc = 0
    except (S31ABlocked, B0RSEERejected, OSError) as exc:
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
    parser.add_argument(
        "--food-item", choices=("bread", "rotten_flesh"), default="bread",
    )
    parser.add_argument(
        "--food-source", choices=("inventory", "ground", "none"), default="inventory",
    )
    parser.add_argument("--rsee-checkout", type=Path)
    parser.add_argument("--rsee-jar", type=Path)
    parser.add_argument("--rsee-snapshot", type=Path)
    parser.add_argument("--rsee-manifest", type=Path)
    parser.add_argument("--rsee-initial-evidence", type=Path)
    parser.add_argument("--rsee-node-runtime-root", type=Path)
    parser.add_argument("--rsee-eula-accepted", action="store_true")
    parser.add_argument(
        "--preflight-only", action="store_true",
        help="read-only pinned RSEE verification; never starts a World",
    )
    parser.add_argument("--confirm", help="operator acknowledgement; NOT a physical grant")
    args = parser.parse_args()
    fields = (
        args.rsee_checkout, args.rsee_jar, args.rsee_snapshot,
        args.rsee_manifest, args.rsee_initial_evidence,
        args.rsee_node_runtime_root,
    )
    # Partial RSEE values are rejected in qualify before any java/node.
    rsee = (
        B0RSEEInputs(*fields, eula_accepted=args.rsee_eula_accepted)
        if all(value is not None for value in fields) else None
    )
    return asyncio.run(qualify(
        args.report, args.server_log,
        food_item=args.food_item, food_source=args.food_source,
        rsee=rsee, confirmation=args.confirm,
        preflight_only=args.preflight_only,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
