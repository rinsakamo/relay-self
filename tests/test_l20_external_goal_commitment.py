"""L20 external Goal original prospective commitment: synthetic DEV only."""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace

import pytest

import test_l13_independent_goal_receipt as l13
import test_l16_s49_first_action_original_capture as l16
import test_l17_saved_original_goal_readback as l17
from adapters.mineflayer.l16_first_action_goal_originals import (
    inspect_l16_first_action_prefix,
)
from adapters.mineflayer.l20_external_goal_commitment_readback import (
    audit_l20_external_goal,
    main,
)
from relay_self.l20_external_goal_commitment import (
    ACTION_SCOPE,
    COMMITMENT_SCHEMA,
    SESSION_SCOPE,
    L20GoalCommitmentRejected,
    review_external_pre_world_criterion,
    review_l20_post_s49_source,
)


def original(plan):
    doc = {
        "schema": COMMITMENT_SCHEMA,
        "criterion_id": "external-criterion-001",
        "external_goal_owner_ref": "paper-reviewer-A",
        "experiment_ref": "l20-experiment-001",
        "session_scope": SESSION_SCOPE,
        "action_scope": ACTION_SCOPE,
        "target_x": plan.target_x,
        "target_z": plan.target_z,
        "tolerance_m": plan.tolerance_m,
        "stable_probe_delta_max_m": plan.stable_probe_delta_max_m,
        "independent_goal_observed": False,
        "authorizes_learning": False,
    }
    return l13.raw(doc)


def src():
    args = l16.fixture()
    raw = original(args["plan"])
    admitted_sha = hashlib.sha256(raw).hexdigest()
    return args, raw, admitted_sha


def test_no_world_future_session_criterion_can_be_preregistered_without_fake_s49_ids():
    args, raw, sha = src()
    pre = review_external_pre_world_criterion(
        original=raw, admitted_sha256=sha, operator_plan=args["plan"],
    )
    assert pre.original_sha256 == sha
    assert pre.matched_operator_plan
    assert pre.criterion_id == "external-criterion-001"
    assert not pre.authenticated_external_owner
    assert not pre.externally_attested_before_world
    assert not pre.independent_goal_observed
    assert not pre.learning_authority
    # The exact future Action/source is only known after S49 runs.
    window = inspect_l16_first_action_prefix(**args)
    bound = review_l20_post_s49_source(
        preflight=pre, window=window, operator_plan=args["plan"],
    )
    assert bound.first_action_id == args["action_id"]
    assert bound.session_id == args["session_id"]
    assert bound.source_goal_diagnostic == "REACHED"
    assert bound.criterion_sha256 == sha
    assert bound.received_original_sha256 == window.received_sha256
    assert not bound.external_owner_authenticated
    assert not bound.pre_world_time_independently_attested
    assert not bound.independent_goal_result_original_present
    assert not bound.no_intervention_physical_proven
    assert bound.qualified_real_l10_pairs == bound.s10_updates == 0


@pytest.mark.parametrize("fault", [
    "sha", "sha_upper", "missing", "goal_status", "session_id", "action_id",
    "owner_missing", "owner_invalid", "target", "tolerance", "stability",
    "future_scope", "other_action_scope", "learning_true", "goal_observed",
    "nan", "duplicate", "noncanonical", "multiline", "oversized",
    "blank", "raw_not_bytes",
])
def test_wrong_preworld_scope_is_rejected_without_reward(fault):
    args, raw, sha = src()
    plan = args["plan"]
    if fault in ("sha", "sha_upper"):
        sha = "f"*64 if fault == "sha" else sha.upper()
    elif fault == "multiline":
        raw += raw
        sha = hashlib.sha256(raw).hexdigest()
    elif fault == "oversized":
        raw += b" " * 4096
        sha = hashlib.sha256(raw).hexdigest()
    elif fault == "blank":
        raw = b""
        sha = hashlib.sha256(raw).hexdigest()
    elif fault == "raw_not_bytes":
        raw = raw.decode("utf-8")
    elif fault == "noncanonical":
        raw = (json.dumps(json.loads(raw), indent=2) + "\n").encode()
        sha = hashlib.sha256(raw).hexdigest()
    elif fault == "duplicate":
        raw = raw.replace(
            b'"target_x":', b'"target_x":123,"target_x":',
        )
        sha = hashlib.sha256(raw).hexdigest()
    else:
        doc = json.loads(raw)
        if fault == "missing":
            del doc["criterion_id"]
        elif fault == "goal_status":
            doc["goal_status"] = "REACHED"
        elif fault == "session_id":
            doc["session_id"] = args["session_id"]
        elif fault == "action_id":
            doc["action_id"] = args["action_id"]
        elif fault == "owner_missing":
            del doc["external_goal_owner_ref"]
        elif fault == "owner_invalid":
            doc["external_goal_owner_ref"] = " "
        elif fault == "target":
            doc["target_z"] += 1
        elif fault == "tolerance":
            doc["tolerance_m"] += 1
        elif fault == "stability":
            doc["stable_probe_delta_max_m"] = 0.01
        elif fault == "future_scope":
            doc["session_scope"] = "CURRENT_SESSION"
        elif fault == "other_action_scope":
            doc["action_scope"] = "ANY_ACTION"
        elif fault == "learning_true":
            doc["authorizes_learning"] = True
        elif fault == "goal_observed":
            doc["independent_goal_observed"] = True
        elif fault == "nan":
            doc["target_x"] = float("nan")
        raw = l13.raw(doc)
        sha = hashlib.sha256(raw).hexdigest()
    with pytest.raises((ValueError, TypeError)):
        review_external_pre_world_criterion(
            original=raw, admitted_sha256=sha, operator_plan=plan,
        )


@pytest.mark.parametrize("fault", [
    "source_replayed", "plan_modified", "false_authenticated",
    "false_time_attested", "false_goal_observed", "false_learning",
    "wrong_s7_plan_sha", "false_goal_authority", "false_qualified_pairs",
])
def test_postworld_source_binding_cannot_upgrade_owner_or_learning(fault):
    args, raw, sha = src()
    pre = review_external_pre_world_criterion(
        original=raw, admitted_sha256=sha, operator_plan=args["plan"],
    )
    win = inspect_l16_first_action_prefix(**args)
    plan = args["plan"]
    if fault == "source_replayed":
        win = replace(win, complete_single_action_captured_prefix=False)
    elif fault == "plan_modified":
        plan = replace(plan, target_z=plan.target_z + 0.5)
    elif fault == "false_authenticated":
        pre = replace(pre, authenticated_external_owner=True)
    elif fault == "false_time_attested":
        pre = replace(pre, externally_attested_before_world=True)
    elif fault == "false_goal_observed":
        pre = replace(pre, independent_goal_observed=True)
    elif fault == "false_learning":
        pre = replace(pre, learning_authority=True)
    elif fault == "wrong_s7_plan_sha":
        win = replace(win, plan_sha256="0"*64)
    elif fault == "false_goal_authority":
        win = replace(win, independent_external_goal_authenticated=True)
    elif fault == "false_qualified_pairs":
        win = replace(win, qualified_real_l10_pairs=1)
    with pytest.raises(L20GoalCommitmentRejected):
        review_l20_post_s49_source(
            preflight=pre, window=win, operator_plan=plan,
        )


def test_pre_and_postworld_cli_read_separate_external_file_without_writes(tmp_path, capsys):
    root, report, args = l17.saved_fixture(tmp_path)
    raw = original(args["plan"])
    sha = hashlib.sha256(raw).hexdigest()
    ext = tmp_path / "external-physical-reviewer.jsonl"
    ext.write_bytes(raw)
    before = {p: p.read_bytes() for p in [ext, report, *root.iterdir()]}
    argv = [
        "--external-criterion-original", str(ext),
        "--admitted-sha256", sha,
        "--target-x", str(args["plan"].target_x),
        "--target-z", str(args["plan"].target_z),
    ]
    assert main(argv) == 0
    pre = json.loads(capsys.readouterr().out)
    assert pre["mode"] == "PREWORLD_SOURCE_ONLY_NO_TIMESTAMP_AUTHENTICATION"
    assert pre["preflight"]["original_sha256"] == sha
    assert not pre["pre_world_time_independently_attested"]
    assert main([*argv, "--root", str(root), "--s49-report", str(report)]) == 0
    post = json.loads(capsys.readouterr().out)
    assert post["binding"]["first_action_id"] == args["action_id"]
    assert post["binding"]["source_goal_diagnostic"] == "REACHED"
    assert post["binding"]["criterion_sha256"] == sha
    assert post["qualified_real_l10_pairs"] == 0
    assert not post["external_goal_owner_authenticated"]
    assert not post["independent_goal_result_original_present"]
    assert before == {p: p.read_bytes() for p in before}


@pytest.mark.parametrize("fault", [
    "tamper_external", "tamper_s7", "tamper_plan", "wrong_target",
    "external_symlink", "external_inside_capture", "missing_report",
    "wrong_session", "root_symlink",
])
def test_postworld_wrong_source_external_file_and_retroactive_goal_are_rejected(
    tmp_path, fault,
):
    root, report, args = l17.saved_fixture(tmp_path)
    ext = tmp_path / "reviewer.jsonl"
    raw = original(args["plan"])
    ext.write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    plan = args["plan"]
    if fault == "tamper_external":
        ext.write_bytes(ext.read_bytes().replace(b"paper-reviewer-A", b"paper-reviewer-B"))
    elif fault == "tamper_s7":
        path = root / "native_bridge_received_original.jsonl"
        path.write_bytes(path.read_bytes() + b'{"fake":true}\n')
    elif fault == "tamper_plan":
        path = root / "l16_pre_world_goal_plan.json"
        path.write_bytes(path.read_bytes().replace(b'"target_x":', b'"target_x":1,'))
    elif fault == "wrong_target":
        plan = replace(plan, target_x=plan.target_x + 1)
    elif fault == "external_symlink":
        link = tmp_path / "symlink.jsonl"
        link.symlink_to(ext)
        ext = link
    elif fault == "external_inside_capture":
        ext = root / "external.jsonl"
        ext.write_bytes(raw)
    elif fault == "missing_report":
        report.unlink()
    elif fault == "wrong_session":
        doc = json.loads(report.read_bytes())
        doc["session_id"] = "another-session"
        report.write_bytes(l13.raw(doc))
    elif fault == "root_symlink":
        link = tmp_path / "capture-symlink"
        link.symlink_to(root, target_is_directory=True)
        root = link
    with pytest.raises((ValueError, OSError, KeyError, TypeError)):
        audit_l20_external_goal(
            external_path=ext, admitted_sha256=sha,
            operator_plan=plan, root=root, report_path=report,
        )


def test_cli_malformed_goal_is_no_go_not_false_label(tmp_path, capsys):
    plan = l16.fixture()["plan"]
    ext = tmp_path / "invalid.jsonl"
    ext.write_bytes(original(plan).replace(b'"authorizes_learning":false', b'"authorizes_learning":true'))
    sha = hashlib.sha256(ext.read_bytes()).hexdigest()
    rc = main([
        "--external-criterion-original", str(ext),
        "--admitted-sha256", sha,
        "--target-x", str(plan.target_x),
        "--target-z", str(plan.target_z),
    ])
    assert rc == 2
    assert "L20 rejected:" in capsys.readouterr().err


@pytest.mark.parametrize("fault", [
    "wrong_sha", "wrong_goal", "file_missing", "symlinked", "not_external",
    "missing_l20_pair", "missing_l16_pair",
])
def test_s49_explicit_l20_gate_refuses_before_java_and_action(
    tmp_path, monkeypatch, fault,
):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    _args, raw, sha = src()
    plan = _args["plan"]
    ext = tmp_path / "reviewer-owned.jsonl"
    ext.write_bytes(raw)
    capture_root = tmp_path / "l16-capture"
    capture_root.mkdir()
    report = tmp_path / "s49-report.json"
    log = tmp_path / "server.log"
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)

    def no_java(*_args, **_kwargs):
        pytest.fail("invalid external Goal source must reject BEFORE Java")

    monkeypatch.setattr(s49, "_fetch_official_server", no_java)
    criterion_file = ext
    criterion_sha = sha
    goal = plan
    capture = capture_root
    if fault == "wrong_sha":
        criterion_sha = "f" * 64
    elif fault == "wrong_goal":
        goal = replace(plan, target_z=plan.target_z + 0.2)
    elif fault == "file_missing":
        criterion_file = tmp_path / "nonexistent.jsonl"
    elif fault == "symlinked":
        link = tmp_path / "reviewer-symlink.jsonl"
        link.symlink_to(ext)
        criterion_file = link
    elif fault == "not_external":
        criterion_file = capture_root / "copied-reviewer.jsonl"
        criterion_file.write_bytes(raw)
    elif fault == "missing_l20_pair":
        criterion_sha = None
    elif fault == "missing_l16_pair":
        capture = None

    rc = asyncio.run(s49.qualify(
        report, log, l16_capture_root=capture, l16_goal_plan=goal,
        l20_external_goal_original=criterion_file,
        l20_admitted_sha256=criterion_sha,
    ))
    assert rc == 2
    assert json.loads(report.read_bytes())["status"] == "BLOCKED"
    # The not_external fault intentionally seeds one foreign file inside the
    # capture root. S49 itself must never write a Goal plan or S7 source.
    assert not (capture_root / "l16_pre_world_goal_plan.json").exists()
    assert not (capture_root / "native_bridge_received_original.jsonl").exists()
    assert not (capture_root / "native_bridge_sent_original.jsonl").exists()
    assert not log.exists()


def test_s49_matching_external_goal_preflight_happens_before_world(
    tmp_path, monkeypatch,
):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    args, raw, sha = src()
    ext = tmp_path / "separate-reviewer.jsonl"
    ext.write_bytes(raw)
    capture_root = tmp_path / "new-l16-root"
    capture_root.mkdir()
    report_path = tmp_path / "report.json"
    calls = []

    def stop_before_java(*_args, **_kwargs):
        calls.append("before-java")
        raise s49.S31ABlocked("test deliberately stops before physical World")

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(s49, "_fetch_official_server", stop_before_java)
    rc = asyncio.run(s49.qualify(
        report_path, tmp_path / "server.log",
        l16_capture_root=capture_root, l16_goal_plan=args["plan"],
        l20_external_goal_original=ext, l20_admitted_sha256=sha,
    ))
    assert rc == 2 and calls == ["before-java"]
    report = json.loads(report_path.read_bytes())
    pre = report["l20_external_goal_preflight"]
    assert report["l20_external_goal_preflight_status"] == (
        "SOURCE_MATCH_BEFORE_WORLD_UNQUALIFIED"
    )
    assert pre["original_sha256"] == sha
    assert pre["matched_operator_plan"]
    assert not pre["authenticated_external_owner"]
    assert not pre["externally_attested_before_world"]
    assert not pre["learning_authority"]
    assert report["status"] == "BLOCKED"
    assert report["l16_capture"]["status"] == "INCOMPLETE_NO_GOAL_LABEL"
    assert (capture_root / "l16_pre_world_goal_plan.json").read_bytes() == (
        args["plan"].original_bytes()
    )
    assert ext.read_bytes() == raw
