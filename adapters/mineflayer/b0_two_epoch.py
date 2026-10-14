"""B0 bounded TWO-fixture ground survival episode; same real World and body.

Uses the existing S50/S51 issued Action owners and unmodified M0 mechanics.
Fixtures and simulated hunger are operator-controlled; not autonomous food
supply, native pickup-event authentication, learning, or scientific evidence.
There is no retry of an uncertain Action or physical session here.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path
from typing import Any

from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.b0_ground_foraging import GroundRejected
from adapters.mineflayer.b0_ground_runner import acquire_staged_ground_flesh
from adapters.mineflayer.b1_local_adaptation import B1LocalCandidate
from adapters.mineflayer.eat_execution import IssuedEatingExecutor
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.eat_hunger import EatCursor, EatStatus
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import save_persistent_cognition
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


class B0TwoEpochRejected(RuntimeError):
    """Missing or ambiguous evidence; no live-action retry/fallback."""


def _p(epoch: int, stage: str) -> Provenance:
    return Provenance("b0-explicit-operator", f"epoch{epoch}:{stage}")


def _admit_hunger_wait(ledger: B0EnergyLedger, read: Any) -> dict[str, Any]:
    """A real observation and L0 WAIT, no issuance and no fake food credit."""
    coverage = read.snapshot.nearby_entities_coverage
    if (
        coverage.truncated
        or coverage.candidate_count != len(read.snapshot.nearby_entities)
        or any(e.name == "item" for e in read.snapshot.nearby_entities)
        or any(i.count > 0 for i in read.snapshot.inventory)
    ):
        raise B0TwoEpochRejected("hunger staging must start with no item fixture")
    decision = ledger.decide(read)
    if decision.kind != "WAIT":
        raise B0TwoEpochRejected("native L0 not WAIT before ground fixture")
    return {
        "probe_seq": read.seq,
        "world_food": read.snapshot.food,
        "l0_kind": decision.kind,
        "energy_sensor": decision.sensor_reading,
        "energy_before": ledger.body.energy,
        "metabolic_tick": ledger.body.tick,
        "issued_action": False,
    }


async def _stage_hunger(
    session: Any, server: Any, ledger: B0EnergyLedger, epoch: int,
    entry: dict[str, Any],
) -> None:
    if server.stdin is None:
        raise B0TwoEpochRejected("missing owned Minecraft console")
    entry["stage"] = "NATIVE_HUNGER_BEFORE_GROUND"
    entry["hunger_trace"] = []
    _command(server, "effect give RelaySelf minecraft:hunger 25 20 true")
    await server.stdin.drain()
    for attempt in range(16):
        await asyncio.sleep(2)
        read = await _correlated_observe(
            session, f"b0-multi-e{epoch}-hunger-{attempt:02d}",
        )
        trace = _admit_hunger_wait(ledger, read)
        entry["hunger_trace"].append(trace)
        if read.snapshot.food < 14:
            break
        transition = ledger.step("WAIT")
        trace["energy_after_wait"] = transition.after.energy
        trace["expenditure"] = transition.expenditure
        if transition.terminal_now:
            raise B0TwoEpochRejected("M0 starved before staged food")
    else:
        raise B0TwoEpochRejected("World hunger never reached L0 feeding threshold")
    _command(server, "effect clear RelaySelf minecraft:hunger")
    await server.stdin.drain()


async def _eat_verified(
    session: Any, ledger: B0EnergyLedger, epoch: int,
    entry: dict[str, Any],
) -> None:
    entry["stage"] = "NATIVE_L0_EAT_ISSUED"
    cursor = EatCursor(ledger.session_id, hunger_threshold=14.0)
    before = choice = None
    entry["eat_gate_trace"] = []
    for attempt in range(16):
        await asyncio.sleep(2)
        probe = await _correlated_observe(
            session, f"b0-multi-e{epoch}-eat-gate-{attempt:02d}",
        )
        decision = ledger.decide(probe)
        entry["eat_gate_trace"].append({
            "probe_seq": probe.seq,
            "kind": decision.kind,
            "world_food": probe.snapshot.food,
            "body_energy": ledger.body.energy,
            "metabolic_tick": ledger.body.tick,
            "issued_action": False,
        })
        if (
            decision.kind == "EAT"
            and decision.eat_choice is not None
            and decision.eat_choice.item_name == "rotten_flesh"
        ):
            before = probe
            choice = cursor.choose(probe)
            break
        if ledger.step("WAIT").terminal_now:
            raise B0TwoEpochRejected("M0 starved awaiting source-qualified EAT")
    if (
        before is None or choice is None
        or choice.status is not EatStatus.CANDIDATE
        or choice.item_name != "rotten_flesh"
    ):
        raise B0TwoEpochRejected("native L0 never selected the newly acquired food")
    entry["eat_before"] = {
        "probe_seq": before.seq,
        "world_food": before.snapshot.food,
        "rotten_flesh_count": sum(
            i.count for i in before.snapshot.inventory if i.name == "rotten_flesh"
        ),
    }
    intent = IntentCommitment()
    intent.commit(
        f"b0-multi-e{epoch}-eat-intent",
        objective="eat the observed rotten flesh when hungry",
        at_ns=1, provenance=_p(epoch, "intent"),
    )
    skill = SkillExecution.start(
        f"b0-multi-e{epoch}-eat-skill", skill_id="eat",
        intent_commitment=intent, at_ns=2,
        provenance=_p(epoch, "skill"),
    )
    action_id = f"b0-multi-e{epoch}-eat-rotten_flesh"
    proposed = ActionLifecycle.propose(
        action_id, skill_execution=skill, intent_commitment=intent,
        at_ns=3, provenance=_p(epoch, "proposed"),
    )
    authorized = proposed.authorize(
        at_ns=4, authority="b0-two-epoch-independent-eat-authorization",
        provenance=_p(epoch, "authorized"),
    )
    supervisor = ActionSupervisor()
    issued = supervisor.issue(
        authorized, at_ns=5, deadline_ns=200,
        provenance=_p(epoch, "issued"),
    )
    entry["eat_action_id"] = action_id
    try:
        receipt = await IssuedEatingExecutor().execute(
            session, supervisor, issued, choice, before,
        )
    finally:
        entry["eat_action_terminal"] = supervisor.get(action_id).state.value
    entry["eat_outcome"] = asdict(receipt.outcome)
    if (
        receipt.terminal.state is not ActionState.OUTCOME
        or receipt.outcome.food_after <= receipt.outcome.food_before
        or receipt.outcome.count_before - receipt.outcome.count_after != 1
        or supervisor.open_actions
    ):
        raise B0TwoEpochRejected("real EAT source/Action outcome not closed")
    entry["energy_before_credit"] = asdict(ledger.body)
    transition = ledger.step("WAIT", eating=receipt)
    entry["metabolism_after_credit"] = {
        **asdict(ledger.body),
        "intake": transition.intake,
        "expenditure": transition.expenditure,
        "credit_count": ledger.credit_count,
        "credited_action_id": action_id,
    }
    if (
        transition.terminal_now
        or transition.intake != ledger.config.food_energy
        or ledger.credit_count != epoch + 1
        or ledger.body.meals != epoch + 1
    ):
        raise B0TwoEpochRejected("M0 credit/terminal not consistent with epoch")
    fresh = await _correlated_observe(
        session, f"b0-multi-e{epoch}-next-native",
    )
    entry["next_native_probe"] = asdict(fresh)
    next_l0 = ledger.decide(fresh)
    entry["next_l0"] = {
        "probe_seq": next_l0.probe_seq,
        "kind": next_l0.kind,
        "energy_sensor": next_l0.sensor_reading,
        "body_tick": next_l0.body_tick,
        "issued_action": False,
    }
    if next_l0.kind != "WAIT":
        raise B0TwoEpochRejected("post-EAT native L0 did not return to WAIT")
    entry["stage"] = "CLOSED"


async def run_two_ground_epochs(
    session: Any, server: Any, ledger: B0EnergyLedger,
    traces: list[dict[str, Any]], *, nonforcing: bool = False,
    b1_local_adaptation: bool = False,
    b1_retention: bool = True,
    b1_memory_path: Path | None = None,
) -> dict[str, Any] | None:
    """One owned session with two sequential staged-item EAT outcomes.

    Caller owns physical lifecycle and original byte recording. This module
    only performs an explicitly authorized bounded two-epoch product trial.
    """
    if (
        not isinstance(ledger, B0EnergyLedger)
        or type(nonforcing) is not bool
        or traces or ledger.body.terminal
    ):
        raise B0TwoEpochRejected("fresh live two-epoch body and trace required")
    if (
        type(b1_local_adaptation) is not bool or type(b1_retention) is not bool
        or (b1_local_adaptation and (
            nonforcing or not isinstance(b1_memory_path, Path)
            or b1_memory_path.exists() or b1_memory_path.is_symlink()
            or not b1_memory_path.parent.is_dir()
        ))
        or (not b1_local_adaptation and b1_memory_path is not None)
    ):
        raise B0TwoEpochRejected("B1 requires fresh isolated DEV Memory destination")
    b1_local = (
        B1LocalCandidate(ledger.session_id, retain=b1_retention)
        if b1_local_adaptation else None
    )
    try:
        return await _run_two_ground_epochs_body(
            session, server, ledger, traces,
            nonforcing=nonforcing, b1_local=b1_local,
        )
    finally:
        if b1_local is not None:
            if traces:
                traces[0]["b1_local_final"] = b1_local.evidence()
            if b1_local.cognition.memories:
                save_persistent_cognition(b1_memory_path, b1_local.cognition)


async def _run_two_ground_epochs_body(
    session: Any, server: Any, ledger: B0EnergyLedger,
    traces: list[dict[str, Any]], *,
    nonforcing: bool, b1_local: B1LocalCandidate | None,
) -> dict[str, Any] | None:
    for epoch in range(2):
        entry: dict[str, Any] = {"epoch": epoch, "stage": "START"}
        traces.append(entry)  # retain partial original report on failure
        await _stage_hunger(session, server, ledger, epoch, entry)
        entry["stage"] = "NATIVE_L0_SEEK_AND_ISSUED_S50_MOVE"
        try:
            entry["ground_pickup"] = await acquire_staged_ground_flesh(
                session, server, energy_ledger=ledger, epoch=epoch,
                nonforcing=nonforcing,
                # The one retained episode remains owned, but cannot steer
                # an unrelated second food target. Epoch 1 runs original L0.
                b1_local=b1_local if epoch == 0 else None,
                b1_obstacle=b1_local is not None and epoch == 0,
            )
        except GroundRejected as exc:
            raise B0TwoEpochRejected("ground fixture/pickup failed") from exc
        item_status = entry["ground_pickup"]["status"]
        if nonforcing and item_status in (
            "M0_TERMINAL_NO_PICKUP", "HORIZON_CENSORED_NO_PICKUP",
        ):
            entry["stage"] = "OBSERVED_NONFORCING_NO_PICKUP"
            return {
                "outcome": item_status, "epochs_started": len(traces),
                "meals": ledger.body.meals, "credits": ledger.credit_count,
                "energy": ledger.body.energy, "m0_terminal": ledger.body.terminal,
                "minecraft_hp_death": "NOT_ESTABLISHED", "science": "NO_GO",
            }
        if (
            item_status != "PICKUP_SOURCE_CONSISTENT"
            or entry["ground_pickup"]["pickup_inventory_delta"] != 1
            or entry["ground_pickup"]["epoch"] != epoch
        ):
            raise B0TwoEpochRejected("exactly one fresh item required per epoch")
        await _eat_verified(session, ledger, epoch, entry)
    if b1_local is not None and (
        b1_local.blocked_count < 1 or b1_local.reuse_count < 1
        or b1_local.alternative_outcomes < 1
        or b1_local.alternative_progressed < 1
    ):
        raise B0TwoEpochRejected("B1 no native BLOCKED-to-alternative OUTCOME witness")
    if ledger.credit_count != 2 or ledger.body.meals != 2 or ledger.body.terminal:
        raise B0TwoEpochRejected("two completed meals did not retain a live body")
    if nonforcing:
        return {
            "outcome": "TWO_GROUND_MEALS_COMPLETED",
            "epochs_started": len(traces),
            "meals": ledger.body.meals, "credits": ledger.credit_count,
            "energy": ledger.body.energy, "m0_terminal": ledger.body.terminal,
            "minecraft_hp_death": "NOT_ESTABLISHED", "science": "NO_GO",
        }
    return None


V2_HORIZON_M0_TICKS = 16
V2_MAX_ISSUED_MOVES = 8
V2_FIRST_ITEM_TICK = 11
V2_ARMS = {
    "SENSOR_ON": ("sensor_gate", 1.0, 0.0),
    "SHAM_ON": ("sensor_gate", 1.0, 0.0),
    "SENSOR_MASKED": ("sensor_gate", 0.0, 12.0),
    "CHEAP_NATIVE": ("native_only", 1.0, 0.0),
}


def validate_v2_arm(ledger: B0EnergyLedger, arm: str) -> None:
    from experiments.metabolism_viability import Interoception

    if (
        arm not in V2_ARMS
        or not isinstance(ledger, B0EnergyLedger)
        or ledger.body.tick != 0 or ledger.body.meals != 0
        or ledger.credit_count != 0 or ledger.body.terminal
    ):
        raise B0TwoEpochRejected("V2 requires a fresh and named reference arm")
    policy, gain, bias = V2_ARMS[arm]
    if (
        ledger.forage_policy != policy
        or ledger.sensor != Interoception(gain=gain, bias=bias)
    ):
        raise B0TwoEpochRejected("V2 arm/policy/sensor projection mismatch")


async def run_v2_fixed_study(
    session: Any, server: Any, ledger: B0EnergyLedger,
    arm: str, entry: dict[str, Any],
) -> dict[str, Any]:
    """Prospective S owner product path, NOT V independent science admission.

    One operator item at the predeclared M0 tick-11 boundary, then
    continue on unchanged M0 physics to globally censored tick16 or
    earlier terminal. World-clock synchronization remains R/V-unqualified.
    """
    validate_v2_arm(ledger, arm)
    if entry:
        raise B0TwoEpochRejected("V2 requires fresh unmodified original report")
    entry.update({
        "study": "V2_SINGLE_PRECOMMITTED_GROUND_OPPORTUNITY",
        "arm": arm, "global_m0_horizon": V2_HORIZON_M0_TICKS,
        "global_max_issued_moves": V2_MAX_ISSUED_MOVES,
        "predeclared_item_spawn_m0_tick": V2_FIRST_ITEM_TICK,
        "external_food_items": 1,
        "stage": "START", "action_source": "S50_S51_EXISTING_OWNER",
        "independent_v_science": "NOT_ADMITTED",
    })
    await _stage_hunger(session, server, ledger, 0, entry)
    if ledger.body.tick != V2_FIRST_ITEM_TICK:
        raise B0TwoEpochRejected(
            "unmatched exogenous first item timing: expected M0 tick 11"
        )
    entry["stage"] = "SINGLE_FIXED_ITEM_OPPORTUNITY"
    entry["source_time_bracket"] = {}
    entry["ground_pickup"] = await acquire_staged_ground_flesh(
        session, server, energy_ledger=ledger, epoch=0, nonforcing=True,
        global_m0_horizon=V2_HORIZON_M0_TICKS,
        global_move_limit=V2_MAX_ISSUED_MOVES,
        source_time_bracket=entry["source_time_bracket"],
    )
    pickup = entry["ground_pickup"]
    if pickup["status"] == "M0_TERMINAL_NO_PICKUP":
        status = "M0_TERMINAL_BEFORE_GLOBAL_HORIZON"
    elif pickup["status"] == "HORIZON_CENSORED_NO_PICKUP":
        status = "HORIZON_CENSORED_NO_PICKUP"
    elif pickup["status"] == "PICKUP_SOURCE_CONSISTENT":
        if ledger.body.tick >= V2_HORIZON_M0_TICKS:
            status = "HORIZON_CENSORED_BEFORE_EAT"
        else:
            entry["stage"] = "ISSUED_NATIVE_S51_EAT"
            await _eat_verified(session, ledger, 0, entry)
            if ledger.body.tick > V2_HORIZON_M0_TICKS:
                raise B0TwoEpochRejected("S51 EAT exceeded global M0 horizon")
            status = "EAT_VERIFIED_CONTINUE"
    else:
        raise B0TwoEpochRejected("unexpected V2 ground opportunity result")
    entry["finish_wait_trace"] = []
    while ledger.body.tick < V2_HORIZON_M0_TICKS and not ledger.body.terminal:
        read = await _correlated_observe(
            session, f"b0-v2-{arm.lower()}-finish-t{ledger.body.tick:02d}",
        )
        decision = ledger.decide(read)
        if decision.kind != "WAIT":
            raise B0TwoEpochRejected("non-WAIT at fixed V2 continuation horizon")
        transition = ledger.step("WAIT")
        entry["finish_wait_trace"].append({
            "probe_seq": read.seq, "kind": decision.kind,
            "energy_sensor": decision.sensor_reading,
            "energy_after": transition.after.energy,
            "m0_tick_after": transition.after.tick,
            "terminal_now": transition.terminal_now,
            "issued_action": False,
        })
    moves = len(pickup["movement_outcomes"])
    if (
        ledger.body.tick > V2_HORIZON_M0_TICKS
        or moves > V2_MAX_ISSUED_MOVES
        or ledger.credit_count != ledger.body.meals
        or ledger.body.meals > 1
        or (ledger.body.terminal and ledger.body.energy != 0)
    ):
        raise B0TwoEpochRejected("V2 global budget/credited-source invariant failed")
    entry["stage"] = "CLOSED"
    return {
        "outcome": "M0_TERMINAL" if ledger.body.terminal else "HORIZON_CENSORED",
        "source_outcome": status,
        "m0_terminal_free_ticks": (
            ledger.body.tick - 1 if ledger.body.terminal else ledger.body.tick
        ),
        "final_m0_energy": ledger.body.energy,
        "net_m0_energy": ledger.body.energy - ledger.config.initial_energy,
        "eats": ledger.body.meals, "credits": ledger.credit_count,
        "issued_moves": moves,
        "global_horizon": V2_HORIZON_M0_TICKS,
        "global_max_moves": V2_MAX_ISSUED_MOVES,
        "fixed_fixture_m0_tick": V2_FIRST_ITEM_TICK,
        "external_world_time_matched": "NOT_INDEPENDENTLY_ATTESTED",
        "native_item_pickup_causation": "UNKNOWN",
        "v_scientific_admission": "NO_GO",
    }
