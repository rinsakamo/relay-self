"""RSEE R4 offline tests: no S3 action cannot become V evidence."""
from __future__ import annotations

import json

import pytest

from experiments.standard_env import s3_v_projection as r4
from experiments.standard_env import shared_runtime as r1
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance


@pytest.fixture
def original_projection(tmp_path):
    derived = tmp_path / "derived"
    original = tmp_path / "native-originals"
    derived.mkdir()
    original.mkdir()
    sid = "session-native-1"
    head = r4.S3_HEAD
    profile = "b" * 64

    events = derived / "session_events.jsonl"
    snapshot = derived / "s3_observed_memory.json"
    cleanup = derived / "owned_cleanup.json"
    envelope = original / "source_envelope.json"
    primary = original / "native_original.jsonl"
    outcome = original / "s16_action_original.jsonl"
    primary.write_bytes(b'{"source":"original"}\n')
    outcome.write_bytes(b'{"source":"typed S16 outcome"}\n')

    def store_events(rows):
        with events.open("w", encoding="utf-8") as handle:
            for i, row in enumerate(rows):
                record = {
                    "schema": r4.EVENT_SCHEMA, "session": sid,
                    "source": "S49_OWNER_EXPLICIT_REAL_OR_SYNTHETIC",
                    "index": i, **row,
                }
                handle.write(json.dumps(record, sort_keys=True) + "\n")

    def store_memory(rows):
        memory_objects = tuple(
            Memory(
                memory_id=row["id"], content=json.dumps(row["content"]),
                source_provenance=Provenance("mineflayer", f"{sid}:4"),
                integration_provenance=Provenance(
                    "self-s3-original-s16-observation",
                    f"{sid}:{row['content']['action_id']}:{row['content']['evidence_sha256']}",
                ),
            ) for row in rows
        )
        cognition = PersistentCognition(
            IdentitySpecification(
                f"s3-session:{sid}", ("Observe only",),
                Provenance("self-s3-operator", f"session:{sid}"),
            ),
            memories=memory_objects,
        )
        save_persistent_cognition(snapshot, cognition)

    cleanup.write_text(json.dumps({
        "schema": r4.CLEANUP_SCHEMA, "session": sid,
        "node_exit": 0, "server_exit": 0,
        "native_stop_ack": False, "model_stop_ack": False,
        "gpu_release_claimed": False, "physical_action_replay": False,
    }), encoding="utf-8")
    hashes = r1.read_only_receipt_index({"native": primary, "outcome": outcome})
    envelope.write_text(json.dumps({
        "schema": r1.SCHEMA, "lane": "S", "source_head": head,
        "environment_profile_sha256": profile,
        "source_session": sid,
        "world_identity": None, "model_identity": None,
        "original_receipt_refs": [
            {"path": str(primary), "sha256": hashes[str(primary)]},
        ],
        "action_outcome_refs": [
            {"path": str(outcome), "sha256": hashes[str(outcome)]},
        ],
        "cleanup_observations": {"source": "REPORTED_ONLY"},
        "terminal_classification": "S3_REPORTED_ONLY",
        "evidence_sha256_index": hashes,
        "physical_execution_authorized": False,
        "science_qualified": False,
        "timeline_is_physical_proof": False,
    }), encoding="utf-8")
    kwargs = dict(
        derived_root=derived, events=events, memory=snapshot, cleanup=cleanup,
        envelope=envelope, original_root=original,
        expected_head=head, expected_profile_sha256=profile,
        expected_session=sid,
    )
    zero = [
        {"kind": "session_started"},
        {"kind": "session_terminal", "terminal": "EVENT_BUDGET_ENDED"},
    ]
    store_events(zero)
    store_memory([])
    return {
        "kwargs": kwargs, "store_events": store_events,
        "store_memory": store_memory, "sid": sid,
        "primary": primary, "outcome": outcome, "envelope": envelope,
        "events": events, "memory": snapshot, "cleanup": cleanup,
    }


def with_retention(fixture):
    sid = fixture["sid"]
    digest = "c" * 64
    memory_id = f"l1:{sid}:s49-native-move-2:4"
    episode = {
        "schema": r4.EPISODE_SCHEMA, "session_id": sid,
        "world_revision": 4, "action_id": "s49-native-move-2",
        "binding_id": "s49-binding-2", "action_ref": "MOVE_BACKWARD",
        "source_status": "OBSERVED_NATIVE",
        "disposition": "outcome", "reason_code": "S16_NATIVE_MOVEMENT",
        "evidence_sha256": digest, "cue_tags": ["near_zombie"],
        "hypothesis": None,
    }
    fixture["store_memory"]([{"id": memory_id, "content": episode}])
    fixture["store_events"]([
        {"kind": "session_started"},
        {"kind": "experience_retained_observation",
         "memory_id": memory_id, "evidence_sha256": digest, "source_seq": 4,
         "session": sid, "action_authority": False,
         "goal_success_attested": False,
         "learning_updates": 0, "habit_grants": 0},
        {"kind": "session_terminal", "terminal": "EVENT_BUDGET_ENDED"},
    ])
    return memory_id


def test_plan_no_files_and_no_model(monkeypatch, capsys):
    def fail(*_args, **_kwargs):
        pytest.fail("default R4 plan must not inspect actual files")
    monkeypatch.setattr(r4, "audit", fail)
    assert r4.main([]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["classification"] == "RSEE_R4_PLAN_ONLY"
    assert report["physical_execution_authorized"] is False


def test_zero_retention_is_not_an_action_or_v_go(original_projection, monkeypatch):
    def fail(*_args, **_kwargs):
        pytest.fail("no Action means no R2 handoff")
    monkeypatch.setattr(r4.r2, "audit_file", fail)
    report = r4.audit(**original_projection["kwargs"])
    assert report["classification"] == "RSEE_R4_NO_RETAINED_ACTION_NOT_V_ADMISSIBLE"
    assert report["r2_original_bytes"] == "NOT_CHECKED"
    assert report["retained_observation_count"] == 0
    assert report["v_admission_granted"] is False
    assert report["science_qualified"] is False


def test_derived_retention_and_independent_raw_bytes_reviewer_only(original_projection):
    with_retention(original_projection)
    got = r4.audit(**original_projection["kwargs"])
    assert got["classification"] == "RSEE_R4_DERIVED_MEMORY_MATCH_R2_BYTES_REVIEW_ONLY"
    assert got["retained_observation_count"] == 1
    assert got["original_action_file_count"] == 1
    assert got["r2_original_bytes"] == "RSEE_R2_RAW_BYTES_MATCH_REVIEW_ONLY"
    assert got["native_source_semantics_attested"] is False
    assert got["action_correlation_attested"] is False
    assert got["v_result"] == "UNDETERMINED_INDEPENDENT_V_OWNER_REQUIRED"
    assert got["v_admission_granted"] is False
    assert got["science_qualified"] is False


@pytest.mark.parametrize(("key", "value", "reason"), [
    ("expected_head", "a" * 40, "pinned S3-lineage source HEAD"),
    ("expected_session", "other", "S3 event identity/order/source mismatch"),
    ("expected_profile_sha256", "wrong", "profile SHA256"),
])
def test_independent_source_identity_fail_closed(original_projection, key, value, reason):
    kw = dict(original_projection["kwargs"])
    kw[key] = value
    with pytest.raises(r4.R4Rejected, match=reason):
        r4.audit(**kw)


def test_retained_event_memory_mismatch_rejected(original_projection):
    with_retention(original_projection)
    src = original_projection["events"]
    raw = src.read_text(encoding="utf-8").replace('"source_seq": 4', '"source_seq": 99')
    src.write_text(raw, encoding="utf-8")
    with pytest.raises(r4.R4Rejected, match="evidence lineage"):
        r4.audit(**original_projection["kwargs"])


def test_stale_memory_without_source_event_rejected(original_projection):
    with_retention(original_projection)
    original_projection["store_events"]([
        {"kind": "session_started"}, {"kind": "session_terminal"},
    ])
    with pytest.raises(r4.R4Rejected, match="Memory count mismatch"):
        r4.audit(**original_projection["kwargs"])


def test_source_is_reported_and_cannot_be_science_or_action(original_projection):
    with_retention(original_projection)
    path = original_projection["events"]
    text = path.read_text()
    path.write_text(text.replace('"action_authority": false', '"action_authority": true'))
    with pytest.raises(r4.R4Rejected, match="authority mismatch"):
        r4.audit(**original_projection["kwargs"])


def test_original_byte_tamper_requires_r2_failure(original_projection):
    with_retention(original_projection)
    original_projection["outcome"].write_bytes(b"forged original")
    with pytest.raises(r4.R4Rejected, match="R2 independent raw-source handoff blocked"):
        r4.audit(**original_projection["kwargs"])


def test_derived_snapshot_cannot_impersonate_raw(original_projection):
    with_retention(original_projection)
    idx = json.loads(original_projection["envelope"].read_text(encoding="utf-8"))
    primary = str(original_projection["primary"])
    derived = original_projection["memory"]
    idx["original_receipt_refs"][0]["path"] = str(derived)
    sha = r1.read_only_receipt_index({"derived": derived})[str(derived)]
    idx["original_receipt_refs"][0]["sha256"] = sha
    del idx["evidence_sha256_index"][primary]
    idx["evidence_sha256_index"][str(derived)] = sha
    original_projection["envelope"].write_text(json.dumps(idx))
    with pytest.raises(r4.R4Rejected, match="R2 independent raw-source handoff blocked"):
        r4.audit(**original_projection["kwargs"])


def test_missing_native_original_even_with_retained_json_rejected(original_projection):
    with_retention(original_projection)
    original_projection["primary"].unlink()
    with pytest.raises(r4.R4Rejected, match="R2 independent raw-source handoff blocked"):
        r4.audit(**original_projection["kwargs"])


def test_empty_event_or_missing_cleanup_blocks(original_projection):
    original_projection["cleanup"].unlink()
    with pytest.raises(r4.R4Rejected, match="derived"):
        r4.audit(**original_projection["kwargs"])
    original_projection["cleanup"].write_text("{}")
    with pytest.raises(r4.R4Rejected, match="cleanup status"):
        r4.audit(**original_projection["kwargs"])


def test_symlinked_derived_file_fails_closed(original_projection, tmp_path):
    root = original_projection["kwargs"]["derived_root"]
    alias = root / "alias-events.jsonl"
    alias.symlink_to(original_projection["events"])
    kw = dict(original_projection["kwargs"])
    kw["events"] = alias
    with pytest.raises(r4.R4Rejected, match="canonical physical derived file"):
        r4.audit(**kw)
    foreign = tmp_path / "outside.jsonl"
    foreign.write_bytes(original_projection["events"].read_bytes())
    kw["events"] = foreign
    with pytest.raises(r4.R4Rejected, match="outside independent output root"):
        r4.audit(**kw)


def test_duplicate_rows_and_missing_terminal_fail_closed(original_projection):
    events = original_projection["events"]
    row = json.loads(events.read_text().splitlines()[1])
    row["index"] = 2
    with events.open("a") as f:
        f.write(json.dumps(row) + "\n")
    with pytest.raises(r4.R4Rejected, match="duplicate terminal"):
        r4.audit(**original_projection["kwargs"])


def test_partial_unretained_action_blocks(original_projection):
    original_projection["store_events"]([
        {"kind": "session_started"},
        {"kind": "experience_not_retained", "reason": "ExperienceRejected"},
        {"kind": "session_terminal"},
    ])
    with pytest.raises(r4.R4Rejected, match="unretained Action"):
        r4.audit(**original_projection["kwargs"])


def test_no_hidden_grants_or_unauthorized_v_input(capsys):
    assert r4.main(["--verify"]) == 2
    output = json.loads(capsys.readouterr().out)
    assert output["classification"] == "RSEE_R4_EVIDENCE_CHAIN_BLOCKED"
    assert output["v_admission_granted"] is False


def test_cli_no_action_exits_nonzero_and_never_admits_v(original_projection, capsys):
    kw = original_projection["kwargs"]
    code = r4.main([
        "--verify",
        "--derived-root", str(kw["derived_root"]),
        "--original-root", str(kw["original_root"]),
        "--envelope", str(kw["envelope"]),
        "--expected-head", kw["expected_head"],
        "--expected-profile-sha256", kw["expected_profile_sha256"],
        "--expected-session", kw["expected_session"],
    ])
    assert code == 2
    result = json.loads(capsys.readouterr().out)
    assert result["classification"] == "RSEE_R4_NO_RETAINED_ACTION_NOT_V_ADMISSIBLE"
    assert result["v_admission_granted"] is False
    assert result["r2_original_bytes"] == "NOT_CHECKED"



def select_emitter_head(case, head):
    """Test-only rewrite of mock expected identity AND mock envelope source."""
    case["kwargs"]["expected_head"] = head
    path = case["envelope"]
    contents = json.loads(path.read_text(encoding="utf-8"))
    contents["source_head"] = head
    path.write_text(json.dumps(contents), encoding="utf-8")


def rename_original(case, source_key, new_name):
    """Keep R2 original paths/hashes source-shaped without inventing a run."""
    old = case[source_key]
    new = old.rename(old.parent / new_name)
    env = json.loads(case["envelope"].read_text(encoding="utf-8"))
    ref_key = "original_receipt_refs" if source_key == "primary" else "action_outcome_refs"
    for ref in env[ref_key]:
        if ref["path"] == str(old):
            ref["path"] = str(new)
    env["evidence_sha256_index"][str(new)] = env["evidence_sha256_index"].pop(
        str(old)
    )
    case["envelope"].write_text(json.dumps(env), encoding="utf-8")
    case[source_key] = new


def test_s3_s6_s7_pinned_exact_source_roster():
    assert set(r4.PINNED_S3_LINEAGE) == {
        r4.S3_HEAD, r4.S6_HEAD, r4.S7_HEAD,
    }
    assert len(set(r4.PINNED_S3_LINEAGE)) == 3


def test_s6_original_predecode_not_archived_is_never_reconstructed(
    original_projection, monkeypatch,
):
    with_retention(original_projection)
    select_emitter_head(original_projection, r4.S6_HEAD)
    # Even a forged synthetic source envelope cannot resurrect unarchived
    # native S6 bytes or become a positive V Action admission.
    def forbidden(*_args, **_kwargs):
        pytest.fail("R2 cannot retroactively check S6 unrecorded native stream")

    monkeypatch.setattr(r4.r2, "audit_file", forbidden)
    got = r4.audit(**original_projection["kwargs"])
    assert got["classification"] == "RSEE_R5_S6_DERIVED_ONLY_RAW_NOT_ARCHIVED"
    assert got["r2_original_bytes"] == "NOT_CHECKED"
    assert got["v_result"] == "NOT_ADMISSIBLE_MISSING_NATIVE_ORIGINAL"
    assert got["source_lineage_class"] == "S6_CONTROLLED_PHYSICAL_DERIVED_NO_BRIDGE_RAW"
    assert got["v_admission_granted"] is False
    assert got["science_qualified"] is False


def test_s6_derived_only_cli_exit_is_nonzero(original_projection, capsys):
    with_retention(original_projection)
    select_emitter_head(original_projection, r4.S6_HEAD)
    kw = original_projection["kwargs"]
    code = r4.main([
        "--verify",
        "--derived-root", str(kw["derived_root"]),
        "--original-root", str(kw["original_root"]),
        "--envelope", str(kw["envelope"]),
        "--expected-head", kw["expected_head"],
        "--expected-profile-sha256", kw["expected_profile_sha256"],
        "--expected-session", kw["expected_session"],
    ])
    assert code == 2
    data = json.loads(capsys.readouterr().out)
    assert data["classification"] == "RSEE_R5_S6_DERIVED_ONLY_RAW_NOT_ARCHIVED"


def test_s7_future_original_predecode_bridge_is_review_only(original_projection):
    with_retention(original_projection)
    select_emitter_head(original_projection, r4.S7_HEAD)
    rename_original(original_projection, "primary", r4.S7_RAW_RECEIVED)
    got = r4.audit(**original_projection["kwargs"])
    assert got["classification"] == "RSEE_R4_DERIVED_MEMORY_MATCH_R2_BYTES_REVIEW_ONLY"
    assert got["source_lineage_class"] == "S7_PROSPECTIVE_BRIDGE_RAW_PRODUCER_NOT_RUN"
    assert got["native_source_semantics_attested"] is False
    assert got["action_correlation_attested"] is False
    assert got["v_admission_granted"] is False
    assert got["science_qualified"] is False


def test_s7_missing_original_bridge_rejected_even_if_other_hashes_match(
    original_projection,
):
    with_retention(original_projection)
    select_emitter_head(original_projection, r4.S7_HEAD)
    with pytest.raises(r4.R4Rejected, match="S7 original predecode received bridge"):
        r4.audit(**original_projection["kwargs"])


def test_s7_sent_attempt_cannot_impersonate_s16_outcome(original_projection):
    with_retention(original_projection)
    select_emitter_head(original_projection, r4.S7_HEAD)
    rename_original(original_projection, "primary", r4.S7_RAW_RECEIVED)
    rename_original(original_projection, "outcome", r4.S7_RAW_SENT)
    with pytest.raises(r4.R4Rejected, match="sent command/derived SHA index"):
        r4.audit(**original_projection["kwargs"])


def test_s7_actual_raw_tamper_or_wrong_envelope_head_blocks(original_projection):
    with_retention(original_projection)
    select_emitter_head(original_projection, r4.S7_HEAD)
    rename_original(original_projection, "primary", r4.S7_RAW_RECEIVED)
    original_projection["primary"].write_bytes(b"modified bridge bytes")
    with pytest.raises(r4.R4Rejected, match="R2 independent raw-source handoff blocked"):
        r4.audit(**original_projection["kwargs"])
    original_projection["primary"].write_bytes(b'{"source":"original"}\n')
    env = json.loads(original_projection["envelope"].read_text(encoding="utf-8"))
    env["source_head"] = r4.S3_HEAD
    original_projection["envelope"].write_text(json.dumps(env), encoding="utf-8")
    with pytest.raises(r4.R4Rejected, match="R2 independent raw-source handoff blocked"):
        r4.audit(**original_projection["kwargs"])


def test_s6_zero_memory_is_still_no_retained_action(original_projection):
    select_emitter_head(original_projection, r4.S6_HEAD)
    got = r4.audit(**original_projection["kwargs"])
    assert got["classification"] == "RSEE_R4_NO_RETAINED_ACTION_NOT_V_ADMISSIBLE"
    assert got["source_lineage_class"] == "S6_CONTROLLED_PHYSICAL_DERIVED_NO_BRIDGE_RAW"
