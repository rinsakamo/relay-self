"""R-only prospective 4-arm native-source joint readback with negative controls."""
import hashlib
from pathlib import Path

import pytest

from experiments.standard_env import m02_v7_remaining_profile_preflight as profile
from experiments.standard_env import m02_v7_remaining_source_review as r
from test_rsee_s50_tick_chord_original_audit import MARKER, specimen as movement_source
from test_rsee_v7_m02_direct_basal_readback import specimen as basal_source

BASE_FILE = (
    Path(__file__).parent / "fixtures" / "rsee_m02_v7_tick_base_qualified_config.yml"
)
ARMS = ("SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO")


def raw_original(arm):
    return movement_source(rate=0.01 * profile.UNQUALIFIED_ARMS[arm][1]) + (
        basal_source(arm)
    )


def run_arm(arm, *, original=None, candidate=None, marker=MARKER, sha=None,
            plugin_sha=profile.PLUGIN_SHA256):
    base = BASE_FILE.read_bytes()
    source = raw_original(arm) if original is None else original
    expected = profile.expected_candidate(base, arm) if candidate is None else candidate
    return r.review_source(
        base, expected, source, arm=arm, action_marker=marker,
        expected_paper_sha256=hashlib.sha256(source).hexdigest() if sha is None else sha,
        plugin_sha256=plugin_sha,
        paper_binary_sha256=profile.PAPER_SHA256,
        server_properties_sha256=profile.SERVER_PROPERTIES_SHA256,
    )


@pytest.mark.parametrize("arm", ARMS)
def test_each_arm_joint_real_world_format_sources_are_review_only(arm):
    out = run_arm(arm)
    basal, walk = profile.UNQUALIFIED_ARMS[arm]
    assert out["classification"] == r.CLASS
    assert out["arm"] == arm
    assert out["source_player_basal_write_rows"] == 200
    assert out["source_native_tick_chord_rows"] == 13
    assert out["observed_tick_chord_lower_bound_blocks"] == pytest.approx(0.75)
    assert out["source_basal_requested_first200"] == pytest.approx(basal * 0.2)
    assert out["observed_walk_native_setter_input"] == pytest.approx(walk * 0.0075)
    assert out["expected_walk_setter_input_per_chord_block"] == walk * .01
    assert out["event_double_billed"] is False
    assert out["bounded_quiet_window"] is True
    assert out["zero_rate_legitimate_if_observed_distance_positive"] == (walk == 0)
    for key in (
        "producer_authenticated_by_this_review",
        "paper_world_tick_shared_action_bracket_attested",
        "native_terminal_action_or_eat_attested",
        "native_pid_or_port_stop_attested",
        "continuous_subtick_path_attested",
        "net_native_hunger_debit_attested",
        "fresh_qualification_grant_issued",
        "physical_world_launch_authorized",
        "candidate_arm_engineering_qualified",
        "other_arms_engineering_qualified",
        "science_go",
        "production_go",
    ):
        assert out[key] is False, key
    assert out["v7_science_trials_credited"] == 0


def test_sham_config_is_identical_but_source_is_not_qualification():
    raw = BASE_FILE.read_bytes()
    assert profile.expected_candidate(raw, "SHAM_ON") == raw
    out = run_arm("SHAM_ON")
    assert not out["candidate_arm_engineering_qualified"]
    assert not out["native_pid_or_port_stop_attested"]


@pytest.mark.parametrize("arm,other", [
    ("SHAM_ON", "BASAL_ZERO"),
    ("BASAL_ZERO", "SHAM_ON"),
    ("WALK_ZERO", "BOTH_ZERO"),
    ("BOTH_ZERO", "WALK_ZERO"),
])
def test_other_arm_source_cannot_replace_registered_physiology(arm, other):
    with pytest.raises((r.SourceRejected, ValueError)):
        run_arm(arm, original=raw_original(other))


@pytest.mark.parametrize("arm", ARMS)
def test_wrong_arm_config_cannot_relabel_real_source(arm):
    other = "BOTH_ZERO" if arm != "BOTH_ZERO" else "BASAL_ZERO"
    wrong = profile.expected_candidate(BASE_FILE.read_bytes(), other)
    with pytest.raises(profile.ProfileRejected):
        run_arm(arm, candidate=wrong)


def test_native_tick_writer_and_basal_each_independently_required():
    good = raw_original("BASAL_ZERO")
    with pytest.raises(ValueError):
        run_arm("BASAL_ZERO", original=basal_source("BASAL_ZERO"))
    with pytest.raises(ValueError):
        run_arm("BASAL_ZERO", original=movement_source(rate=.01))
    with pytest.raises(ValueError):
        run_arm("BASAL_ZERO", original=good.replace(
            b"M02_DEV_BASAL_WRITE id=33", b"M02_DEV_BASAL_WRITE id=32"))
    with pytest.raises(ValueError):
        run_arm("BASAL_ZERO", original=good.replace(
            b"S50_DEV_TICK_MOTION id=2", b"S50_DEV_TICK_MOTION id=1"))


def test_foreign_marker_hash_and_binary_rejected():
    with pytest.raises(r.SourceRejected, match="SHA256 comparator"):
        run_arm("BOTH_ZERO", sha="0" * 64)
    with pytest.raises(r.SourceRejected, match="marker"):
        run_arm("BOTH_ZERO", marker="INVALID MARKER")
    with pytest.raises(profile.ProfileRejected, match="unregistered"):
        run_arm("BOTH_ZERO", plugin_sha="0" * 64)


@pytest.mark.parametrize("arm", ("WALK_ZERO", "BOTH_ZERO"))
def test_zero_cost_cannot_be_replaced_with_an_unreported_positive_debit(arm):
    paper = raw_original(arm)
    assert b"billed=0.0" in paper
    with pytest.raises(ValueError):
        run_arm(arm, original=paper.replace(b"billed=0.0", b"billed=0.003", 1))


def test_original_files_and_cli_do_not_mutate_evidence(tmp_path, monkeypatch, capsys):
    import json
    import sys

    arm = "SHAM_ON"
    candidate = tmp_path / "SHAM_ON.yml"
    candidate.write_bytes(profile.expected_candidate(BASE_FILE.read_bytes(), arm))
    paper = tmp_path / "paper_server.log"
    source = raw_original(arm)
    paper.write_bytes(source)
    recorded = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in tmp_path.iterdir()}
    args = [
        "--base-config-original", str(BASE_FILE.resolve()),
        "--candidate-config", str(candidate),
        "--paper-original", str(paper),
        "--paper-original-sha256", hashlib.sha256(source).hexdigest(),
        "--arm", arm, "--action-marker", MARKER,
        "--plugin-sha256", profile.PLUGIN_SHA256,
        "--paper-binary-sha256", profile.PAPER_SHA256,
        "--server-properties-sha256", profile.SERVER_PROPERTIES_SHA256,
    ]
    monkeypatch.setattr(sys, "argv", ["r-joint-sources", *args])
    assert r.main() == 0
    assert json.loads(capsys.readouterr().out)["classification"] == r.CLASS
    assert recorded == {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in tmp_path.iterdir()
    }
    (tmp_path / "alias.log").symlink_to(paper)
    with pytest.raises(r.SourceRejected, match="aliased"):
        r.review_paths(
            BASE_FILE.resolve(), candidate, tmp_path / "alias.log",
            arm=arm, action_marker=MARKER,
            expected_paper_sha256=hashlib.sha256(source).hexdigest(),
            plugin_sha256=profile.PLUGIN_SHA256,
            paper_binary_sha256=profile.PAPER_SHA256,
            server_properties_sha256=profile.SERVER_PROPERTIES_SHA256,
        )
