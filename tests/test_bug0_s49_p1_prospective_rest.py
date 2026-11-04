"""Bug-0 S49 P1 prospective REST DEV: causal source and original owner guards."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from adapters.mineflayer.s49_p1_paper_dev import S49P1SourceRejected
from test_bug0_s49_p1_paper_dev import NONCE, SESSION, sample_log
from tools.bug0_s49_p1_prospective_sensor import (
    EXPERIMENTAL_SENSOR_THRESHOLD,
    EXPERIMENTAL_WAIT_RECOVERY,
    _prefix,
    prospective_request,
)


def prospective_log() -> str:
    return "\n".join(
        line for line in sample_log().splitlines()
        if "S49P1_REST " not in line
        and "S49P1_STOP " not in line
        and not (line.startswith("S49P1_TICK ") and any(
            f"tick={tick} " in line for tick in range(116, 131)
        ))
    )


def test_live_paper_prefix_only_fight_and_observed_wait_candidates():
    prefix = _prefix(prospective_log(), nonce=NONCE)
    assert prefix["fight_event_tick"] == 103
    assert prefix["fight_callback_tick"] == 104
    assert prefix["source_last_tick"] == 115
    assert prefix["callback_rows"] == 15
    assert EXPERIMENTAL_WAIT_RECOVERY == 0.002
    assert EXPERIMENTAL_SENSOR_THRESHOLD == 0.05


@pytest.mark.parametrize("change", (
    "post-rest", "post-stop", "source-fault", "missing-fight", "fight-duplicate",
    "foreign-nonce", "foreign-world", "foreign-player", "gapped",
    "late-swing", "late-move", "late-teleport", "nonfinite-position",
    "nonfinite-distance", "negative-counter", "missing-index",
))
def test_prospective_prefix_never_infers_wait_on_unverified_source(change):
    text = prospective_log()
    if change == "post-rest":
        text += f"\nS49P1_REST nonce={NONCE} world=11111111-2222-3333-4444-555555555555 tick=116 index=15"
    elif change == "post-stop":
        text += f"\nS49P1_STOP nonce={NONCE} world=11111111-2222-3333-4444-555555555555 tick=116 index=15 faults=0"
    elif change == "source-fault":
        text += "\nS49P1_SOURCE_FAULT reason=GAPPED_OR_OVERFLOW"
    elif change == "missing-fight":
        text = "\n".join(x for x in text.splitlines() if "S49P1_FIGHT " not in x)
    elif change == "fight-duplicate":
        text += "\n" + next(x for x in text.splitlines() if "S49P1_FIGHT " in x)
    elif change == "foreign-nonce":
        text = text.replace(f"S49P1_TICK nonce={NONCE}", "S49P1_TICK nonce=foreign123456", 1)
    elif change == "foreign-world":
        text = text.replace("world=11111111-2222-3333-4444-555555555555 tick=115", "world=other tick=115")
    elif change == "foreign-player":
        text = text.replace("attacker=99999999-aaaa-bbbb-cccc-111111111111", "attacker=99999999-aaaa-bbbb-cccc-222222222222")
    elif change == "gapped":
        text = "\n".join(x for x in text.splitlines() if "S49P1_TICK " not in x or "tick=110 " not in x)
    elif change == "late-swing":
        text = text.replace("tick=112 index=12 x=2.5 y=-60.0 z=0.5 move_events=0 move_distance=0.0 fight_events=0 swing_events=0", "tick=112 index=12 x=2.5 y=-60.0 z=0.5 move_events=0 move_distance=0.0 fight_events=0 swing_events=1")
    elif change == "late-move":
        text = text.replace("tick=112 index=12 x=2.5 y=-60.0 z=0.5 move_events=0", "tick=112 index=12 x=2.5 y=-60.0 z=0.5 move_events=1")
    elif change == "late-teleport":
        text = text.replace("tick=112 index=12 x=2.5 y=-60.0 z=0.5 move_events=0 move_distance=0.0 fight_events=0 swing_events=0 interact_events=0 velocity_events=0 teleport_events=0", "tick=112 index=12 x=2.5 y=-60.0 z=0.5 move_events=0 move_distance=0.0 fight_events=0 swing_events=0 interact_events=0 velocity_events=0 teleport_events=1")
    elif change == "nonfinite-position":
        text = text.replace("tick=112 index=12 x=2.5", "tick=112 index=12 x=NaN")
    elif change == "nonfinite-distance":
        text = text.replace("tick=112 index=12 x=2.5 y=-60.0 z=0.5 move_events=0 move_distance=0.0", "tick=112 index=12 x=2.5 y=-60.0 z=0.5 move_events=0 move_distance=NaN")
    elif change == "negative-counter":
        text = text.replace("tick=112 index=12 x=2.5 y=-60.0 z=0.5 move_events=0", "tick=112 index=12 x=2.5 y=-60.0 z=0.5 move_events=-1")
    elif change == "missing-index":
        text = text.replace("tick=112 index=12", "tick=112 index=13")
    with pytest.raises(S49P1SourceRejected):
        _prefix(text, nonce=NONCE)


def test_pinned_original_p1_nondefault_live_sensor_when_checkout_available():
    owner = os.environ.get("S49_P1_ORIGINAL_CHECKOUT")
    if not owner:
        pytest.skip("original P1 checkout not present in ordinary unit test")
    result = prospective_request(
        prospective_log(),
        nonce=NONCE, session_id=SESSION, probe_seq=12,
        p1_checkout=Path(owner).resolve(),
    )
    assert result["request_rest"] is True
    assert result["model_default_fatigue_pre_decision"] == 0
    assert result["model_experimental_fatigue_pre_decision"] > 0.05
    assert result["source_as_of_tick"] == 115
    assert result["original_P1_runtime_state_installed"] is False
    assert result["source_post_rest_lookahead_used"] is False
    assert result["p1_real_fatigue_attested"] is False
    with pytest.raises(S49P1SourceRejected):
        prospective_request(
            prospective_log(), nonce=NONCE,
            session_id="foreign", probe_seq=12,
            p1_checkout=Path(owner).resolve(),
        )


@pytest.mark.parametrize("variant", (
    "missing-live-gate", "old-paper-mode", "old-attack-mode",
    "rest-mode", "unified-mode", "missing-original-p1", "wrong-type",
))
def test_new_prospective_s49_gate_blocks_before_java(
    tmp_path, monkeypatch, variant,
):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_BUG0_P1_PAPER_DEV_ONLY", "1")
    monkeypatch.setenv("S49_BUG0_P1_PROSPECTIVE_REST_ONLY", "1")
    monkeypatch.setenv("S49_P1_ORIGINAL_CHECKOUT", "/tmp/p1-unavailable")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(
        s49, "_fetch_official_server",
        lambda *_: (_ for _ in ()).throw(AssertionError("unexpected startup")),
    )
    flags = {"bug0_p1_prospective_rest_dev": True}
    if variant == "missing-live-gate":
        monkeypatch.delenv("S49_BUG0_P1_PROSPECTIVE_REST_ONLY")
    elif variant == "old-paper-mode":
        flags["bug0_p1_paper_dev"] = True
    elif variant == "old-attack-mode":
        flags["bug0_attack_dev"] = True
    elif variant == "rest-mode":
        flags["bug0_rest_dev"] = True
    elif variant == "unified-mode":
        flags["bug0_unified_survival_dev"] = True
    elif variant == "missing-original-p1":
        monkeypatch.delenv("S49_P1_ORIGINAL_CHECKOUT")
    else:
        flags["bug0_p1_prospective_rest_dev"] = "yes"
    path = tmp_path / "blocked.json"
    result = asyncio.run(s49.qualify(
        path, tmp_path / "paper.log", **flags,
    ))
    report = json.loads(path.read_text())
    assert result == 2 and report["status"] == "BLOCKED"
    assert report["actual_native_actions"] == []
    assert not (tmp_path / "paper.log").exists()
