"""Q1b hostile pre-S2 historical WAL tests using synthetic bytes, NOT World."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from experiments.q_lane_coupled_custody_dev import (
    QCoupledCustodyHold,
    verify_coupled_s1_s2_custody,
)
from experiments.q_lane_s1_boundary_audit_dev import (
    QS1BoundaryHold,
    verify_s1_s2_anchor,
)

HEAD = "1" * 40
WORLD = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
OWNER = "owner-original-A"
SELF = "A"
SESSION = "native-A-epoch-4"


def _bytes(row: object) -> bytes:
    return (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _setup(tmp_path: Path) -> tuple[Path, bytes, dict, dict]:
    root = tmp_path / "original"
    root.mkdir(parents=True)
    s1 = {
        "action_id": "action-s1", "intent_id": "intent-s1",
        "skill_execution_id": "skill-s1",
        "status": "NATIVE_PLACE_MOVE_SETTLED",
    }
    s2 = {
        "action_id": "action-s2", "intent_id": "intent-s2",
        "skill_execution_id": "skill-s2", "session_id": SESSION,
        "status": "NATIVE_PLACE_MOVE_NO_PROGRESS",
    }
    before = {"schema": 2, "self_id": SELF, "actions": [s1]}
    after = {"schema": 2, "self_id": SELF, "actions": [copy.deepcopy(s1), s2]}
    (root / "s1-wal.json").write_bytes(_bytes(before))
    (root / "s2-wal.json").write_bytes(_bytes(after))
    (root / "s1-checkpoint.json").write_bytes(_bytes({
        "generation": 4, "actor": SELF, "owner": OWNER,
    }))
    anchor = {
        "schema": 1, "phase": "S1_TERMINAL_PRE_S2",
        "head": HEAD, "world_uuid": WORLD,
        "owner_id": OWNER, "self_id": SELF,
        "native_session_id": SESSION, "checkpoint_generation": 4,
        "s1_intent_id": "intent-s1", "s1_skill_execution_id": "skill-s1",
        "s1_action_id": "action-s1", "s1_status": "NATIVE_PLACE_MOVE_SETTLED",
        "s1_wal_sha256": _sha((root / "s1-wal.json").read_bytes()),
        "s1_checkpoint_sha256": _sha((root / "s1-checkpoint.json").read_bytes()),
        "s1_action_count": 1,
    }
    raw_anchor = _bytes(anchor)
    args = {
        "expected_pre_s2_anchor_sha256": _sha(raw_anchor),
        "s1_wal_path": "s1-wal.json", "s1_checkpoint_path": "s1-checkpoint.json",
        "s2_wal_path": "s2-wal.json", "expected_s2_action_id": "action-s2",
        "expected_head": HEAD, "expected_world_uuid": WORLD,
        "expected_owner_id": OWNER, "expected_self_id": SELF,
        "expected_native_session_id": SESSION, "expected_checkpoint_generation": 4,
    }
    return root, raw_anchor, anchor, args


def _verify(root: Path, anchor: bytes, args: dict):
    return verify_s1_s2_anchor(root, anchor_bytes=anchor, **args)


def test_q1b_synthetic_preanchor_and_wal_continuity_read_only(tmp_path):
    root, anchor, _row, args = _setup(tmp_path)
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.iterdir()}
    verdict = _verify(root, anchor, args)
    assert verdict["classification"] == "Q1B_PINNED_S1_S2_WAL_PREFIX_CPU_OFFLINE_DEV"
    assert verdict["s1_action_count"] == 1
    assert verdict["s2_total_action_count"] == 2
    assert verdict["s2_terminal_status_label"] == "NATIVE_PLACE_MOVE_NO_PROGRESS"
    assert verdict["s2_native_session_claim"] == SESSION
    assert verdict["one_s2_action_appended"] is True
    assert verdict["s2_outcome_original_native_paper_attested"] is False
    assert verdict["s2_skill_success_attested"] is False
    assert verdict["trusted_external_anchor_origin_verified"] is False
    assert verdict["pre_s2_temporal_order_verified"] is False
    assert verdict["original_stage28_checkpoint_restored"] is False
    assert verdict["original_owner_semantics_verified"] is False
    assert verdict["real_world_attested"] is False and verdict["qual_go"] is False
    assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                      for p in root.iterdir()}


@pytest.mark.parametrize(("field", "replacement"), [
    ("expected_head", "2" * 40),
    ("expected_world_uuid", "different-world"),
    ("expected_owner_id", "different-owner"),
    ("expected_self_id", "B"),
    ("expected_native_session_id", "stale-native-session"),
    ("expected_checkpoint_generation", 5),
    ("expected_pre_s2_anchor_sha256", "0" * 64),
])
def test_q1b_rejects_scope_and_externally_pinned_digest_changes(
    tmp_path, field, replacement,
):
    root, anchor, _row, args = _setup(tmp_path)
    args[field] = replacement
    with pytest.raises(QS1BoundaryHold):
        _verify(root, anchor, args)


@pytest.mark.parametrize(("field", "replacement"), [
    ("head", "2" * 40), ("owner_id", "foreign-owner"),
    ("native_session_id", "old-session"),
    ("s1_status", "PREPARED_UNRESOLVED"),
    ("s1_action_count", 2),
    ("phase", "S1_TERMINAL_AFTER_S2"),
    ("s1_action_id", "stale-action"),
])
def test_q1b_rejects_rehashed_manifest_claims_without_external_preanchor(
    tmp_path, field, replacement,
):
    root, anchor, row, args = _setup(tmp_path)
    row[field] = replacement
    forged = _bytes(row)
    # Recompute the attacker's local manifest SHA. The independent pin
    # remains the ORIGINAL digest, so this does not establish origin.
    assert _sha(forged) != args["expected_pre_s2_anchor_sha256"]
    with pytest.raises(QS1BoundaryHold, match="external digest"):
        _verify(root, forged, args)


@pytest.mark.parametrize(("file", "replace", "with_text"), [
    ("s1-wal.json", b"action-s1", b"action-SWAPPED"),
    ("s1-wal.json", b"NATIVE_PLACE_MOVE_SETTLED", b"PREPARED_UNRESOLVED"),
    ("s1-checkpoint.json", b'"generation":4', b'"generation":5'),
    ("s1-checkpoint.json", b"owner-original-A", b"owner-SWAPPED"),
])
def test_q1b_s1_raw_bytes_cannot_be_modified_and_rehashed_locally(
    tmp_path, file, replace, with_text,
):
    root, anchor, row, args = _setup(tmp_path)
    path = root / file
    old = path.read_bytes()
    new = old.replace(replace, with_text)
    assert new != old
    path.write_bytes(new)
    # Recomputing the local manifest SHA cannot update trusted earlier pin.
    row["s1_wal_sha256" if file == "s1-wal.json" else "s1_checkpoint_sha256"] = (
        _sha(new)
    )
    with pytest.raises(QS1BoundaryHold):
        _verify(root, _bytes(row), args)


@pytest.mark.parametrize(("change", "expected"), [
    ("s1-action-id", "Historical S1 WAL row"),
    ("s1-action-status", "Historical S1 WAL row"),
    ("s1-intent", "Historical S1 WAL row"),
    ("reordered", "Historical S1 WAL row"),
    ("duplicate-id", "Duplicate/replayed"),
    ("no-s2", "exactly one new S2 Action"),
    ("prepared-s2", "Unresolved PREPARED"),
    ("foreign-self", "schema or Self mismatch"),
    ("wrong-s2-id", "S2 new Action"),
    ("nonterminal-s2", "no qualified terminal status"),
    ("foreign-s2-session", "native session differs"),
    ("missing-s2-session", "Native session missing"),
    ("missing-s2-status", "no qualified terminal status"),
    ("nonblank-s2-skill", "Intent/Skill/Native session missing"),
    ("extra-s2-row", "exactly one new S2 Action"),
])
def test_q1b_rejects_s2_history_replay_or_reinterpretation(
    tmp_path, change, expected,
):
    root, anchor, _row, args = _setup(tmp_path)
    path = root / "s2-wal.json"
    body = json.loads(path.read_bytes())
    old = body["actions"][0]
    next_row = body["actions"][1]
    if change == "s1-action-id":
        old["action_id"] = "changed-then-rehashed"
    elif change == "s1-action-status":
        old["status"] = "NATIVE_MOVE_SETTLED"
    elif change == "s1-intent":
        old["intent_id"] = "foreign-intent"
    elif change == "reordered":
        body["actions"].reverse()
    elif change == "duplicate-id":
        next_row["action_id"] = old["action_id"]
    elif change == "no-s2":
        body["actions"].pop()
    elif change == "prepared-s2":
        next_row["status"] = "PREPARED_UNRESOLVED"
    elif change == "foreign-self":
        body["self_id"] = "B"
    elif change == "wrong-s2-id":
        args["expected_s2_action_id"] = "stale-action"
    elif change == "nonterminal-s2":
        next_row["status"] = "PREPARED_BUT_NO_OUTCOME"
    elif change == "foreign-s2-session":
        next_row["session_id"] = "foreign-session"
    elif change == "missing-s2-session":
        del next_row["session_id"]
    elif change == "missing-s2-status":
        del next_row["status"]
    elif change == "nonblank-s2-skill":
        next_row["skill_execution_id"] = None
    elif change == "extra-s2-row":
        body["actions"].append({
            "action_id": "action-s3", "status": "NATIVE_PLACE_MOVE_SETTLED",
        })
    path.write_bytes(_bytes(body))
    with pytest.raises(QS1BoundaryHold, match=expected):
        _verify(root, anchor, args)


def test_q1b_rejects_missing_symlinked_or_incomplete_evidence(tmp_path):
    root, anchor, row, args = _setup(tmp_path)
    (root / "s1-checkpoint.json").unlink()
    with pytest.raises(QS1BoundaryHold):
        _verify(root, anchor, args)
    root, anchor, row, args = _setup(tmp_path / "second")
    checkpoint = root / "s1-checkpoint.json"
    checkpoint.unlink()
    checkpoint.symlink_to(root / "s1-wal.json")
    with pytest.raises(QS1BoundaryHold):
        _verify(root, anchor, args)


def test_q1b_both_modified_pin_and_wal_can_pass_but_is_not_authenticated(tmp_path):
    """Demonstrates why Q refuses to claim independent source authentication."""
    root, _old_anchor, row, args = _setup(tmp_path)
    original = json.loads((root / "s1-wal.json").read_bytes())
    original["actions"][0]["action_id"] = "attacker-s1"
    new = json.loads((root / "s2-wal.json").read_bytes())
    new["actions"][0]["action_id"] = "attacker-s1"
    (root / "s1-wal.json").write_bytes(_bytes(original))
    (root / "s2-wal.json").write_bytes(_bytes(new))
    row["s1_wal_sha256"] = _sha((root / "s1-wal.json").read_bytes())
    row["s1_action_id"] = "attacker-s1"
    forged_anchor = _bytes(row)
    # If the presumed out-of-band anchor digest is also writable by the
    # attacker, all hashes can agree. This is exactly why result says NOT
    # authenticated, even when this limited consistency check passes.
    args["expected_pre_s2_anchor_sha256"] = _sha(forged_anchor)
    receipt = _verify(root, forged_anchor, args)
    assert receipt["trusted_external_anchor_origin_verified"] is False
    assert receipt["pre_s2_temporal_order_verified"] is False


def _coupled_git_fixture(tmp_path: Path, *, anchor_bytes: bytes, s2_wal: bytes):
    """Disposable Git evidence repo: separate from original read-only source."""
    git_repo = tmp_path / "evidence-git"
    git_repo.mkdir(parents=True)
    subprocess.run(["git", "-C", str(git_repo), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(git_repo), "config", "user.name", "Q Synthetic"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(git_repo), "config", "user.email", "q@example.invalid"],
        check=True,
    )

    def _commit(message: str) -> str:
        subprocess.run(["git", "-C", str(git_repo), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(git_repo), "commit", "-qm", message], check=True,
        )
        return subprocess.check_output(
            ["git", "-C", str(git_repo), "rev-parse", "HEAD"], text=True,
        ).strip()

    (git_repo / "README.txt").write_text("untrusted fixture, not real source\n")
    root_commit = _commit("fixture root")
    proof = git_repo / "proof"
    proof.mkdir()
    (proof / "s1-anchor.json").write_bytes(anchor_bytes)
    before_commit = _commit("pre S2 committed anchor")
    (proof / "s2-wal.json").write_bytes(s2_wal)
    after_commit = _commit("post S2 committed WAL")
    git_claims = {
        "trusted_root_sha": root_commit,
        "pre_s2_anchor_commit": before_commit,
        "post_s2_evidence_commit": after_commit,
        "anchor_path": "proof/s1-anchor.json",
        "s2_path": "proof/s2-wal.json",
    }
    return git_repo, git_claims


def _run_coupled(root, repo, anchor, source, git):
    return verify_coupled_s1_s2_custody(
        evidence_dir=root, git_repo_root=repo, anchor_bytes=anchor,
        source_claims=source, git_claims=git,
    )


def test_q1e_matches_actual_s1_anchor_and_s2_wal_in_both_readers(tmp_path):
    original, anchor, _row, claims = _setup(tmp_path)
    repo, git = _coupled_git_fixture(
        tmp_path, anchor_bytes=anchor,
        s2_wal=(original / "s2-wal.json").read_bytes(),
    )
    before = {x.name: (x.read_bytes(), x.stat().st_mtime_ns)
              for x in original.iterdir()}
    git_head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True,
    ).strip()
    receipt = _run_coupled(original, repo, anchor, claims, git)
    assert receipt["classification"] == (
        "Q1E_GIT_S1_ANCHOR_S2_WAL_COUPLED_CPU_OFFLINE_DEV"
    )
    assert receipt["source_bytes_coupled_at_readback"] is True
    assert receipt["history_first_appearance_consistent"] is True
    assert receipt["execution_code_head"] == HEAD
    assert receipt["evidence_git_s1_commit"] == git["pre_s2_anchor_commit"]
    assert receipt["evidence_git_s2_commit"] == git["post_s2_evidence_commit"]
    assert receipt["s2_wal_sha256"] == _sha((original / "s2-wal.json").read_bytes())
    assert receipt["external_git_root_origin_authenticated"] is False
    assert receipt["external_anchor_producer_authenticated"] is False
    assert receipt["actual_pre_s2_runtime_capture_verified"] is False
    assert receipt["real_world_attested"] is False
    assert receipt["qual_go"] is False and receipt["science_run"] is False
    assert before == {x.name: (x.read_bytes(), x.stat().st_mtime_ns)
                      for x in original.iterdir()}
    assert subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True,
    ).strip() == git_head


def test_q1e_two_separately_valid_sources_with_wrong_s2_bytes_are_rejected(tmp_path):
    original, anchor, _row, claims = _setup(tmp_path)
    bad_wal = (original / "s2-wal.json").read_bytes().replace(
        b"NATIVE_PLACE_MOVE_NO_PROGRESS", b"NATIVE_MOVE_SETTLED",
    )
    assert bad_wal != (original / "s2-wal.json").read_bytes()
    repo, git = _coupled_git_fixture(tmp_path, anchor_bytes=anchor, s2_wal=bad_wal)
    # Q1b verifies original local S2; Git may verify the unrelated later
    # WAL against its own independently supplied digest. The composite
    # MUST reject the incompatible two-source evidence splice.
    assert _verify(original, anchor, claims)["s2_wal_sha256"] != _sha(bad_wal)
    with pytest.raises(QCoupledCustodyHold):
        _run_coupled(original, repo, anchor, claims, git)


def test_q1e_rejects_git_committed_foreign_anchor(tmp_path):
    original, anchor, _row, claims = _setup(tmp_path)
    repo, git = _coupled_git_fixture(
        tmp_path, anchor_bytes=anchor.replace(b"intent-s1", b"foreign-s1"),
        s2_wal=(original / "s2-wal.json").read_bytes(),
    )
    with pytest.raises(QCoupledCustodyHold):
        _run_coupled(original, repo, anchor, claims, git)


@pytest.mark.parametrize(("key", "new"), [
    ("expected_owner_id", "wrong-owner"),
    ("expected_self_id", "B"),
    ("expected_native_session_id", "old-session"),
    ("expected_checkpoint_generation", 12),
    ("expected_pre_s2_anchor_sha256", "0" * 64),
])
def test_q1e_rejects_scope_and_preanchor_pin_changes(tmp_path, key, new):
    original, anchor, _row, claims = _setup(tmp_path)
    repo, git = _coupled_git_fixture(
        tmp_path, anchor_bytes=anchor,
        s2_wal=(original / "s2-wal.json").read_bytes(),
    )
    claims[key] = new
    with pytest.raises(QCoupledCustodyHold):
        _run_coupled(original, repo, anchor, claims, git)


def test_q1e_original_s2_wal_changed_after_git_commit_fails(tmp_path):
    original, anchor, _row, claims = _setup(tmp_path)
    repo, git = _coupled_git_fixture(
        tmp_path, anchor_bytes=anchor,
        s2_wal=(original / "s2-wal.json").read_bytes(),
    )
    s2 = original / "s2-wal.json"
    new_bytes = s2.read_bytes().replace(
        b"NATIVE_PLACE_MOVE_NO_PROGRESS", b"NATIVE_MOVE_SETTLED",
    )
    assert new_bytes != s2.read_bytes()
    s2.write_bytes(new_bytes)
    # The new synthetic S2 state remains terminal and Q1b accepts the same
    # S1 history, but committed S2 blob does not match changed original bytes.
    assert _verify(original, anchor, claims)["s2_wal_sha256"] == _sha(new_bytes)
    with pytest.raises(QCoupledCustodyHold):
        _run_coupled(original, repo, anchor, claims, git)


def test_q1e_rejects_supplied_or_preverified_receipt_without_raw_source(tmp_path):
    original, anchor, _row, claims = _setup(tmp_path)
    repo, git = _coupled_git_fixture(
        tmp_path, anchor_bytes=anchor,
        s2_wal=(original / "s2-wal.json").read_bytes(),
    )
    claims["supplied_receipt"] = {
        "classification": "Q1B_PINNED_S1_S2_WAL_PREFIX_CPU_OFFLINE_DEV",
    }
    with pytest.raises(QCoupledCustodyHold, match="exact"):
        _run_coupled(original, repo, anchor, claims, git)


def test_q1e_rejects_duplicate_git_sha_claim_or_missing_file(tmp_path):
    original, anchor, _row, claims = _setup(tmp_path)
    repo, git = _coupled_git_fixture(
        tmp_path, anchor_bytes=anchor,
        s2_wal=(original / "s2-wal.json").read_bytes(),
    )
    git["s2_path"] = git["anchor_path"]
    with pytest.raises(QCoupledCustodyHold):
        _run_coupled(original, repo, anchor, claims, git)
    git["s2_path"] = "proof/s2-wal.json"
    (original / "s1-checkpoint.json").unlink()
    with pytest.raises(QCoupledCustodyHold):
        _run_coupled(original, repo, anchor, claims, git)


def test_q1e_rejects_original_wal_mutated_mid_composite_inspection(
    tmp_path, monkeypatch,
):
    from experiments import q_lane_coupled_custody_dev as coupled

    original, anchor, _row, claims = _setup(tmp_path)
    repo, git = _coupled_git_fixture(
        tmp_path, anchor_bytes=anchor,
        s2_wal=(original / "s2-wal.json").read_bytes(),
    )
    old_git = coupled.inspect_git_pre_s2_custody
    calls = 0

    def mutate_source_after_git_read(*args, **kwargs):
        nonlocal calls
        receipt = old_git(*args, **kwargs)
        calls += 1
        if calls == 1:
            path = original / "s2-wal.json"
            path.write_bytes(path.read_bytes().replace(
                b"NATIVE_PLACE_MOVE_NO_PROGRESS", b"NATIVE_MOVE_SETTLED",
            ))
        return receipt

    monkeypatch.setattr(
        coupled, "inspect_git_pre_s2_custody", mutate_source_after_git_read,
    )
    with pytest.raises(QCoupledCustodyHold):
        _run_coupled(original, repo, anchor, claims, git)
    assert calls == 1


def test_q1e_rejects_git_head_drift_during_final_wal_readback(
    tmp_path, monkeypatch,
):
    from experiments import q_lane_coupled_custody_dev as coupled

    original, anchor, _row, claims = _setup(tmp_path)
    repo, git = _coupled_git_fixture(
        tmp_path, anchor_bytes=anchor,
        s2_wal=(original / "s2-wal.json").read_bytes(),
    )
    original_verify = coupled.verify_s1_s2_anchor
    calls = 0

    def advance_head_on_second_original_read(*args, **kwargs):
        nonlocal calls
        receipt = original_verify(*args, **kwargs)
        calls += 1
        if calls == 2:
            (repo / "unrelated.txt").write_text("new Git HEAD\n")
            subprocess.run(
                ["git", "-C", str(repo), "add", "unrelated.txt"], check=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-qm", "change HEAD mid-audit"],
                check=True,
            )
        return receipt

    monkeypatch.setattr(
        coupled, "verify_s1_s2_anchor", advance_head_on_second_original_read,
    )
    with pytest.raises(QCoupledCustodyHold):
        _run_coupled(original, repo, anchor, claims, git)
    assert calls == 2
