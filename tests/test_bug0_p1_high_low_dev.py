"""High/low *virtual* P1 profile discrimination, not measured fatigue.

Both rate profiles process the SAME original Paper FIGHT and stationary
callback interval; high/low differ only by explicitly hypothesized rate.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from adapters.mineflayer.s49_p1_paper_dev import S49P1SourceRejected
from test_bug0_s49_p1_paper_dev import NONCE, SESSION, sample_log
from tools.bug0_s49_p1_prospective_sensor import prospective_request


def same_source_at_180() -> str:
    lines = [
        line for line in sample_log().splitlines()
        if "S49P1_REST " not in line and "S49P1_STOP " not in line
    ]
    last = next(line for line in lines if "S49P1_TICK " in line and "tick=130 " in line)
    for tick in range(131, 181):
        lines.append(last.replace("tick=130 index=30",
                                  f"tick={tick} index={tick - 100}"))
    return "\n".join(lines)


def test_long_predecision_prefix_is_same_original_native_source():
    from tools.bug0_s49_p1_prospective_sensor import _prefix

    result = _prefix(same_source_at_180(), nonce=NONCE)
    assert result["callback_rows"] == 80
    assert result["source_last_tick"] == 180
    assert result["fight_callback_tick"] == 104
    assert result["fight_callback_count"] == 1


def test_unchanged_p1_model_branches_on_hypothetical_rate_not_fake_sensor():
    path = os.environ.get("S49_P1_ORIGINAL_CHECKOUT")
    if not path:
        pytest.skip("original pinned P1 separate checkout required")
    args = dict(
        paper_log=same_source_at_180(), nonce=NONCE,
        session_id=SESSION, probe_seq=30, p1_checkout=Path(path).resolve(),
        sensor_policy="margin",
    )
    low = prospective_request(**args, experimental_wait_rate=0.002)
    high = prospective_request(**args, experimental_wait_rate=0.001)
    assert low["original_p1_commit"] == high["original_p1_commit"]
    assert low["original_p1_module_sha256"] == high["original_p1_module_sha256"]
    assert low["paper_source_uuid"] == high["paper_source_uuid"]
    assert low["source_as_of_tick"] == high["source_as_of_tick"] == 180
    assert low["model_default_fatigue_pre_decision"] == 0
    assert high["model_default_fatigue_pre_decision"] == 0
    assert 0 < low["model_experimental_fatigue_pre_decision"] < 0.05
    assert high["model_experimental_fatigue_pre_decision"] > 0.10
    assert low["request_rest"] is False
    assert low["safety_margin_rest_shadow"] is False
    assert high["request_rest"] is True
    assert high["safety_margin_rest_shadow"] is True
    assert high["model_experimental_sensor_reading"] >= 0.1
    for x in (low, high):
        assert x["source_post_rest_lookahead_used"] is False
        assert x["p1_real_fatigue_attested"] is False
        assert x["original_P1_runtime_state_installed"] is False


@pytest.mark.parametrize("rate", (0.0009, 0.0015, 0.003, 0, 1,
                                     "0.001", True, None))
def test_high_low_profile_cannot_be_arbitrary_fit(rate):
    with pytest.raises(S49P1SourceRejected):
        prospective_request(
            same_source_at_180(), nonce=NONCE,
            session_id=SESSION, probe_seq=12,
            p1_checkout=Path("/dev/null"),
            sensor_policy="margin", experimental_wait_rate=rate,
        )


@pytest.mark.parametrize("variant", (
    "missing-gate", "missing-paper", "margin-conflict", "paper-conflict",
    "prospective-conflict", "wrong-checkout", "wrong-type",
))
def test_high_rate_original_s49_single_owner_gate_blocks_before_world(
    tmp_path, monkeypatch, variant,
):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_BUG0_P1_PAPER_DEV_ONLY", "1")
    monkeypatch.setenv("S49_BUG0_P1_HIGH_DEV_ONLY", "1")
    monkeypatch.setenv("S49_P1_ORIGINAL_CHECKOUT", "/tmp/one-p1-original")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(
        s49, "_fetch_official_server",
        lambda *_: (_ for _ in ()).throw(AssertionError("unexpected Mojang start")),
    )
    flags = {"bug0_p1_high_dev": True}
    if variant == "missing-gate":
        monkeypatch.delenv("S49_BUG0_P1_HIGH_DEV_ONLY")
    elif variant == "missing-paper":
        monkeypatch.delenv("S49_BUG0_P1_PAPER_DEV_ONLY")
    elif variant == "margin-conflict":
        flags["bug0_p1_margin_dev"] = True
    elif variant == "paper-conflict":
        flags["bug0_p1_paper_dev"] = True
    elif variant == "prospective-conflict":
        flags["bug0_p1_prospective_rest_dev"] = True
    elif variant == "wrong-checkout":
        monkeypatch.delenv("S49_P1_ORIGINAL_CHECKOUT")
    elif variant == "wrong-type":
        flags["bug0_p1_high_dev"] = "yes"
    out = tmp_path / "blocked.json"
    code = asyncio.run(s49.qualify(out, tmp_path / "paper.log", **flags))
    row = json.loads(out.read_text(encoding="utf8"))
    assert code == 2 and row["status"] == "BLOCKED"
    assert row["actual_native_actions"] == []
    assert not (tmp_path / "paper.log").exists()
