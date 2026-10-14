"""B1 DEV route and evidence projection; no Java/Node/Minecraft starts."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from adapters.mineflayer import self_demo as demo
from adapters.mineflayer import s51_eat_real_ci as s51


def _args(path):
    return SimpleNamespace(
        output_dir=path, confirm=demo.CONFIRM, run_disposable=True,
        think=False, live_think=False, reflect_report=None, smoke=False,
        retry_of=None, dev_scenario="b1-local-adaptation", b1_retention="on",
    )


def test_b1_dev_isolation_denies_qualification_and_grant(tmp_path):
    with pytest.raises(SystemExit):
        demo.main(["--dev-scenario", "b1-local-adaptation", "--run-disposable"])
    opts = dict(food_item="rotten_flesh", food_source="ground2",
                b1_local_adaptation=True, dev_only=True)
    for bad in ({"dev_only": False}, {"rsee": object()},
                {"food_source": "ground"}, {"b0_v2_arm": "SENSOR_ON"},
                {"b0_v6_phase": "LOW"}):
        with pytest.raises(ValueError):
            asyncio.run(s51.qualify(tmp_path / "r", tmp_path / "l",
                                    **{**opts, **bad}))
    assert not (tmp_path / "r").exists()


def test_b1_cli_delegates_unchanged_s51_owner(tmp_path, monkeypatch):
    calls = []
    async def owner(report, log, **kwargs):
        calls.append(kwargs)
        return 0
    monkeypatch.setattr(s51, "qualify", owner)
    assert asyncio.run(demo._run_b1_local_dev(
        tmp_path / "report", tmp_path / "log", retention=False,
    )) == 0
    assert calls == [dict(
        food_item="rotten_flesh", food_source="ground2",
        dev_only=True, b1_local_adaptation=True, b1_retention=False,
    )]


def test_b1_forged_owner_success_never_promotes_to_r_or_v(tmp_path, monkeypatch):
    monkeypatch.setattr(demo.shutil, "which", lambda _: "/tool")
    monkeypatch.setattr(demo.subprocess, "run", lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout="version", stderr=""))
    async def owner(report, log, *, retention):
        report.write_text(json.dumps({
            "status": "PASS", "owner_status": "PASS", "classification": "QUALIFIED",
            "session_id": "native-test", "server_exit": 0, "node_exit": 0,
            "metabolism_terminal": {"meals": 2, "energy": 3.0},
            "b1_local_final": {"blocked_action_count": 1, "reused_for_lateral_choice": 1,
                               "retained_observations": 1},
            "two_ground_epochs": [
                {"hunger_trace": [{}], "eat_gate_trace": [{}],
                 "ground_pickup": {"movement_outcomes": [{"kind": "BLOCKED"},
                    {"kind": "PROGRESSED"}], "l0_ground_seek_trace": [{}]},
                 "eat_action_terminal": "outcome", "next_l0": {"kind": "WAIT"}},
                {"hunger_trace": [{}], "eat_gate_trace": [{}],
                 "ground_pickup": {"movement_outcomes": [{"kind": "PROGRESSED"}],
                                   "l0_ground_seek_trace": [{}]},
                 "eat_action_terminal": "outcome", "next_l0": {"kind": "WAIT"}},
            ],
        }))
        return 0
    monkeypatch.setattr(demo, "_run_b1_local_dev", owner)
    root = tmp_path / "fresh-b1"
    assert demo._dev_run(_args(root)) == 0
    output = json.loads((root / "dev_receipt.json").read_text())
    assert output["classification"] == "DEV_ONLY"
    assert output["source_scope"] == "S51_OWNER_B1_DEV_NOT_QUALIFIED"
    assert output["dev_b1_action_outcomes"] == 5
    assert output["dev_b1_decisions"] == 8
    assert output["dev_b1_epoch_count"] == 2
    assert output["dev_b1_meals"] == 2
    assert output["stop_ack"] == "UNATTESTED"
    assert output["native_actions"] == 5
    assert not any(output[k] for k in (
        "engineering_qualified", "science_success", "g3_go", "m_energy_credited",
    ))
