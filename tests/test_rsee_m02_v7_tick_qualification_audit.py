"""R one-shot new plugin qualification negatives; no Minecraft execution."""
from pathlib import Path

import pytest

from experiments.standard_env import m02_v7_tick_qualification_audit as q


def test_new_scope_is_distinct_from_consumed_previous_qualification():
    assert q.PINS["relay-metabolism-paper-dev.jar"] == (
        "a43afa4d0a1fdaf01c633efd2543ed24b6b53b12ee38ed62a33594057e701e8f"
    )
    assert q.PINS["config.yml"] == (
        "939c2da60ed4ce2f5afb5609c1f784886e3b021104c28a83658c17b744159b16"
    )
    assert q.GRANT == "USER_M02_V7_TICK_CHORD_BASE_ON_20261016_ONCE"
    assert q.PASS != "M02_RSEE_PAPER_CANDIDATE_ENGINEERING_QUALIFIED"


def test_absent_physical_source_is_never_qualified(tmp_path: Path):
    root=tmp_path/"qual"
    assets=tmp_path/"assets"
    root.mkdir()
    assets.mkdir()
    witness=tmp_path/"host.json"
    witness.write_text("{}",encoding="utf-8")
    with pytest.raises(q.NotQualified,match="missing/aliased original"):
        q.review(root,assets,witness,"38905000000")


def test_fake_predeclared_source_does_not_qualify(tmp_path: Path):
    root=tmp_path/"qual"
    assets=tmp_path/"assets"
    root.mkdir()
    assets.mkdir()
    (root/"qualification_producer.json").write_text(
        '{"classification":"S_M02_V7_TICK_CHORD_QUAL_SOURCE_CLOSED_R_REVIEW_REQUIRED",'
        '"authorization_consumed":true,"qual_engineering":true}',encoding="utf-8")
    witness=tmp_path/"host.json"
    witness.write_text('{"java_absent":true,"node_absent":true}',
                       encoding="utf-8")
    with pytest.raises(q.NotQualified):
        q.review(root,assets,witness,"38905000000")


def test_original_file_alias_denied(tmp_path: Path):
    root=tmp_path/"root"
    root.mkdir()
    outside=tmp_path/"original"
    outside.write_text("fake",encoding="utf-8")
    (root/"qualification_producer.json").symlink_to(outside)
    with pytest.raises(q.NotQualified,match="aliased"):
        q.original(root,"qualification_producer.json")


def test_duplicate_or_noncanonical_credential_never_admitted():
    with pytest.raises(q.NotQualified):
        q.need(False,"wrong physical grant")
    assert q.FAIL.endswith("FAILED_OR_UNDETERMINED")

def test_official_paper_jar_over_20mb_remains_bounded_and_accepted(tmp_path: Path):
    """Regression: old 20 MiB cap falsely rejected genuine 52,811,717-byte Paper."""
    jar = tmp_path / "paper-1.21.8.jar"
    with jar.open("wb") as handle:
        handle.truncate(52_811_717)
    assert len(q.original(tmp_path, jar.name)) == 52_811_717


def test_non_paper_original_cannot_bypass_20mb_limit(tmp_path: Path):
    oversized = tmp_path / "source_plugin.jar"
    with oversized.open("wb") as handle:
        handle.truncate(20 * 1024 * 1024)
    with pytest.raises(q.NotQualified, match="oversize"):
        q.original(tmp_path, oversized.name)
