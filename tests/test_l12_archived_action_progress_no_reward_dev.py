"""L12: real saved G413 S16 endpoint progress is not external per-Action Goal."""
from __future__ import annotations

import copy
import json
import os
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from adapters.mineflayer.l11_saved_real_goal_originals_dev import PINNED
from adapters.mineflayer.l12_archived_action_progress_no_reward_dev import (
    L12ProgressRejected,
    _action_rows,
    audit_l12_real_action_goal_gate,
    main,
    require_l10_qualified_goal_training,
)


@pytest.fixture(scope="module")
def original_zip() -> Path:
    path = os.environ.get("L11_REAL_ORIGINAL_ZIP")
    if path is None:
        pytest.skip("independent original real Paper source was not provided")
    actual = Path(path)
    assert actual.is_absolute() and actual.is_file()
    return actual


def test_missing_real_source_does_not_mint_learning(capsys):
    assert main([]) == 0
    x = json.loads(capsys.readouterr().out)
    assert x["classification"] == "L12_REAL_ORIGINAL_BYTES_NOT_SUPPLIED"
    assert x["qualified_l10_training_pairs"] == 0
    assert x["new_worlds_started"] == 0


def test_original_11_action_endpoints_not_independent_goal_receipts(original_zip):
    report = audit_l12_real_action_goal_gate(original_zip)
    assert report.producer_artifact_id == 12952335343
    assert report.original_s49_action_rows == 11
    assert report.original_t2_world_ticks == 182
    assert report.action_end_inside_tolerance == 1
    assert report.action_end_outside_tolerance == 10
    assert report.endpoint_step_exceeds_action_displacement == 9
    assert len(report.post_terminal_goal_reductions_m) == 2
    assert report.post_terminal_goal_reductions_m == pytest.approx(
        (0.04980496347192731, 0.06465261996232563),
        abs=1e-10,
    )
    baseline = report.action_progress[:5]
    controlled = report.action_progress[5:]
    assert [x.ordinal for x in baseline] == [1, 2, 3, 4, 5]
    assert [x.ordinal for x in controlled] == [1, 2, 3, 4, 5, 6]
    assert all(x.world == "WORLD-G4" for x in baseline)
    assert all(x.world == "WORLD-G413" for x in controlled)
    assert len({x.session_id for x in report.action_progress}) == 2
    assert all(x.s16_executed for x in report.action_progress)
    assert all(x.observed_endpoint_goal_reduction_m > 0 for x in report.action_progress)
    assert all(x.external_action_goal_reached is None for x in report.action_progress)
    assert all(not x.per_action_goal_attested for x in report.action_progress)
    assert all(not x.causal_motor_contribution_attested for x in report.action_progress)
    assert all(not x.native_source_packet_authenticated for x in report.action_progress)
    assert baseline[-1].at_s16_inside_goal_tolerance
    assert not controlled[-1].at_s16_inside_goal_tolerance
    assert baseline[-1].after_endpoint_goal_error_m == pytest.approx(0.45259187129648093)
    assert controlled[-1].after_endpoint_goal_error_m == pytest.approx(0.5124054721976607)
    assert report.independent_per_action_goal_receipts == 0
    assert report.original_native_pre_action_world_body_receipts == 0
    assert report.independent_native_s16_jsonl_receipts == 0
    assert report.qualified_l10_training_pairs == 0
    assert not report.l10_retention_action_authorized
    assert not report.physical_learning_attested
    assert report.s10_learning_updates == report.s11_habit_grants == 0
    assert report.physical_actions_started == report.new_worlds_started == 0
    assert not report.qualification_go and not report.science_go
    assert audit_l12_real_action_goal_gate(original_zip) == report
    with pytest.raises(L12ProgressRejected, match="cannot authorize L10"):
        require_l10_qualified_goal_training(report)
    with pytest.raises(L12ProgressRejected):
        require_l10_qualified_goal_training(replace(report, qualified_l10_training_pairs=99))
    with pytest.raises(L12ProgressRejected):
        require_l10_qualified_goal_training(None)


@pytest.mark.parametrize("fault", (
    "alter_end", "alter_goal_error", "alter_motion", "negative_motion",
    "bad_initial_seq", "out_of_order", "missing_action", "unknown_s16",
    "negative_error", "nonfinite", "tampered_action_count",
))
def test_source_derived_per_action_readback_fail_closed(original_zip, fault):
    with zipfile.ZipFile(original_zip) as z:
        report = json.loads(z.read("WORLD-G413/goal_report.json"))
    damaged = copy.deepcopy(report)
    a = damaged["native_actions"][1]
    if fault == "alter_end":
        a["end_z"] += 0.12
    elif fault == "alter_goal_error":
        a["goal_error_at_S16_end_m"] += 0.12
    elif fault == "alter_motion":
        a["native_travel_z"] += 0.12
    elif fault == "negative_motion":
        a["native_displacement_m"] = -1.0
    elif fault == "bad_initial_seq":
        damaged["initial_native_xz"]["seq"] = "invalid"
    elif fault == "out_of_order":
        a["before_seq"] = damaged["native_actions"][0]["after_seq"]
    elif fault == "missing_action":
        a.pop("goal_error_at_S16_end_m")
    elif fault == "unknown_s16":
        a["s16_terminal"] = "unknown"
    elif fault == "negative_error":
        a["goal_error_at_S16_end_m"] = -1.0
    elif fault == "nonfinite":
        a["end_z"] = float("nan")
    else:
        damaged["native_actions"] = []
    with pytest.raises(L12ProgressRejected):
        _action_rows("WORLD-G413", damaged, PINNED["WORLD-G413/goal_report.json"])


@pytest.mark.parametrize("member", sorted(PINNED))
def test_real_saved_report_or_t2_original_modification_never_mints_reward(
    original_zip, tmp_path, member,
):
    altered = tmp_path / "changed-source.zip"
    with zipfile.ZipFile(original_zip) as z, zipfile.ZipFile(
        altered, "w", compression=zipfile.ZIP_DEFLATED,
    ) as out:
        for name in z.namelist():
            contents = z.read(name)
            if name == member:
                contents += b" "
            out.writestr(name, contents)
    with pytest.raises(L12ProgressRejected, match="original L11"):
        audit_l12_real_action_goal_gate(altered)


def test_real_source_absent_or_symlink_does_not_permit_learning(original_zip, tmp_path):
    with pytest.raises(L12ProgressRejected):
        audit_l12_real_action_goal_gate(tmp_path / "absent.zip")
    path = tmp_path / "symlink.zip"
    path.symlink_to(original_zip)
    with pytest.raises(L12ProgressRejected):
        audit_l12_real_action_goal_gate(path)


def test_cli_original_readback_is_repeatable_and_read_only(original_zip, capsys):
    original_data = original_zip.read_bytes()
    assert main(["--artifact-zip", str(original_zip)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["original_s49_action_rows"] == 11
    assert payload["action_end_inside_tolerance"] == 1
    assert payload["qualified_l10_training_pairs"] == 0
    assert payload["new_worlds_started"] == 0
    assert original_zip.read_bytes() == original_data
