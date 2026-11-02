"""Z1 one physical World entry preflight: OFFLINE fake assets/no Java/Node."""
from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest

from tools import l_zombie_z1_one_world_dev as runner


def fixture_bundle(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    world = tmp_path / "worlds"
    world.mkdir()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    paper = tmp_path / "paper.jar"
    paper.write_bytes(b"paper-test-fixture")
    plugin = tmp_path / runner.EXPECTED_PLUGIN
    plugin.write_bytes(b"plugin-test-fixture")
    monkeypatch.setattr(runner, "PAPER_SHA256", hashlib.sha256(paper.read_bytes()).hexdigest())
    monkeypatch.setattr(runner, "PAPER_SIZE", paper.stat().st_size)
    monkeypatch.setattr(runner, "_clean_head", lambda *args: None)
    monkeypatch.setattr(runner, "_loopback_port_can_bind", lambda port: True)
    monkeypatch.setenv("L_ZOMBIE_Z1_ONE_WORLD_DEV", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    return {
        "confirm": runner.CONFIRM, "repo": repo, "expected_head": "a"*40,
        "paper_jar": paper, "plugin_jar": plugin,
        "plugin_sha256": runner._sha256(plugin),
        "world_parent": world, "evidence_parent": evidence,
        "run_id": "0123456789abcdef",
    }


def test_offline_one_world_asset_and_new_root_preflight(tmp_path, monkeypatch):
    args = fixture_bundle(tmp_path, monkeypatch)
    receipt = runner.preflight(**args)
    assert receipt["classification"] == "Z1_PREWORLD_SOURCE_ONLY"
    assert receipt["world_budget_max"] == 1 and receipt["world_retries_max"] == 0
    assert receipt["real_gemma_calls"] == receipt["self_actions"] == 0
    assert sorted(args["world_parent"].iterdir()) == []
    assert sorted(args["evidence_parent"].iterdir()) == []


@pytest.mark.parametrize("change", [
    {"confirm": "UNAUTHORIZED"},
    {"run_id": "non-unique"},
    {"plugin_sha256": "b"*64},
    {"expected_head": "broken"},
])
def test_invalid_run_inputs_prevent_any_java_spawn(tmp_path, monkeypatch, change):
    args = fixture_bundle(tmp_path, monkeypatch)
    args.update(change)
    if "expected_head" in change:
        monkeypatch.setattr(
            runner, "_clean_head",
            lambda *a: (_ for _ in ()).throw(runner.ZombieWorldBlocked("HEAD")),
        )
    with pytest.raises(runner.ZombieWorldBlocked):
        runner.preflight(**args)
    assert list(args["world_parent"].iterdir()) == []


def test_stale_world_and_evidence_roots_are_rejected(tmp_path, monkeypatch):
    args = fixture_bundle(tmp_path, monkeypatch)
    (args["world_parent"] / f"l-z1-world-{args['run_id']}").mkdir()
    with pytest.raises(runner.ZombieWorldBlocked, match="root"):
        runner.preflight(**args)
    (args["world_parent"] / f"l-z1-world-{args['run_id']}").rmdir()
    (args["evidence_parent"] / f"l-z1-evidence-{args['run_id']}").mkdir()
    with pytest.raises(runner.ZombieWorldBlocked, match="root"):
        runner.preflight(**args)


def test_absent_opt_in_node_substitution_and_port_busy_are_refused(tmp_path, monkeypatch):
    args = fixture_bundle(tmp_path, monkeypatch)
    monkeypatch.delenv("L_ZOMBIE_Z1_ONE_WORLD_DEV")
    with pytest.raises(runner.ZombieWorldBlocked):
        runner.preflight(**args)
    monkeypatch.setenv("L_ZOMBIE_Z1_ONE_WORLD_DEV", "1")
    monkeypatch.setenv("NODE_OPTIONS", "--require fakes")
    with pytest.raises(runner.ZombieWorldBlocked):
        runner.preflight(**args)
    monkeypatch.delenv("NODE_OPTIONS")
    monkeypatch.setattr(runner, "_loopback_port_can_bind", lambda port: False)
    with pytest.raises(runner.ZombieWorldBlocked):
        runner.preflight(**args)


def test_default_paper_profile_only_two_activation_flags():
    default = (
        "dev-enabled: false\n"
        "zombie-tick-readonly-dev: false\n"
        "minecraft-version: 1.21.8\n"
    )
    active = runner.active_plugin_config(default)
    assert active == (
        "dev-enabled: true\n"
        "zombie-tick-readonly-dev: true\n"
        "minecraft-version: 1.21.8\n"
    )
    for bad in (
        default.replace("1.21.8", "1.21.9"),
        default.replace("dev-enabled: false", "dev-enabled: true"),
        default.replace(
            "zombie-tick-readonly-dev: false", "zombie-tick-readonly-dev: true"
        ),
    ):
        with pytest.raises(runner.ZombieWorldBlocked):
            runner.active_plugin_config(bad)


def test_raw_window_following_single_original_collector(tmp_path):
    raw = tmp_path / "paper-console-original.log"
    raw.write_text(
        "[01:00:00 INFO]: L_ZOMBIE_ARM_V1 marker=z1-source-1 session=z1-client-1\n"
        "[01:00:02 INFO]: L_ZOMBIE_END_V1 marker=z1-source-1 "
        "session=z1-client-1 result=PAPER_WINDOW_COMPLETE samples=31 last_offset=30\n"
    )
    asyncio.run(runner.wait_original_window(
        raw, marker=runner.MARKER, session=runner.SESSION, timeout_s=2,
    ))


def test_early_zombie_loss_cannot_be_reported_complete(tmp_path):
    raw = tmp_path / "paper-console-original.log"
    raw.write_text(
        "[01:00:02 INFO]: L_ZOMBIE_END_V1 marker=z1-source-1 "
        "session=z1-client-1 result=ENTITY_REMOVED samples=10 last_offset=9\n"
    )
    with pytest.raises(runner.ZombieWorldBlocked):
        asyncio.run(runner.wait_original_window(
            raw, marker=runner.MARKER, session=runner.SESSION, timeout_s=2,
        ))


def test_paper_plugin_staging_is_isolated_to_new_world(tmp_path, monkeypatch):
    args = fixture_bundle(tmp_path, monkeypatch)
    repo = args["repo"]
    config_path = repo / (
        "adapters/mineflayer/l_zombie_paper_dev/src/main/resources/config.yml"
    )
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "dev-enabled: false\nzombie-tick-readonly-dev: false\n"
        "minecraft-version: 1.21.8\n"
    )
    root = args["world_parent"] / "new"
    root.mkdir()
    evid = args["evidence_parent"] / "new"
    evid.mkdir()
    runner._set_up_world(
        repo=repo, world_root=root, evidence_root=evid,
        plugin_jar=args["plugin_jar"],
    )
    assert (root / "plugins" / runner.EXPECTED_PLUGIN).read_bytes() == b"plugin-test-fixture"
    original = (evid / "activated-paper-plugin-original.yml").read_text()
    assert (root / "plugins/RelayZombieTickDev/config.yml").read_text() == original
    assert "dev-enabled: true" in original
    assert "zombie-tick-readonly-dev: true" in original
    assert "server-ip=127.0.0.1" in (root / "server.properties").read_text()


def test_real_one_world_entry_is_not_started_by_any_source_import():
    assert runner.CONFIRM.startswith("Z1_ONE")
    assert runner.PAPER_SHA256 == "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e"
    assert runner.EXPECTED_PLUGIN.endswith(".jar")



def test_pursuit_mode_requires_independent_explicit_single_world_grant(tmp_path, monkeypatch):
    args = fixture_bundle(tmp_path, monkeypatch)
    args["pursuit_dev"] = True
    with pytest.raises(runner.ZombieWorldBlocked, match="pursuit"):
        runner.preflight(**args)
    monkeypatch.setenv("L_ZOMBIE_Z1_PURSUIT_DEV", "1")
    with pytest.raises(runner.ZombieWorldBlocked, match="pursuit"):
        runner.preflight(**args)
    args["confirm"] = runner.PURSUIT_CONFIRM
    receipt = runner.preflight(**args)
    assert receipt["pursuit_dev"] is True
    assert receipt["real_gemma_calls"] == 0
    assert receipt["world_retries_max"] == 0
    args["confirm"] = runner.CONFIRM
    args["pursuit_dev"] = False
    assert runner.preflight(**args)["pursuit_dev"] is False
    assert list(args["world_parent"].iterdir()) == []


def test_pursuit_world_uses_only_bounded_survival_target_readonly_zombie_controls():
    from inspect import getsource
    source = getsource(runner.one_world)
    assert "if pursuit_dev:" in source
    assert 'effect give RelaySelf minecraft:resistance 90 4 true' in source
    assert 'effect give RelaySelf minecraft:regeneration 90 4 true' in source
    assert 'gamemode survival RelaySelf' in source
    assert "summon minecraft:zombie" in source
    assert "NoAI:0b,PersistenceRequired:1b" in source
    assert "self_actions" in source
    assert '"zombie_pursuit_attested"] = False' in source
    assert "displacement > 0.02" in source
    assert "Z1B_PAPER_SOURCE_PASS_MOTION_NOT_OBSERVED" in source



def test_z2a_prospective_cheap_requires_new_specific_one_world_grant(tmp_path, monkeypatch):
    args = fixture_bundle(tmp_path, monkeypatch)
    args.update(pursuit_dev=True, prospective_cheap_dev=True)
    monkeypatch.delenv("L_ZOMBIE_Z2A_CHEAP_DEV", raising=False)
    monkeypatch.setenv("L_ZOMBIE_Z1_PURSUIT_DEV", "1")
    with pytest.raises(runner.ZombieWorldBlocked, match="pursuit"):
        runner.preflight(**args)
    args["confirm"] = runner.PROSPECTIVE_CONFIRM
    with pytest.raises(runner.ZombieWorldBlocked, match="pursuit"):
        runner.preflight(**args)
    monkeypatch.setenv("L_ZOMBIE_Z2A_CHEAP_DEV", "1")
    r = runner.preflight(**args)
    assert r["prospective_cheap_dev"]
    assert r["world_budget_max"] == 1 and r["world_retries_max"] == 0
    args["pursuit_dev"] = False
    with pytest.raises(runner.ZombieWorldBlocked):
        runner.preflight(**args)
    assert list(args["world_parent"].iterdir()) == []


def test_z2a_activates_new_flag_only_for_new_world():
    default = (
        "dev-enabled: false\n"
        "zombie-tick-readonly-dev: false\n"
        "zombie-prospective-cheap-dev: false\n"
        "minecraft-version: 1.21.8\n"
    )
    old = runner.active_plugin_config(default)
    assert "zombie-prospective-cheap-dev: false" in old
    new = runner.active_plugin_config(default, prospective_cheap_dev=True)
    assert "zombie-prospective-cheap-dev: true" in new
    with pytest.raises(runner.ZombieWorldBlocked):
        runner.active_plugin_config(
            default.replace("zombie-prospective-cheap-dev: false", ""),
            prospective_cheap_dev=True,
        )



def test_z2b_real_prepared_policy_preflight_denies_missing_new_flag(tmp_path, monkeypatch):
    from test_l_zombie_z2b_policy_contract import frozen

    args = fixture_bundle(tmp_path, monkeypatch)
    args.update(
        confirm=runner.PREPARED_CONFIRM,
        pursuit_dev=True, prospective_cheap_dev=True,
        prepared_l2_root=tmp_path / "prepared",
        z1b_prior_original=tmp_path / "z1b.raw",
        z2a_prior_original=tmp_path / "z2a.raw",
    )
    monkeypatch.setenv("L_ZOMBIE_Z1_PURSUIT_DEV", "1")
    monkeypatch.setenv("L_ZOMBIE_Z2A_CHEAP_DEV", "1")
    calls = []
    monkeypatch.setattr(runner, "verify_prepared_archive", lambda **kw: (
        calls.append(kw) or frozen()
    ))
    with pytest.raises(runner.ZombieWorldBlocked):
        runner.preflight(**args)
    assert calls == []
    monkeypatch.setenv("L_ZOMBIE_Z2B_PREPARED_DEV", "1")
    r = runner.preflight(**args)
    assert r["prepared_l2_policy_sha256"] == frozen().policy_sha256
    assert len(calls) == 1
    assert r["world_retries_max"] == 0
    args["prepared_l2_root"] = None
    with pytest.raises(runner.ZombieWorldBlocked):
        runner.preflight(**args)


def test_z2b_config_stages_verified_prepared_policy_without_new_world_action(tmp_path, monkeypatch):
    from test_l_zombie_z2b_policy_contract import frozen

    args = fixture_bundle(tmp_path, monkeypatch)
    repo = args["repo"]
    path = repo / (
        "adapters/mineflayer/l_zombie_paper_dev/src/main/resources/config.yml"
    )
    path.parent.mkdir(parents=True)
    path.write_text(
        'dev-enabled: false\n'
        'zombie-tick-readonly-dev: false\n'
        'zombie-prospective-cheap-dev: false\n'
        'minecraft-version: 1.21.8\n'
        'zombie-prepared-l2-shadow-dev: false\n'
        'zombie-prepared-l2-strategy: "ABSTAIN"\n'
        'zombie-prepared-l2-speed-m-per-tick: "none"\n'
        'zombie-prepared-l2-policy-sha256: "none"\n'
    )
    world_root = args["world_parent"] / "new"
    world_root.mkdir()
    evidence_root = args["evidence_parent"] / "new"
    evidence_root.mkdir()
    p = frozen()
    runner._set_up_world(
        repo=repo, world_root=world_root, evidence_root=evidence_root,
        plugin_jar=args["plugin_jar"],
        prospective_cheap_dev=True, prepared_l2_policy=p,
    )
    settings = (world_root / "plugins/RelayZombieTickDev/config.yml").read_text()
    assert "zombie-prepared-l2-shadow-dev: true" in settings
    assert p.policy_sha256 in settings
    assert 'zombie-prepared-l2-strategy: "TARGET_APPROACH"' in settings
    assert "zombie-prospective-cheap-dev: true" in settings
    assert "zombie-prepared-l2-shadow-dev: false" not in settings
    assert list(args["world_parent"].iterdir()) == [world_root]
    assert list(args["evidence_parent"].iterdir()) == [evidence_root]
