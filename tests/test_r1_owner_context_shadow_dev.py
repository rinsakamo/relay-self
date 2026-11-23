"""R1 Owner Shadow hostile synthetic tests; never launch World/LLM or S1/S2."""
import json
from dataclasses import FrozenInstanceError, replace

import pytest

from relay_self.bd1b_question_store_dev import _store_current_inquiry
from relay_self.persistent_cognition import Memory
from relay_self.provenance import Provenance
from relay_self.r0_cognitive_context_dev import context_is_live
from relay_self.r1_owner_context_shadow_dev import (
    EXPECTED_SEMANTIC_DIFFERENCES,
    R1ShadowComparison,
    R1ShadowStatus,
    compare_original_owner_r1_shadow,
)
from relay_self.three_self_present import EpistemicStatus, Lens
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files


def _args(case, self_id="A"):
    _, bridge, boot, world, links, _ = case
    return dict(bridge=bridge, boot=boot, world=world, links=links, self_id=self_id)


def _snapshot(bridge):
    return {
        sid: (owner.retained, owner.intent.events, dict(owner.skills),
              set(owner.pending_questions), owner.pattern_registry)
        for sid, owner in bridge.owners.items()
    }


def _seed_original_accepted_question(case, *, choice="1", source="issuer-adopt"):
    """A synthetic *fixture* Owner storage event, NOT real Gemma attestation."""
    bridge = case[1]
    resident = bridge.cognitive_work
    inquiry = resident.read_coverage_inquiry_cpu(**_args(case))
    assert inquiry is not None
    owner = bridge.owners["A"]
    origin = Provenance(source, json.dumps({
        "work_ref": "fixture-original-job",
        "request_id": "fixture-original-request",
        "choice_id": choice,
    }, sort_keys=True))
    with resident.lock:
        _store_current_inquiry(
            resident, owner=owner, self_id="A", inquiry=inquiry,
            expected_revision=0, origin=origin,
        )
    return inquiry.question_ref


@pytest.mark.parametrize("sid", ("A", "B"))
def test_r1_shadow_compares_original_present_without_side_effect(
    tmp_path, monkeypatch, sid,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    prior_files = _files(bridge)
    prior_owner = _snapshot(bridge)
    prior_turns = dict(bridge.cognitive_work._coverage_adoption_turns)
    report = compare_original_owner_r1_shadow(**_args(case, sid))
    assert type(report) is R1ShadowComparison
    assert report.self_id == sid
    assert report.status is R1ShadowStatus.MATCH
    assert report.context is not None
    assert report.context.current.scope.self_id == sid
    assert report.context.current.coverage is EpistemicStatus.UNKNOWN
    assert len(report.context.current.signals) == 1
    assert report.legacy_body_claim_count >= 1
    assert report.context.recent.entries == ()
    assert report.context.retrieved.references == ()
    assert report.expected_differences == EXPECTED_SEMANTIC_DIFFERENCES
    assert report.l1_input_switched is False
    assert report.physical_authorized is False
    assert report.memory_adopted is False
    assert context_is_live(
        report.context, bridge=bridge, boot=case[2], world=case[3],
        links=case[4],
    )
    assert _files(bridge) == prior_files
    assert _snapshot(bridge) == prior_owner
    assert dict(bridge.cognitive_work._coverage_adoption_turns) == prior_turns
    for forbidden in ("issue_action", "start_shadow", "submit_llm", "commit_intent",
                      "finish_reviewed_skill", "adopt_question", "save_memory"):
        assert not hasattr(report, forbidden)


def test_r1_shadow_no_schema_need_stays_unknown(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=False)
    report = compare_original_owner_r1_shadow(**_args(case))
    assert report.status is R1ShadowStatus.MATCH
    assert report.context.current.signals == ()
    assert report.context.current.need_refs == ()
    assert report.context.recent.entries == ()


def test_r1_shadow_issuer_adopted_owner_question_is_subjective_only(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    question_ref = _seed_original_accepted_question(case)
    before_file = _files(case[1])
    before_owner = _snapshot(case[1])
    report = compare_original_owner_r1_shadow(**_args(case))
    assert report.status is R1ShadowStatus.MATCH
    assert report.accepted_question_refs == (question_ref,)
    assert report.context is not None
    entries = report.context.recent.entries
    assert len(entries) == 1
    assert entries[0].claim.lens is Lens.MYSELF
    assert entries[0].claim.status is EpistemicStatus.HYPOTHETICAL
    assert entries[0].claim.value_ref == question_ref
    assert entries[0].claim.source_refs[0].source == "issuer-adopt"
    assert entries[0].claim.source_revision_refs == ()
    assert entries[0].generation == 0  # no fabricated GPU result generation
    assert report.context.retrieved.references == ()
    assert _snapshot(case[1]) == before_owner
    assert _files(case[1]) == before_file


def test_r1_shadow_unadmitted_question_not_recent(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    _seed_original_accepted_question(case, source="coverage-inquiry")
    report = compare_original_owner_r1_shadow(**_args(case))
    assert report.status is R1ShadowStatus.MATCH
    assert report.accepted_question_refs == ()
    assert report.context.recent.entries == ()


def test_r1_shadow_forged_issuer_claim_cannot_become_recent(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    _seed_original_accepted_question(case, choice="2")
    report = compare_original_owner_r1_shadow(**_args(case))
    assert report.status is R1ShadowStatus.HOLD
    assert report.context is None
    assert report.accepted_question_refs == ()


def test_r1_shadow_existing_owner_memory_remembered_not_observed(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch)
    memory = Memory(
        "original-experience", "past action did not attest this new World",
        Provenance("native", "past-outcome"),
        Provenance("original-owner", "retained"),
    )
    case[1].owners["A"].retain_memory(memory)
    before_files = _files(case[1])
    report = compare_original_owner_r1_shadow(
        **_args(case), memory_ids=("original-experience",),
    )
    assert report.status is R1ShadowStatus.MATCH
    assert report.selected_memory_refs == ("original-experience",)
    assert len(report.context.retrieved.references) == 1
    ref = report.context.retrieved.references[0]
    assert ref.status is EpistemicStatus.REMEMBERED
    assert ref.applicability == "UNKNOWN"
    assert ref.revision_sha256 and len(ref.revision_sha256) == 64
    assert not hasattr(ref, "content")
    assert _files(case[1]) == before_files
    case[1].owners["A"].retained = replace(
        case[1].owners["A"].retained,
        memories=(replace(memory, content="tampered"),),
    )
    assert not context_is_live(
        report.context, bridge=case[1], boot=case[2], world=case[3],
        links=case[4],
    )


@pytest.mark.parametrize("failure", (
    "paper", "native", "epoch", "registry", "fence", "foreign-owner",
    "missing-schema", "cognition-file",
))
def test_r1_shadow_stale_foreign_and_disk_change_fail_closed(
    tmp_path, monkeypatch, failure,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    if failure == "paper":
        bridge.paper._session_id = "new-world-foreign"
    elif failure == "native":
        bridge.owners["A"].current_worldbody_observation = replace(
            bridge.owners["A"].current_worldbody_observation,
        )
    elif failure == "epoch":
        bridge.cognitive_work._states["A"].epoch += 1
    elif failure == "registry":
        owner = bridge.owners["A"]
        owner.pattern_registry = replace(owner.pattern_registry, revision=909)
    elif failure == "fence":
        bridge.cognitive_work.fence_self("A")
    elif failure == "foreign-owner":
        bridge.owners["A"] = bridge.owners["B"]
    elif failure == "missing-schema":
        del bridge.cognitive_work._present_schemas["A"]
    elif failure == "cognition-file":
        owner = bridge.owners["A"]
        owner.files.cognition_file.write_text('{"invalid":true}')
    result = compare_original_owner_r1_shadow(**_args(case))
    assert result.status is R1ShadowStatus.HOLD
    assert result.context is None
    assert not result.l1_input_switched
    assert not result.physical_authorized


def test_r1_shadow_reports_legacy_epoch_disagreement(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    resident = case[1].cognitive_work
    original = resident.read_present_cpu

    def fake_legacy(**kwargs):
        present = original(**kwargs)
        return replace(
            present, present=replace(
                present.present, frame_revision=present.present.frame_revision + 1,
            ),
        )

    monkeypatch.setattr(resident, "read_present_cpu", fake_legacy)
    result = compare_original_owner_r1_shadow(**_args(case))
    assert result.status is R1ShadowStatus.MISMATCH
    assert "LEGACY_OWNER_EPOCH_MISMATCH" in result.mismatch_codes
    assert result.context is not None


def test_r1_shadow_rejects_interleaved_paper_source_change(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    bridge = case[1]
    original = bridge.cognitive_work.read_present_cpu

    def changed_after_read(**kwargs):
        frame = original(**kwargs)
        bridge.paper._session_id = "paper-replaced-mid-read"
        return frame

    monkeypatch.setattr(bridge.cognitive_work, "read_present_cpu", changed_after_read)
    result = compare_original_owner_r1_shadow(**_args(case))
    assert result.status is R1ShadowStatus.HOLD
    assert result.context is None


@pytest.mark.parametrize("selector", (
    ("missing-unadopted-memory",),
    ("duplicate", "duplicate"),
    ("",),
))
def test_r1_shadow_refuses_unaccepted_memory_selector(tmp_path, monkeypatch, selector):
    case = _configured(tmp_path, monkeypatch)
    report = compare_original_owner_r1_shadow(
        **_args(case), memory_ids=selector,
    )
    assert report.status is R1ShadowStatus.HOLD
    assert report.context is None


def test_r1_shadow_l2_timeout_or_cancel_not_in_owner_cognition(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch)
    # Neither a failed L2 proposal nor any fake provider output is held by
    # original B retained owner; R1 must not invent a RECENT entry from it.
    case[1].owners["A"].pending_questions.add("L2-TIMEOUT-NOT-ADOPTED")
    result = compare_original_owner_r1_shadow(**_args(case))
    assert result.status is R1ShadowStatus.MATCH
    assert result.context.recent.entries == ()
    assert result.accepted_question_refs == ()
    assert result.memory_adopted is False


def test_r1_shadow_frozen_result_cannot_be_grant(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    result = compare_original_owner_r1_shadow(**_args(case))
    with pytest.raises(ValueError):
        replace(result, l1_input_switched=True)
    with pytest.raises(ValueError):
        replace(result, physical_authorized=True)
    with pytest.raises(ValueError):
        replace(result, memory_adopted=True)
    with pytest.raises(ValueError):
        replace(result, status=R1ShadowStatus.MATCH, mismatch_codes=("fake",))
    with pytest.raises(FrozenInstanceError):
        result.status = R1ShadowStatus.HOLD
