"""Independent V2 review of S's pinned nonforcing owner (source-shaped only).

This loads S's *unmodified* fixture at an immutable CI checkout; it executes
no Java/Node/World/model, issues no Action, and cannot attest real outcomes.
"""
from __future__ import annotations

import argparse
import ast
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from experiments.validation.v2_knockdown import ARMS, SENSORS, load_protocol

S_NONFORCING_HEAD = "6f95c34918fbe29fea56bc7284e94c4edce21aff"
CLASSIFICATION = "V2_S_NONFORCING_OFFLINE_PARITY_WITH_PREREG_MISMATCH"
EXPECTED_BLOCKERS = [
    "S_24_OPPORTUNITY_DECISIONS_NOT_V_16_M0_TICK_GLOBAL_HORIZON",
    "S_8_ISSUED_MOVES_PER_EPOCH_NOT_V_8_TOTAL",
    "UNFROZEN_MATCHED_WORLD_STARTS_AND_EXOGENOUS_STAGING",
    "NO_REAL_SHAM_CHEAP_OR_MASKED_OUTCOME_PAIRS",
    "NO_INDEPENDENT_R_V_ORIGINAL_SOURCE_GOAL_ADMISSION",
]


class SBoundaryRejected(ValueError):
    """S changed/misloaded, bounded source mismatch or unsupported promotion."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SBoundaryRejected(message)


def _range_calls(path: Path, method: str) -> list[int]:
    """Review source-owned declared loop bounds, never executing the runner."""
    require(path.is_file() and not path.is_symlink(), "S file not regular")
    module = ast.parse(path.read_text(encoding="utf-8"))
    funcs = [
        node for node in ast.walk(module)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == method
    ]
    require(len(funcs) == 1, "S function changed/missing")
    values: list[int] = []
    for node in ast.walk(funcs[0]):
        if not isinstance(node, (ast.For, ast.AsyncFor)):
            continue
        call = node.iter
        if (
            isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
            and call.func.id == "range" and len(call.args) == 1
            and isinstance(call.args[0], ast.Constant)
            and type(call.args[0].value) is int
        ):
            values.append(call.args[0].value)
    return values


def source_bounds(s_root: Path) -> tuple[int, int, int]:
    ground = _range_calls(
        s_root / "adapters/mineflayer/b0_ground_runner.py",
        "acquire_staged_ground_flesh",
    )
    epochs = _range_calls(
        s_root / "adapters/mineflayer/b0_two_epoch.py", "run_two_ground_epochs",
    )
    require(24 in ground and ground.count(8) >= 2 and 2 in epochs,
            "S opportunity/move/epoch bounds changed")
    return 24, 8, 2


def review_s_nonforcing(s_root: Path) -> dict[str, Any]:
    """S owned decision code + V independent fixed oracle, with no host I/O.

    Run only with PYTHONPATH pointing to separately checked-out exact S HEAD.
    """
    from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
    from adapters.mineflayer.b0_ground_foraging import select_ground_target
    from adapters.mineflayer.b0_ground_runner import nonforcing_ground_decision
    from experiments.metabolism_viability import Interoception
    import test_b0_ground_foraging as s_fixture

    protocol = load_protocol()
    require(protocol["design"]["horizon_m0_ticks"] == 16, "V study changed")
    require(protocol["design"]["max_issued_moves"] == 8, "V move budget changed")
    assert source_bounds(s_root) == (24, 8, 2)
    # Source-shaped mock, same native food and one item for all four arms.
    native = s_fixture._ground()
    native = replace(native, snapshot=replace(native.snapshot, food=13.0))
    target = select_ground_target(native)
    decisions: dict[str, list[str]] = {}
    bodies: dict[str, dict[str, float | int | bool]] = {}
    sensor_at_seek: dict[str, float | None] = {}
    for arm in ARMS:
        policy, gain, bias, quantum = SENSORS[arm]
        ledger = B0EnergyLedger(
            native.session_id, forage_policy=policy,
            sensor=Interoception(gain=gain, bias=bias, quantum=quantum),
        )
        rows: list[str] = []
        seen_reading = None
        for i in range(16):
            probe = replace(
                native, seq=native.seq + i,
                request_id=f"v2-shadow-{arm.lower()}-{i}",
            )
            row = nonforcing_ground_decision(ledger, probe, target)
            require(row["issued_action"] is False, "fictitious issued WAIT/SEEK")
            require(row["item_entity_id"] == target.entity_id, "item switch")
            rows.append(row["kind"])
            if row["kind"] == "SEEK":
                seen_reading = row["energy_sensor"]
                break
            require(row["kind"] == "WAIT" and row["intake"] == 0
                    and row["m0_tick_after"] == row["m0_tick_before"] + 1,
                    "invalid observed WAIT")
            require(row["expenditure"] == 0.5, "S M0 physics drift")
        decisions[arm] = rows
        bodies[arm] = {
            "energy": ledger.body.energy,
            "tick": ledger.body.tick,
            "terminal": ledger.body.terminal,
            "credits": ledger.credit_count,
        }
        sensor_at_seek[arm] = seen_reading

    require(
        decisions["SENSOR_ON"] == decisions["SHAM_ON"]
        == ["WAIT"] * 7 + ["SEEK"], "ON/sham or sensor quantization drift",
    )
    require(sensor_at_seek["SENSOR_ON"] == sensor_at_seek["SHAM_ON"] == 8,
            "ties-to-even E8.5 -> 8 witness changed")
    require(decisions["SENSOR_MASKED"] == ["WAIT"] * 16
            and decisions["CHEAP_NATIVE"] == ["SEEK"],
            "masked vs equal-info cheap source contrast changed")
    require(
        bodies["SENSOR_ON"] == bodies["SHAM_ON"] == {
            "energy": 8.5, "tick": 7, "terminal": False, "credits": 0,
        }
        and bodies["SENSOR_MASKED"] == {
            "energy": 4.0, "tick": 16, "terminal": False, "credits": 0,
        }
        and bodies["CHEAP_NATIVE"] == {
            "energy": 12.0, "tick": 0, "terminal": False, "credits": 0,
        }, "unexpected source owner M0 side effect",
    )
    output = {
        "classification": CLASSIFICATION,
        "s_source_head": S_NONFORCING_HEAD,
        "source_kind": "S_OWNED_SYNTHETIC_MINEFLAYER_SHAPED_FIXTURE",
        "s_opportunity_max_decisions_per_epoch": 24,
        "s_issued_move_max_per_epoch": 8,
        "s_epoch_max": 2,
        "v_registered_global_m0_horizon": 16,
        "v_registered_total_move_budget": 8,
        "arms": decisions,
        "m0_end_state": bodies,
        "quantization_boundary": "E8.5_SENSOR_8_TIES_TO_EVEN_SEEK_AT_DECISION_8",
        "independent_real_world_starts": 0,
        "actual_world_trials": 0,
        "physical_original_readback": "NOT_RUN",
        "no_action_issued": True,
        "v2_live_trial_admitted": False,
        "scientific_g3": "NO_GO",
        "science_go": False,
        "blockers": EXPECTED_BLOCKERS,
    }
    return validate_review(output)


def validate_review(d: dict[str, Any]) -> dict[str, Any]:
    """Fail closed on a report attempting to promote synthetic source parity."""
    require(type(d) is dict and set(d) == {
        "classification", "s_source_head", "source_kind",
        "s_opportunity_max_decisions_per_epoch",
        "s_issued_move_max_per_epoch", "s_epoch_max",
        "v_registered_global_m0_horizon", "v_registered_total_move_budget",
        "arms", "m0_end_state", "quantization_boundary",
        "independent_real_world_starts", "actual_world_trials",
        "physical_original_readback", "no_action_issued",
        "v2_live_trial_admitted", "scientific_g3", "science_go", "blockers",
    }, "invalid report shape")
    require(
        d["classification"] == CLASSIFICATION
        and d["s_source_head"] == S_NONFORCING_HEAD
        and d["source_kind"] == "S_OWNED_SYNTHETIC_MINEFLAYER_SHAPED_FIXTURE",
        "source promotion",
    )
    require(
        (d["s_opportunity_max_decisions_per_epoch"],
         d["s_issued_move_max_per_epoch"], d["s_epoch_max"],
         d["v_registered_global_m0_horizon"],
         d["v_registered_total_move_budget"]) == (24, 8, 2, 16, 8),
        "misstated trial horizon/budget",
    )
    require(d["arms"] == {
        "SENSOR_ON": ["WAIT"] * 7 + ["SEEK"],
        "SHAM_ON": ["WAIT"] * 7 + ["SEEK"],
        "SENSOR_MASKED": ["WAIT"] * 16,
        "CHEAP_NATIVE": ["SEEK"],
    }, "altered synthetic S choices")
    require(d["m0_end_state"] == {
        "SENSOR_ON": {"energy": 8.5, "tick": 7, "terminal": False, "credits": 0},
        "SHAM_ON": {"energy": 8.5, "tick": 7, "terminal": False, "credits": 0},
        "SENSOR_MASKED": {"energy": 4.0, "tick": 16, "terminal": False, "credits": 0},
        "CHEAP_NATIVE": {"energy": 12.0, "tick": 0, "terminal": False, "credits": 0},
    }, "M0 cost or terminal fraud")
    require(d["quantization_boundary"]
            == "E8.5_SENSOR_8_TIES_TO_EVEN_SEEK_AT_DECISION_8",
            "quantized boundary missing")
    require(type(d["independent_real_world_starts"]) is int
            and d["independent_real_world_starts"] == 0
            and type(d["actual_world_trials"]) is int
            and d["actual_world_trials"] == 0
            and d["physical_original_readback"] == "NOT_RUN"
            and d["no_action_issued"] is True
            and d["v2_live_trial_admitted"] is False
            and d["scientific_g3"] == "NO_GO"
            and d["science_go"] is False
            and d["blockers"] == EXPECTED_BLOCKERS,
            "false scientific/physical promotion")
    return d


def main() -> int:
    parser = argparse.ArgumentParser(description="V2 read-only S owner parity")
    parser.add_argument("--s-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(review_s_nonforcing(args.s_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
