"""S5 pure stopped-native-NBT threat-opportunity admission tests.

Synthetic stopped-world NBT is NOT qualified #583 physical evidence.
No Java/Node/Minecraft, GPU, LLM POST, Action, new snapshot or World write.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from adapters.mineflayer import self_s5_world_opportunity as s5
from test_rsee_world_bootstrap import _comp, _root, _str, _tag


def _fixture_rule(tmp_path, value: str):
    saved = tmp_path / "snapshot"
    saved.mkdir()
    (saved / "level.dat").write_bytes(
        _root(_comp("Data", _comp(
            "GameRules", _tag(8, "doMobSpawning", _str(value)),
        )))
    )
    return saved


@pytest.mark.parametrize("rule,classification", [
    ("false", "FROZEN_WORLD_NATURAL_MOB_SPAWNING_DISABLED"),
    ("true", "NATURAL_MOB_SPAWNING_RULE_ENABLED_TARGET_UNPROVEN"),
])
def test_exact_saved_rule_never_grants_physical_opportunity(
    tmp_path, monkeypatch, rule, classification,
):
    root = tmp_path / "rsee"
    root.mkdir()
    saved = _fixture_rule(tmp_path, rule)
    manifest_digest = "a" * 64
    seen = []

    def fake_qualified(jar, snapshot, manifest, initial):
        seen.append((jar, snapshot, manifest, initial))
        assert snapshot == root / "bootstrap-approved-20261011-once" / "snapshot"
        return SimpleNamespace(snapshot=saved, manifest_sha256=manifest_digest)

    monkeypatch.setattr(s5, "RSEE", root)
    monkeypatch.setattr(s5, "verify_qualified_world", fake_qualified)
    record = s5.assess_qualified_rsee_world(root)
    assert len(seen) == 1
    assert record.classification == classification
    assert record.do_mob_spawning == rule
    assert record.world_identity == manifest_digest
    assert record.natural_zombie_spawn_opportunity_qualified is False
    assert record.existing_zombie_absence_proven is False
    assert record.world_wide_entity_coverage_proven is False
    assert not record.physical_execution_authorized
    assert record.minecraft_sessions_started == record.llm_posts == 0
    assert record.action_authority is False
    assert record.learning_or_habit_qualified is False


@pytest.mark.parametrize("invalid", ["disabled", "0", "False", "", "not-present"])
def test_native_missing_or_nonstandard_rule_is_blocked(tmp_path, invalid):
    if invalid == "not-present":
        saved = tmp_path / "snapshot"
        saved.mkdir()
        (saved / "level.dat").write_bytes(_root(_comp("Data", _comp("GameRules", b""))))
    else:
        saved = _fixture_rule(tmp_path, invalid)
    with pytest.raises(s5.OpportunityRejected):
        s5.read_stopped_world_gamerule(saved)


def test_missing_native_level_and_wrong_identity_fail_closed(tmp_path, monkeypatch, capsys):
    missing = tmp_path / "missing"
    with pytest.raises(s5.OpportunityRejected):
        s5.read_stopped_world_gamerule(missing)
    root = tmp_path / "rsee"
    root.mkdir()
    monkeypatch.setattr(s5, "RSEE", root)

    def reject(*_):
        raise s5.WorldBindingRejected("not the #583 receipt")

    monkeypatch.setattr(s5, "verify_qualified_world", reject)
    assert s5.main(["--rsee-root", str(root)]) == 2
    row = json.loads(capsys.readouterr().out)
    assert row["classification"] == "S5_WORLD_OPPORTUNITY_UNKNOWN_BLOCKED"
    assert row["minecraft_sessions_started"] == 0
    assert row["natural_zombie_spawn_opportunity_qualified"] is False


def test_world_diagnostic_is_not_a_replacement_asset_or_unverified_world(tmp_path):
    with pytest.raises(s5.OpportunityRejected, match="canonical"):
        s5.assess_qualified_rsee_world(tmp_path)
    with pytest.raises(s5.OpportunityRejected):
        s5.read_stopped_world_gamerule("not-a-path")


def test_cli_is_only_original_stopped_world_inspection(tmp_path, monkeypatch, capsys):
    root = tmp_path / "rsee"
    root.mkdir()
    saved = _fixture_rule(tmp_path, "false")
    monkeypatch.setattr(s5, "RSEE", root)

    def verified(*_):
        return SimpleNamespace(snapshot=saved, manifest_sha256="b" * 64)

    monkeypatch.setattr(s5, "verify_qualified_world", verified)
    assert s5.main(["--rsee-root", str(root)]) == 0
    row = json.loads(capsys.readouterr().out)
    assert row["classification"] == "FROZEN_WORLD_NATURAL_MOB_SPAWNING_DISABLED"
    assert row["physical_execution_authorized"] is False
    assert row["minecraft_sessions_started"] == 0
    assert row["llm_posts"] == 0
