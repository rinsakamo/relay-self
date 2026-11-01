"""H9a preserved real A/B configs: forensic differences do NOT change pair gate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from relay_self.l_bcg_h9a_config_forensics import (
    ConfigForensicsRejected,
    compare_h9a_archived_generated_timestamp,
)
from tools.l_bcg_h9a_config_forensics import _arm

ROOT = (
    Path(__file__).resolve().parents[1] / "docs/evidence"
    / "l-bcg-h9a-20261101"
)


def _preserved():
    return {**_arm(ROOT / "a", "a"), **_arm(ROOT / "b", "b")}


def _rebind_one_modified_config(inp: dict, prefix: str, mutated: bytes):
    """Simulate forged coordinated manifests and still reject non-date edits."""
    inp[prefix + "_config_original"] = mutated
    raw_manifest = json.loads(inp[prefix + "_runtime_assets_original"])
    original_manifest = json.loads(inp[prefix + "_original_sha256_manifest"])
    entry = next(k for k in raw_manifest if k.endswith("/server.properties"))
    sha = hashlib.sha256(mutated).hexdigest()
    raw_manifest[entry]["sha256"] = sha
    raw = json.dumps(raw_manifest, separators=(",", ":")).encode()
    original_manifest["runtime-config/server.properties"] = sha
    original_manifest["runtime-assets-sha256.json"] = hashlib.sha256(raw).hexdigest()
    inp[prefix + "_runtime_assets_original"] = raw
    inp[prefix + "_original_sha256_manifest"] = json.dumps(
        original_manifest, separators=(",", ":")
    ).encode()


def test_h9a_real_archived_only_timestamp_line_differs_but_pair_remains_rejected():
    x = compare_h9a_archived_generated_timestamp(**_preserved())
    assert x.raw_sha_a == "dbcae461ab304682b8d97d7876de46748501ad9fab83300387d4218f5743487c"
    assert x.raw_sha_b == "288b1cfb719d2b6d8c964cc37b77fffd5b708e7e9d988445c7e8731898748c36"
    assert x.byte_diff_line_numbers == (2,)
    assert x.only_generated_timestamp_line_differs
    assert x.other_critical_asset_sha_equal
    assert x.independent_original_manifest_per_arm_checked
    assert x.original_pair_raw_sha_gate == "REJECTED_AS_PREDECLARED"
    assert not x.changes_original_pair_decision
    assert x.supplementary_classification == "POSTHOC_CONFIG_TIMESTAMP_ONLY_DIAGNOSTIC_NOT_PAIR_PASS"
    assert x.extra_worlds == x.additional_actions == x.qualified_training_worlds == 0
    assert x.qualification == "NO_GO" and x.science == "NOT_RUN"


@pytest.mark.parametrize("target", [
    "a_config_original", "a_runtime_assets_original",
    "a_original_sha256_manifest", "b_config_original",
    "b_runtime_assets_original", "b_original_sha256_manifest",
])
def test_tampered_preserved_original_manifest_source_rejected(target):
    d = _preserved()
    d[target] += b"\x00forged"
    with pytest.raises(ConfigForensicsRejected):
        compare_h9a_archived_generated_timestamp(**d)


@pytest.mark.parametrize("mutation", [
    "change_port", "change_gamemode", "change_s42_unrelated_config",
    "insert_comment", "drop_header", "rename_header",
    "different_line_ending", "missing_timestamp", "bad_timestamp",
    "delete_property", "duplicate_property", "reorder_property",
])
def test_even_coordinated_forged_manifests_cannot_hide_other_config_changes(mutation):
    d = _preserved()
    original = d["b_config_original"]
    if mutation == "change_port":
        new = original.replace(b"server-port=25565", b"server-port=25566")
    elif mutation == "change_gamemode":
        new = original.replace(b"gamemode=creative", b"gamemode=survival")
    elif mutation == "change_s42_unrelated_config":
        new = original.replace(b"spawn-monsters=true", b"spawn-monsters=false")
    elif mutation == "insert_comment":
        new = original.replace(b"difficulty=easy", b"#random\ndifficulty=easy")
    elif mutation == "drop_header":
        new = original.split(b"\n", 1)[1]
    elif mutation == "rename_header":
        new = original.replace(b"#Minecraft server properties", b"#Other server properties")
    elif mutation == "different_line_ending":
        new = original.replace(b"\n", b"\r\n")
    elif mutation == "missing_timestamp":
        new = original.replace(b"#Sun Nov 01 16:10:48 JST 2026\n", b"")
    elif mutation == "bad_timestamp":
        new = original.replace(b"#Sun Nov 01 16:10:48 JST 2026", b"#not a timestamp")
    elif mutation == "delete_property":
        new = original.replace(b"spawn-monsters=true\n", b"")
    elif mutation == "duplicate_property":
        new = original.replace(b"spawn-monsters=true\n", b"spawn-monsters=true\nspawn-monsters=true\n")
    else:
        new = original.replace(
            b"spawn-monsters=true\nspawn-protection=0\n",
            b"spawn-protection=0\nspawn-monsters=true\n",
        )
    assert new != original
    _rebind_one_modified_config(d, "b", new)
    with pytest.raises(ConfigForensicsRejected):
        compare_h9a_archived_generated_timestamp(**d)


def test_source_manifest_cannot_launder_non_config_asset_change():
    d = _preserved()
    assets = json.loads(d["b_runtime_assets_original"])
    original_manifest = json.loads(d["b_original_sha256_manifest"])
    path = next(k for k in assets if k.endswith("/minecraft.jar"))
    assets[path]["sha256"] = "0" * 64
    raw = json.dumps(assets).encode()
    original_manifest["runtime-assets-sha256.json"] = hashlib.sha256(raw).hexdigest()
    d["b_runtime_assets_original"] = raw
    d["b_original_sha256_manifest"] = json.dumps(original_manifest).encode()
    with pytest.raises(ConfigForensicsRejected, match="other critical"):
        compare_h9a_archived_generated_timestamp(**d)


def test_previous_pair_rejection_record_remains_unchanged():
    reject = json.loads((ROOT / "pair/result-rejected.json").read_bytes())
    assert reject["classification"] == "H9A_PAIR_REJECTED_RUNTIME_SHA_MISMATCH"
    assert reject["exploratory_pair_pass"] is False
    assert reject["qualified_training_worlds"] == 0
