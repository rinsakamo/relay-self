"""Prospective negative controls for the four nonqualified S50 tick-chord arms.

These fixtures never issue a grant, native Action, Java, World or V trial.
"""
from pathlib import Path

import pytest

from experiments.standard_env import m02_v7_remaining_profile_preflight as gate

REFERENCE = (
    Path(__file__).parent / "fixtures" / "rsee_m02_v7_tick_base_qualified_config.yml"
)


def source() -> bytes:
    return REFERENCE.read_bytes()


def approve_shape(candidate: bytes, arm: str, **substitutions):
    inputs = {
        "plugin_sha256": gate.PLUGIN_SHA256,
        "paper_sha256": gate.PAPER_SHA256,
        "server_properties_sha256": gate.SERVER_PROPERTIES_SHA256,
    }
    inputs.update(substitutions)
    return gate.review_config(source(), candidate, arm=arm, **inputs)


def test_qualified_base_fixture_is_full_original_exact_digest():
    raw = source()
    assert gate.digest(raw) == gate.BASE_CONFIG_SHA256
    assert gate.pinned_base(raw).count("s50-tick-meter-dev: true") == 1


@pytest.mark.parametrize(("arm", "basal", "walk"), [
    ("SHAM_ON", 1, 1),
    ("BASAL_ZERO", 0, 1),
    ("WALK_ZERO", 1, 0),
    ("BOTH_ZERO", 0, 0),
])
def test_four_config_byte_shapes_never_confer_separate_qualification(arm, basal, walk):
    base = source()
    candidate = gate.expected_candidate(base, arm)
    result = approve_shape(candidate, arm)
    assert result["classification"] == gate.CLASS
    assert result["arm"] == arm
    assert result["basal_multiplier"] == basal
    assert result["walk_multiplier"] == walk
    assert result["expected_basal_setter_input_per_player_tick"] == basal * 0.001
    assert result["expected_walk_setter_input_per_observed_tick_chord_block"] == walk * 0.01
    assert result["candidate_config_sha256"] == gate.digest(candidate)
    assert result["identical_config_to_base_on"] == (arm == "SHAM_ON")
    for field in (
        "identical_config_confers_separate_world_qualification",
        "caller_supplied_bytes_independently_authenticated",
        "original_host_stop_attested",
        "fresh_qual_grant_issued",
        "physical_world_launch_authorized",
        "candidate_arm_engineering_qualified",
        "other_arms_engineering_qualified",
        "science_go",
        "production_go",
    ):
        assert result[field] is False, field
    assert result["v7_science_trials_credited"] == 0


def test_sham_same_bytes_still_independent_new_world_and_host_required():
    assert gate.expected_candidate(source(), "SHAM_ON") == source()
    assert gate.BASE_GRANT in gate.CONSUMED_GRANTS
    assert gate.OLD_GRANT in gate.CONSUMED_GRANTS
    assert approve_shape(source(), "SHAM_ON")["candidate_arm_engineering_qualified"] is False


@pytest.mark.parametrize("arm", ["BASE_ON", "UNKNOWN", "", "base_on"])
def test_unregistered_or_already_qualified_base_scope_not_reopened(arm):
    with pytest.raises(gate.ProfileRejected, match="four unqualified"):
        gate.expected_candidate(source(), arm)


@pytest.mark.parametrize("field", [
    "plugin_sha256", "paper_sha256", "server_properties_sha256",
])
def test_foreign_binary_or_server_identity_denied(field):
    candidate = gate.expected_candidate(source(), "BASAL_ZERO")
    with pytest.raises(gate.ProfileRejected, match="unregistered"):
        approve_shape(candidate, "BASAL_ZERO", **{field: "0" * 64})


@pytest.mark.parametrize(("arm", "other"), [
    ("SHAM_ON", "BASAL_ZERO"),
    ("BASAL_ZERO", "WALK_ZERO"),
    ("WALK_ZERO", "BOTH_ZERO"),
    ("BOTH_ZERO", "SHAM_ON"),
])
def test_no_profile_aliasing_or_selection_after_readback(arm, other):
    wrong = gate.expected_candidate(source(), other)
    with pytest.raises(gate.ProfileRejected, match="foreign config"):
        approve_shape(wrong, arm)


@pytest.mark.parametrize("bad", [
    lambda raw: raw + b"\nfree-exhaustion: true\n",
    lambda raw: raw.replace(b"s50-tick-meter-dev: true",
                            b"s50-tick-meter-dev: false"),
    lambda raw: raw.replace(b"additional: 0.0", b"additional: -10", 1),
    lambda raw: raw.replace(b"standard: 0.01", b"standard: 0"),
    lambda raw: raw.replace(b"dev-enabled: true", b"dev-enabled: false"),
    lambda raw: raw.replace(b"target-player: RelaySelf",
                            b"target-player: OtherBot"),
    lambda raw: raw + b"\x00",
])
def test_any_unregistered_cost_world_or_credential_edit_fails_closed(bad):
    candidate = gate.expected_candidate(source(), "WALK_ZERO")
    with pytest.raises(gate.ProfileRejected, match="foreign config"):
        approve_shape(bad(candidate), "WALK_ZERO")


def test_missing_or_tampered_base_identity_is_never_forgiven():
    candidate = gate.expected_candidate(source(), "BOTH_ZERO")
    wrong_reference = source().replace(b"standard-food: cooked_beef",
                                       b"standard-food: gold")
    with pytest.raises(gate.ProfileRejected, match="BASE_ON reference"):
        gate.review_config(
            wrong_reference, candidate, arm="BOTH_ZERO",
            plugin_sha256=gate.PLUGIN_SHA256,
            paper_sha256=gate.PAPER_SHA256,
            server_properties_sha256=gate.SERVER_PROPERTIES_SHA256,
        )


@pytest.mark.parametrize("bad", [b"", b"x" * 8193, None, "text"])
def test_empty_unbounded_or_nonbinary_candidate_denied(bad):
    with pytest.raises(gate.ProfileRejected):
        approve_shape(bad, "SHAM_ON")


def test_relative_or_aliased_source_file_denied(tmp_path):
    candidate = tmp_path / "candidate.yml"
    candidate.write_bytes(source())
    link = tmp_path / "linked.yml"
    link.symlink_to(candidate)
    with pytest.raises(gate.ProfileRejected, match="noncanonical"):
        gate.read_source(Path("candidate.yml"))
    with pytest.raises(gate.ProfileRejected, match="noncanonical"):
        gate.read_source(link)
    assert gate.read_source(candidate) == source()


def test_cli_only_reports_shape_without_writes(monkeypatch, capsys, tmp_path):
    import json
    import sys

    original = source()
    candidate = gate.expected_candidate(original, "BASAL_ZERO")
    candidate_path = tmp_path / "candidate.yml"
    candidate_path.write_bytes(candidate)
    before = sorted(p.name for p in tmp_path.iterdir())
    monkeypatch.setattr(sys, "argv", [
        "r-only-shape",
        "--base-config-original", str(REFERENCE.resolve()),
        "--candidate-config", str(candidate_path.resolve()),
        "--arm", "BASAL_ZERO",
        "--plugin-sha256", gate.PLUGIN_SHA256,
        "--paper-sha256", gate.PAPER_SHA256,
        "--server-properties-sha256", gate.SERVER_PROPERTIES_SHA256,
    ])
    assert gate.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["classification"] == gate.CLASS
    assert output["physical_world_launch_authorized"] is False
    assert sorted(p.name for p in tmp_path.iterdir()) == before
