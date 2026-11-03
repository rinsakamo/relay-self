"""M #616: fail-closed physical WorldTick / energy admission boundary.

This is an audit of the *saved* original S49/S14/S16/B0 DEV readbacks;
it cannot reconstruct tick count, full-tick activity, true body energy, or
S/R producer authority from session/action IDs, time_of_day, or packet age.

M0 modeled basal/action costs, Minecraft hunger/exhaustion, P1 fatigue,
B0's unadvanced experimental ledger and wall/CPU/GPU costs are distinct.
Without S-owned continuous per-tick source and a separate admission rule,
energy debit is always zero. This gate never calls metabolism_step().
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Status = Literal["DEFERRED", "SOURCE_REJECTED"]

SCHEMA = "M616_S49_WORLD_TICK_ENERGY_COVERAGE_GATE_DEV_V1"


@dataclass(frozen=True, slots=True)
class WorldTickEnergyGate:
    status: Status
    reason: str
    session_id: str | None = None
    original_decisions: int = 0
    original_actions: int = 0
    original_b0_decisions: int = 0
    native_full_tick_coverage: str = "NOT_SUPPLIED"
    b0_model_energy: str = "UNADVANCED_INITIAL_STATE_NOT_PHYSICAL_COST"
    true_world_energy: str = "UNKNOWN_NO_PHYSICAL_ENERGY_TICK"
    consecutive_world_ticks: int | None = None
    paid_basal_ticks: int = 0
    paid_movement_ticks: int = 0
    physical_food_credits: int = 0
    energy_debits: int = 0
    p1_fatigue_updates: int = 0
    action_issues: int = 0
    model_calls: int = 0
    source_attested: bool = False
    action_authority: bool = False


def _rejected() -> WorldTickEnergyGate:
    return WorldTickEnergyGate("SOURCE_REJECTED", "foreign_or_forged_s49_b0_source")


def audit_original_s49_energy_coverage(
    s49_report: object, m_report: object,
) -> WorldTickEnergyGate:
    """Inspect same-session original saved reports, without promoting their scope.

    This function deliberately has no positive energy-debit path. A future
    source owner must expose a separately typed, independently assessed
    continuous WorldTick and event-census boundary; adding a JSON flag,
    S49 event seq, Minecraft time_of_day or V6 sparse packet sample will
    never satisfy this contract.
    """
    if type(s49_report) is not dict or type(m_report) is not dict:
        return _rejected()
    try:
        sid = s49_report["session_id"]
        decisions = s49_report["decisions"]
        actions = s49_report["actual_native_actions"]
        b0 = s49_report["original_b0_decision_readback"]
        l0 = s49_report["original_completion_readback"]
        s14 = s49_report["original_planned_readback"]
        m_b0 = m_report["m_original_b0_decision_only"]
        m_s14 = m_report["m_s14_original_join"]
        assert type(sid) is str and sid
        assert s49_report["status"] == "PASS" and s49_report["stage"] == "CLOSED"
        assert s49_report["node_exit"] == s49_report["server_exit"] == 0
        assert m_report["status"] == "RECORDED"
        assert s49_report["original_b0_decision_observer"] == "CALLBACK_RETURNED"
        assert s49_report["original_completion_observer"] == "CALLBACK_RETURNED"
        assert s49_report["original_planned_observer"] == "CALLBACK_RETURNED"
        assert type(decisions) is list and len(decisions) == 3
        assert type(actions) is list and len(actions) == 2
        assert [d["selected"] for d in decisions] == [
            "WAIT", "MOVE_AWAY", "MOVE_AWAY",
        ]
        assert [d["issued"] for d in decisions] == [False, True, True]
        assert len({d["probe_seq"] for d in decisions}) == 3
        assert all(type(d["probe_seq"]) is int for d in decisions)
        assert all(
            type(d["event_seq"]) is int and d["event_seq"] < d["probe_seq"]
            for d in decisions
        )
        for row in (b0, l0, s14, m_b0):
            assert type(row) is dict and row["session_id"] == sid
            assert row["source_attested"] is False
            assert row["action_authority"] is False
            assert row["energy_debits"] == 0
        assert b0["status"] == m_b0["status"] == "RECORDED"
        assert b0["decision_count"] == m_b0["decision_count"] == 3
        assert b0["decision_probe_seqs"] == [d["probe_seq"] for d in decisions]
        assert b0["decision_kinds"] == [x["b0_kind"] for x in m_b0["decisions"]]
        assert b0["owner_model_tick"] == 0
        assert b0["energy_transitions"] == m_b0["energy_transition_count"] == 0
        assert b0["energy_debits"] == m_b0["energy_debits"] == 0
        assert b0["food_credits"] == m_b0["food_credits"] == 0
        assert b0["true_world_energy"] == m_b0["true_world_energy"] == (
            "UNKNOWN_NO_PHYSICAL_ENERGY_TICK"
        )
        assert b0["b0_owner_model_energy"] == m_b0["b0_owner_model_energy"] == (
            "UNADVANCED_INITIAL_STATE_NOT_PHYSICAL_COST"
        )
        assert l0["step_count"] == 3 and l0["outcome_count"] == 2
        assert l0["real_b0_decision_supplied"] is False  # older S49 L0 contract
        assert s14["status"] == m_s14["m_original_s14_planned"]["status"] == "RECORDED"
        assert s14["move_epoch_count"] == 2 and s14["wait_epoch_count"] == 0
        assert m_s14["status"] == "RECORDED"
        assert m_s14["m_original_s16_receipts"]["status"] == "RECORDED"
        assert m_s14["m_admission"]["status"] == "RECORDED"
        assert m_s14["m_admission"]["session_id"] == sid
        assert m_s14["m_original_s16_receipts"]["session_id"] == sid
        assert m_report["original_b0_callbacks"] == 1
        assert m_report["energy_debits"] == m_report["new_native_reads"] == 0
        assert m_report["new_action_issues"] == m_report["new_model_calls"] == 0
        # Native S49 wire event seq is not a World tick. Neither the S49
        # observation day-clock nor a new arbitrary JSON flag can certify a
        # complete, action-classified per-tick census.
        for index, action in enumerate(actions):
            expected = decisions[index + 1]
            assert action["action"] == (
                f"s49-native-move-{expected['event_seq']}"
            )
            assert action["event_seq"] == expected["event_seq"]
            assert action["probe_seq"] == expected["probe_seq"]
            assert action["terminal"] == "outcome"
            evidence = action["execution_evidence"]
            assert evidence["status"] == "executed"
            assert evidence["action_id"] == action["action"]
            assert evidence["session_id"] == sid
            for key in ("before_observation", "after_observation"):
                obs = evidence[key]
                assert obs["session_id"] == sid
                assert type(obs["seq"]) is int
                assert obs["kind"] == "probe"
                assert type(obs["snapshot"]["time"]["time_of_day"]) is int
                assert "world_full_time" not in obs
                assert "world_age_ticks" not in obs
            assert (
                evidence["before_observation"]["seq"]
                < evidence["after_observation"]["seq"]
            )
        # Extra fields deliberately cannot make this a qualified source.
        # Retaining the zero debt is essential even if a caller appends
        # forged world_full_time or a positive tick count to saved JSON.
    except (AssertionError, KeyError, IndexError, TypeError, ValueError):
        return _rejected()
    return WorldTickEnergyGate(
        "DEFERRED", "S49_NATIVE_EVENT_SEQ_NOT_CONTINUOUS_WORLD_TICK",
        session_id=sid, original_decisions=len(decisions),
        original_actions=len(actions), original_b0_decisions=b0["decision_count"],
    )


def bounded_world_tick_energy_gate(gate: WorldTickEnergyGate) -> dict[str, Any]:
    if (
        not isinstance(gate, WorldTickEnergyGate)
        or gate.status not in ("DEFERRED", "SOURCE_REJECTED")
        or gate.source_attested or gate.action_authority
        or gate.native_full_tick_coverage != "NOT_SUPPLIED"
        or gate.true_world_energy != "UNKNOWN_NO_PHYSICAL_ENERGY_TICK"
        or gate.consecutive_world_ticks is not None
        or any((
            gate.paid_basal_ticks, gate.paid_movement_ticks,
            gate.physical_food_credits, gate.energy_debits,
            gate.p1_fatigue_updates, gate.action_issues, gate.model_calls,
        ))
        or (
            gate.status == "SOURCE_REJECTED"
            and (
                gate.reason != "foreign_or_forged_s49_b0_source"
                or gate.session_id is not None
                or gate.original_decisions or gate.original_actions
                or gate.original_b0_decisions
            )
        )
        or (
            gate.status == "DEFERRED"
            and (
                gate.reason != "S49_NATIVE_EVENT_SEQ_NOT_CONTINUOUS_WORLD_TICK"
                or not gate.session_id
                or gate.original_decisions != 3
                or gate.original_actions != 2
                or gate.original_b0_decisions != 3
            )
        )
    ):
        raise ValueError("forged physical WorldTick/B0 energy admission")
    return {
        "schema": SCHEMA,
        "status": gate.status,
        "reason": gate.reason,
        "session_id": gate.session_id,
        "original_decisions": gate.original_decisions,
        "original_actions": gate.original_actions,
        "original_b0_decisions": gate.original_b0_decisions,
        "native_full_tick_coverage": gate.native_full_tick_coverage,
        "consecutive_world_ticks": None,
        "physical_energy_debit_admitted": False,
        "paid_basal_ticks": 0,
        "paid_movement_ticks": 0,
        "physical_food_credits": 0,
        "energy_debits": 0,
        "p1_fatigue_updates": 0,
        "action_issues": 0,
        "model_calls": 0,
        "world_time_of_day_is_tick_meter": False,
        "s49_native_event_seq_is_world_tick": False,
        "b0_owner_model_energy": gate.b0_model_energy,
        "true_world_energy": gate.true_world_energy,
        "source_attested": False,
        "action_authority": False,
        "s42_owner_receipt": "NOT_SUPPLIED",
        "l8_owner_receipt": "NOT_SUPPLIED",
        "science": "NOT_RUN",
        "qualification": "NO_GO",
    }
