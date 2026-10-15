"""Synthetic adversarial checks for R M0.2 Paper DEV original-source audit."""
from __future__ import annotations

import copy
import json

import pytest

from experiments.standard_env import m02_paper_dev_audit as r


def dump(x):
    return (json.dumps(x, sort_keys=True) + "\n").encode()


def specimen():
    session = "dev-m02-synthetic"
    native = [
        {"type": "observation", "kind": "probe", "session_id": session,
         "seq": i, "snapshot": {"food": 13, "food_saturation": 0.0,
                                "inventory": [{"name": "cooked_beef", "count": 3}]}}
        for i in range(10)
    ]
    native[0]["type"] = "adapter_started"
    native[4] = {"type": "effect_result", "seq": 4, "session_id": session,
                 "effect": "equip_item", "action_id": "m02-paper-eat-steak-1-equip",
                 "result": "applied"}
    native[5] = {"type": "effect_result", "seq": 5, "session_id": session,
                 "effect": "consume_held", "action_id": "m02-paper-eat-steak-1-consume",
                 "result": "applied"}
    for i in (6, 7):
        native[i]["snapshot"] = {"food": 20, "food_saturation": 12.8,
                                 "inventory": [{"name": "cooked_beef", "count": 2}]}
    native[8]["type"] = "shutdown_ack"
    native[9]["type"] = "connection_end"
    commands = [
        {"type": "effect", "effect": "equip_item",
         "action_id": "m02-paper-eat-steak-1-equip"},
        {"type": "effect", "effect": "consume_held",
         "action_id": "m02-paper-eat-steak-1-consume"},
        {"type": "shutdown"},
    ]
    log = ("[Paper] M02_DEV_ONLY: candidate physics, not qualified by R/V\n"
           "M02_DEV_BODY sampled_tick=1 player=RelaySelf food=13 "
           "exhaustion=0.001 events=0\n"
           "M02_DEV_BODY sampled_tick=20 player=RelaySelf food=13 "
           "exhaustion=0.02 events=1\n"
           "M02_DEV_EVENT id=1 reason=WALK original=0.0 replaced=0.0\n"
           "M02_DEV_MOTION id=1 reason=WALK blocks=0.8 billed=0.008 "
           "cumulative_blocks=0.8 cumulative_billed=0.008\n")
    report = {
        "milestone": "M0.2_PAPER_DEV",
        "classification": "M02_PAPER_DEV_ONLY_PHYSICS_OBSERVED",
        "status": "PASS", "owner_status": "PASS",
        "physical_world": "STARTED_NEW_DEV_PAPER",
        "minecraft_version": "1.21.8", "steak": "cooked_beef",
        "m0_virtual_ledger_used": False, "qualified": False,
        "science_go": False, "production_go": False,
        "java_exit": 0, "node_exit": 0, "port_released_after_shutdown": True,
        "source_session_id": session,
        "movement": {
            "source_session": session, "action_id": "m02-paper-walk-1",
            "action_state": "outcome", "requested_max_step_blocks": 1.0,
            "observed_progress_blocks": 0.65,
            "source_before_seq": 1, "source_after_seq": 2,
        },
        "eating": {
            "source_session": session, "action_id": "m02-paper-eat-steak-1",
            "action_state": "outcome", "virtual_energy_credit": 0,
            "native_outcome": {
                "action_id": "m02-paper-eat-steak-1", "session_id": session,
                "consumed_item": "cooked_beef", "count_before": 3,
                "count_after": 2, "food_before": 13, "food_after": 20,
                "after_probe_seq": 6,
            },
            "saturation_before": 0.0, "saturation_after": 12.8,
        },
    }
    return log, native, commands, report


def run(s):
    log, native, commands, report = s
    return r.inspect(log.encode(), b"".join(map(dump, native)),
                     b"".join(map(dump, commands)), report)


def test_default_never_reads_host(monkeypatch):
    monkeypatch.setattr(r, "audit", lambda _: pytest.fail("unexpected host read"))
    assert r.main([]) == 0


def test_source_envelope_independent_arithmetic_and_nonpromotion():
    result = run(specimen())
    assert result["observed_motion_packets"] == 1
    assert result["observed_motion_blocks"] == pytest.approx(0.8)
    assert result["recomputed_walk_exhaustion"] == pytest.approx(0.008)
    assert result["observed_native_steak_eat"]
    assert result["native_stop_ack_seq"] == 8
    assert not result["engineering_qualified"]
    assert not result["science_go"]
    assert result["physical_world_launches_by_reviewer"] == 0


@pytest.mark.parametrize("fault", [
    "native_duplicate", "native_session", "stop_lost",
    "double_shutdown", "eat_child_rejected", "eat_child_duplicate",
    "eat_report_forged", "food_forged", "stock_forged",
    "movement_billed_low", "movement_cumulative_forged",
    "walk_native_not_zero", "basal_missing", "dev_qualified",
    "virtual_credit", "wrong_world", "bad_move_probe", "unknown_eat",
])
def test_fail_closed_critical_inconsistencies(fault):
    s = list(copy.deepcopy(specimen()))
    if fault == "native_duplicate":
        s[1][6]["seq"] = 5
    elif fault == "native_session":
        s[1][6]["session_id"] = "other"
    elif fault == "stop_lost":
        s[1][8]["type"] = "observation"
    elif fault == "double_shutdown":
        s[2].insert(-1, {"type": "shutdown"})
    elif fault == "eat_child_rejected":
        s[1][5]["result"] = "rejected"
    elif fault == "eat_child_duplicate":
        s[2].insert(1, dict(s[2][0]))
    elif fault == "eat_report_forged":
        s[3]["eating"]["native_outcome"]["count_after"] = 3
    elif fault == "food_forged":
        s[1][6]["snapshot"]["food"] = 13
    elif fault == "stock_forged":
        s[1][6]["snapshot"]["inventory"] = []
    elif fault == "movement_billed_low":
        s[0] = s[0].replace("billed=0.008", "billed=0.001")
    elif fault == "movement_cumulative_forged":
        s[0] = s[0].replace("cumulative_blocks=0.8", "cumulative_blocks=1.2")
    elif fault == "walk_native_not_zero":
        s[0] = s[0].replace("replaced=0.0", "replaced=0.001")
    elif fault == "basal_missing":
        s[0] = s[0].replace("sampled_tick=20", "sampled_tick=19")
    elif fault == "dev_qualified":
        s[3]["qualified"] = True
    elif fault == "virtual_credit":
        s[3]["m0_virtual_ledger_used"] = True
    elif fault == "wrong_world":
        s[3]["minecraft_version"] = "1.21.7"
    elif fault == "bad_move_probe":
        s[3]["movement"]["source_before_seq"] = 4
    elif fault == "unknown_eat":
        s[3]["eating"]["action_state"] = "unknown"
    with pytest.raises(r.Rejected):
        run(s)


def test_original_digest_and_symlink_negative(tmp_path):
    root = tmp_path / "paper"
    root.mkdir()
    log, native, commands, report = specimen()
    for name, data in {
        "paper_server.log": log.encode(),
        "original_native.jsonl": b"".join(map(dump, native)),
        "owner_commands.jsonl": b"".join(map(dump, commands)),
        "m02_report.json": dump(report),
    }.items():
        (root / name).write_bytes(data)
    with pytest.raises(r.Rejected, match="SHA256"):
        r.audit(root)
    (root / "paper_server.log").unlink()
    (root / "paper_server.log").symlink_to(root / "m02_report.json")
    with pytest.raises(r.Rejected, match="nonregular"):
        r.audit(root)
