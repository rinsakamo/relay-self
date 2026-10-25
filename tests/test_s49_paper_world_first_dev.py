"""Offline DEV-only tests for the original S49 report/Paper/P1 join."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

from adapters.mineflayer import s49_normal_session_real_ci as original_s49

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_postwait_dev import review_postaction_wait_dev
from adapters.mineflayer.s49_paper_world_first_dev import (
    CONFIRM,
    offline_uuid,
    run,
)
from experiments.fatigue_p1 import FatigueProfile
from test_s49_paper_transcript_dev import PLAYER, transcript, typed_owner

WORLD = "42345678-1234-4234-8234-123456789abc"


def sources(monkeypatch):
    capture = typed_owner(monkeypatch)
    evidence = capture.projection.decoded_evidence
    sid = capture.projection.session_id
    native = {
        "status": "PASS",
        "session_id": sid,
        "actual_native_actions": [
            {"action": "original-prior-move"},
            {
                "action": capture.projection.action_id,
                "source": sid,
                "terminal": "outcome",
                "movement_m": evidence["movement_m"],
                "execution_evidence": json.loads(json.dumps(evidence)),
            },
        ],
    }
    paper = transcript(capture).replace(
        "world=paper-dev-world-s49", "world=" + WORLD,
    )
    return native, paper


def evaluate(native, paper):
    return review_postaction_wait_dev(
        native, paper, expected_player_uuid=PLAYER,
        profile=FatigueProfile(enabled=True, initial=0.5),
    )


def test_post_s49_original_receipt_world_paper_idle_and_p1_dev(monkeypatch):
    native, paper = sources(monkeypatch)
    result = evaluate(native, paper)
    assert result["status"] == "OFFLINE_MODEL_REPLAY"
    assert result["dev_wait_count"] == 8
    assert [t["tick"] for t in result["dev_wait_ticks"]] == list(range(71, 79))
    assert result["uncertain_release_tick_excluded"] == 70
    assert result["dev_fatigue_before"] == 0.5
    assert result["dev_fatigue_after"] == pytest.approx(0.0)
    assert result["dev_fatigue_recovered"] == pytest.approx(0.5)
    assert result["dev_fatigue_initial_origin"].startswith("EXPLICIT_DEV_SEEDED")
    assert result["source_bound_tick"] is None
    assert result["wait_ticks_admitted"] == 0
    assert result["p1_fatigue_recovered"] == 0
    assert not result["world_run_verified"]
    assert not result["qualification_go"]
    assert not result["science_go"]


@pytest.mark.parametrize("bad", [
    "original_not_pass", "not_two_actions", "no_clear",
    "foreign_session", "foreign_world", "wrong_player",
    "missing_tick", "duplicate_complete", "input_active",
    "moved", "abort", "old_run", "missing_server_input",
    "fake_authority", "wrong_post_tick", "no_recovery_profile",
])
def test_bad_native_or_paper_cannot_be_replayed(monkeypatch, bad):
    native, paper = sources(monkeypatch)
    if bad == "original_not_pass":
        native["status"] = "FAIL"
    elif bad == "not_two_actions":
        native["actual_native_actions"].pop()
    elif bad == "no_clear":
        native["actual_native_actions"][-1]["execution_evidence"][
            "cleanup_receipt"]["result"] = "rejected"
    elif bad == "foreign_session":
        native["session_id"] = "foreign-session"
    elif bad == "foreign_world":
        paper = paper.replace("world=" + WORLD, "world=foreign", 1)
    elif bad == "wrong_player":
        paper = paper.replace("player_uuid=" + PLAYER, "player_uuid=bad", 1)
    elif bad == "missing_tick":
        paper = "".join(line for line in paper.splitlines(keepends=True)
                        if "index=5 " not in line)
    elif bad == "duplicate_complete":
        paper += paper.splitlines(keepends=True)[-1]
    elif bad == "input_active":
        paper = "".join(line.replace("input_idle=true", "input_idle=false")
                        if "index=4 " in line else line
                        for line in paper.splitlines(keepends=True))
    elif bad == "moved":
        paper += "S49_DEV_BACK_WAIT_ABORT reason=SELF_MOVEMENT_EVENT_DURING_OBSERVATION\n"
    elif bad == "abort":
        paper += "S49_DEV_BACK_WAIT_ABORT reason=INPUT_RESUMED\n"
    elif bad == "old_run":
        paper += paper
    elif bad == "missing_server_input":
        paper = "".join(line for line in paper.splitlines(keepends=True)
                        if "S49_OBSERVER_SERVER_INPUT " not in line)
    elif bad == "fake_authority":
        paper = paper.replace("authority=NONE", "authority=ATTESTED")
    elif bad == "wrong_post_tick":
        paper = paper.replace("last_tick=78", "last_tick=79")
    else:
        with pytest.raises(BoundaryRejected):
            review_postaction_wait_dev(
                native, paper, expected_player_uuid=PLAYER,
                profile=FatigueProfile(enabled=True, initial=0.0),
            )
        return
    with pytest.raises(BoundaryRejected):
        evaluate(native, paper)


def test_offline_uuid_is_stable_and_name_pinned():
    from adapters.mineflayer.s31a_real_server_ci import BOT_USERNAME

    assert offline_uuid(BOT_USERNAME) == offline_uuid(BOT_USERNAME)
    assert len(offline_uuid(BOT_USERNAME)) == 36


def test_dev_runner_denies_missing_operator_confirmation_without_world(tmp_path):
    output = tmp_path / "world-first"
    server = tmp_path / "paper.jar"
    plugin = tmp_path / "plugin.jar"
    server.write_bytes(b"not-a-real-paper-server")
    plugin.write_bytes(b"not-a-real-observer")
    result = asyncio.run(run(
        output, server, hashlib.sha256(server.read_bytes()).hexdigest(),
        plugin, hashlib.sha256(plugin.read_bytes()).hexdigest(),
        confirmation=CONFIRM + "-wrong",
    ))
    assert result == 2
    assert not output.exists()


def test_no_source_or_world_mutation_in_passive_join():
    source = Path(__file__).parents[1] / "adapters/mineflayer"
    code = (source / "s49_paper_postwait_dev.py").read_text()
    assert "execute_mineflayer_command(" not in code
    assert "SourceBoundTick(" not in code
    assert "p1_fatigue_recovered" in code


def test_disposable_paper_asset_and_observer_are_staged_without_java(
    monkeypatch, tmp_path,
):
    """Fake only the outer S49 runner; do not launch Java, Node or a World."""
    paper = tmp_path / "paper.jar"
    plugin = tmp_path / "plugin.jar"
    paper.write_bytes(b"synthetic-paper-asset-no-launch")
    plugin.write_bytes(b"synthetic-observer-asset-no-launch")
    output = tmp_path / "fresh-s49-paper"
    seen = []

    async def fake_original_qualify(report_path, server_log):
        from pathlib import Path as P

        world = tmp_path / "owned-fake-world"
        world.mkdir()
        staged = world / "minecraft.jar"
        receipt = original_s49._fetch_official_server(staged)
        assert receipt["runtime"] == "PAPER_1_21_8_DISPOSABLE_DEV"
        original_s49._write_config(world)
        assert staged.read_bytes() == paper.read_bytes()
        observer = world / "plugins" / "s49-wait-observer-dev.jar"
        assert observer.read_bytes() == plugin.read_bytes()
        settings = (world / "plugins" / "RelayS49WaitObserverDev"
                    / "config.yml").read_text()
        assert "enabled: true" in settings
        assert "expected-player-name: RelaySelf" in settings
        assert P(report_path).parent == output
        assert P(server_log).parent == output
        seen.append("original-s49-called-with-paper")
        # Intentionally no native outcome: a fake should never become World PASS.
        return 2

    monkeypatch.setattr(original_s49, "qualify", fake_original_qualify)
    # Config fixture writes to a temp path only; no actual Minecraft process.
    status = asyncio.run(run(
        output, paper, hashlib.sha256(paper.read_bytes()).hexdigest(),
        plugin, hashlib.sha256(plugin.read_bytes()).hexdigest(),
        confirmation=CONFIRM,
    ))
    assert status == 2
    assert seen == ["original-s49-called-with-paper"]
    receipt = json.loads((output / "world_first_dev_report.json").read_text())
    assert receipt["classification"] == "DEV_ONLY"
    assert receipt["qualification_go"] is False
    assert receipt["science_go"] is False
    assert receipt["p1_production_state_updated"] is False
