"""Paper sidecar S49 source-only safety/packaging contract checks.

These tests intentionally DO NOT compile, install or run the Java plugin;
they cannot establish Paper API compatibility, runtime ownership or W4 proof.
"""
from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from test_s49_paper_backward_wait_dev import raw_paper, run, typed_owner

ROOT = (
    Path(__file__).resolve().parents[1]
    / "adapters/mineflayer/s49_paper_wait_observer_dev"
)
JAVA = (
    ROOT / "src/main/java/io/github/rinsakamo/relays49observer"
    / "S49WaitObserverPlugin.java"
)


def test_standalone_plugin_default_disabled_and_no_world_runner_edits():
    xml = ElementTree.parse(ROOT / "pom.xml").getroot()
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}
    assert xml.findtext("m:artifactId", namespaces=ns) == (
        "relay-s49-wait-observer-dev"
    )
    assert xml.findtext("m:properties/m:maven.compiler.release", namespaces=ns) == (
        "21"
    )
    assert xml.findtext("m:dependencies/m:dependency/m:version", namespaces=ns) == (
        "1.21.8-R0.1-SNAPSHOT"
    )
    config = (ROOT / "src/main/resources/config.yml").read_text()
    plugin = (ROOT / "src/main/resources/plugin.yml").read_text()
    assert "enabled: false" in config
    assert "expected-player-name: RelaySelf" in config
    assert "name: RelayS49WaitObserverDev" in plugin
    assert "S49WaitObserverPlugin" in plugin
    assert "relays49observe:" in plugin
    assert "load: POSTWORLD" in plugin


def test_java_source_is_console_opt_in_one_shot_sync_observation_only():
    source = JAVA.read_text(encoding="utf-8")
    assert "sender instanceof ConsoleCommandSender" in source
    assert "!Bukkit.isPrimaryThread()" in source
    assert '!getConfig().getBoolean("enabled", false)' in source
    assert "used || active || args.length != 3" in source
    assert "used = true;" in source
    assert "active = true;" in source
    assert source.index("used = true;") < source.index(
        'getLogger().info("S49_DEV_BACK_WAIT_BEGIN "'
    )
    assert "subject.getUniqueId().equals(parsedPlayer)" in source
    assert "subject.getName().equals(expectedName)" in source
    assert "subject.getWorld().getFullTime()" in source
    assert 'private static final int SAMPLE_COUNT = 8;' in source
    assert "tick != beginTick + next" in source
    assert "runTaskTimer(" in source
    assert "1L, 1L" in source
    assert "runTaskTimerAsynchronously" not in source
    assert "S49_DEV_BACK_WAIT_BEGIN" in source
    assert "S49_DEV_BACK_WAIT_TICK" in source
    assert "S49_DEV_BACK_WAIT_ABORT" in source
    assert "OBSERVER_START_FAILED" in source
    assert "PLUGIN_DISABLED" in source
    assert "S49_OBSERVER_SUBJECT" in source
    assert "S49_OBSERVER_SERVER_INPUT" in source
    assert "input_idle=true" in source
    assert "s49_release_causality=NOT_ATTESTED" in source
    assert "subject.getCurrentInput()" in source
    assert "idleInput(event.getInput())" in source
    assert "EventPriority.MONITOR" in source
    assert "ignoreCancelled = false" in source
    assert "samePosition(event.getFrom(), event.getTo())" in source
    assert "samePosition(subject.getLocation(), startingLocation)" in source
    assert "registerEvents(this, this)" in source
    assert "SERVER_INPUT_ACTIVE_AT_START" in source
    assert "SERVER_INPUT_ACTIVE_AT_CALLBACK" in source
    assert "SERVER_INPUT_ACTIVE_DURING_OBSERVATION" in source
    assert "SELF_MOVEMENT_EVENT_DURING_OBSERVATION" in source
    for disallowed in (
        "setExhaustion(", "setFoodLevel(", "setHealth(",
        "setVelocity(", "teleport(", "setWalkSpeed(",
        "dispatchCommand(", "performCommand(",
        "sendSetControl(", "sendClearControls(",
    ):
        assert disallowed not in source


def test_java_emitted_fields_match_exact_existing_s49_parser():
    source = JAVA.read_text(encoding="utf-8")
    assert '"marker_id=" + marker + " action_id=" + action' in source
    assert '" session_id=" + session + " world=" + worldId' in source
    assert '" tick=" + beginTick + " index=0"' in source
    assert '" tick=" + tick + " index=" + index' in source
    assert "marker = action + \"-\" + session;" in source
    # No extra columns that the current strict Python reader would ignore.
    assert source.count('getLogger().info("S49_DEV_BACK_WAIT_TICK "') == 1


@pytest.mark.parametrize("before_complete", [True, False])
def test_paper_abort_marks_candidate_unusable(
    monkeypatch, tmp_path, before_complete,
):
    capture = typed_owner(monkeypatch)
    original = raw_paper(capture)
    context = (
        "S49_OBSERVER_SUBJECT action_id=untrusted"
        " clear_ack=UNATTESTED_CONSOLE_CLAIM\n"
    )
    abort = (
        "S49_DEV_BACK_WAIT_ABORT marker_id=untrusted"
        " reason=PLUGIN_DISABLED samples=3\n"
    )
    if before_complete:
        lines = original.splitlines(keepends=True)
        paper = context + "".join(lines[:4]) + abort
    else:
        paper = context + original + abort
    destination = tmp_path / "aborted.json"
    with pytest.raises(BoundaryRejected):
        run(capture, paper, destination)
    report = json.loads(destination.read_text())
    assert report["status"] == "REJECTED_NOT_QUALIFIED"
    assert report["wait_interval_ref"] is None
    assert report["p1_fatigue_recovered"] == 0.0


def test_paper_subject_context_alone_is_not_provenance(
    monkeypatch, tmp_path,
):
    capture = typed_owner(monkeypatch)
    claimed = (
        "S49_OBSERVER_SUBJECT action_id=claimed "
        "session_id=claimed player_uuid=00000000-0000-0000-0000-000000000000 "
        "clear_ack=UNATTESTED_CONSOLE_CLAIM\n"
    )
    result = run(
        capture, claimed + raw_paper(capture), tmp_path / "candidate.json",
    )
    assert result["status"] == "SAME_ACTION_PAPER_SHAPE_ONLY"
    assert result["source_authentication"] == "UNATTESTED_CALLER_PAPER_INPUT"
    assert result["whole_tick_self_inactivity"] == "NOT_ATTESTED"
    assert result["wait_ticks_admitted"] == 0
