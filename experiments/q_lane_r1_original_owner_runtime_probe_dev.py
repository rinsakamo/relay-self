"""Q independent R1 runtime probes against an exact *separate* R1 Git worktree.

This file is intentionally under experiments/, not collected by Q's normal
pytest run: only the pinned-object Actions job runs it with R1's original
source and original B synthetic fixtures on sys.path. No WSL/World/Gemma.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from relay_self.persistent_cognition import Memory, save_persistent_cognition
from relay_self.provenance import Provenance
from relay_self.r1_owner_context_shadow_dev import (
    R1ShadowStatus,
    compare_original_owner_r1_shadow,
    r1_shadow_is_live,
)
from relay_self.three_self_present import EpistemicStatus
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files


def _params(case, sid="A"):
    _, bridge, boot, world, links, _ = case
    return dict(bridge=bridge, boot=boot, world=world, links=links, self_id=sid)


def _alive(case, report):
    p = _params(case)
    return r1_shadow_is_live(
        report, bridge=p["bridge"], boot=p["boot"],
        world=p["world"], links=p["links"],
    )


def _state(bridge):
    return {
        sid: (owner.retained, owner.intent.events, tuple(owner.skills.items()),
              frozenset(owner.pending_questions), owner.pattern_registry,
              owner.native_session_id, owner.last_observed_tick)
        for sid, owner in bridge.owners.items()
    }


@pytest.mark.parametrize("sid", ("A", "B"))
def test_q_original_b_present_matches_read_only_r1_and_no_authority(
    tmp_path, monkeypatch, sid,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    state_before = _state(bridge)
    files_before = _files(bridge)
    turns_before = dict(bridge.cognitive_work._coverage_adoption_turns)
    original = bridge.cognitive_work.read_present_cpu(**_params(case, sid))
    result = compare_original_owner_r1_shadow(**_params(case, sid))
    assert result.status is R1ShadowStatus.MATCH
    assert result.context is not None
    assert original.present.signals == result.context.current.signals
    assert original.source == result.context.current.source
    assert original.schema == result.context.current.schema
    assert original.present.three_self.scope == result.context.current.scope
    assert original.present.three_self.source_revision_refs == (
        result.context.current.source_revision_refs
    )
    assert result.context.current.coverage is EpistemicStatus.UNKNOWN
    assert result.context.recent.entries == ()
    assert result.context.retrieved.references == ()
    assert not result.l1_input_switched
    assert not result.physical_authorized
    assert not result.memory_adopted
    assert _alive(case, result)
    assert _state(bridge) == state_before
    assert _files(bridge) == files_before
    assert dict(bridge.cognitive_work._coverage_adoption_turns) == turns_before


@pytest.mark.parametrize("field,value", (
    ("need_refs", ("old-no-longer-qualified-need",)),
    ("attention_refs", ("old-attention-revision",)),
    ("frame_revision", 915),
    ("registry_revision", 916),
))
def test_q_cached_match_must_be_revoked_by_legacy_present_drift(
    tmp_path, monkeypatch, field, value,
):
    """Even without Native/Paper movement, legacy Present drift is stale."""
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    old = compare_original_owner_r1_shadow(**_params(case))
    assert old.status is R1ShadowStatus.MATCH
    assert _alive(case, old)
    original_reader = bridge.cognitive_work.read_present_cpu

    def changed_original_present(**kw):
        view = original_reader(**kw)
        return replace(view, present=replace(view.present, **{field: value}))

    monkeypatch.setattr(bridge.cognitive_work, "read_present_cpu",
                        changed_original_present)
    assert not _alive(case, old), (
        f"R1 cached MATCH incorrectly survived original Present {field} drift"
    )


@pytest.mark.parametrize("tamper", (
    "other-self", "paper-session", "owner-epoch", "retained-disk",
))
def test_q_original_owner_foreign_or_expired_source_never_lives(
    tmp_path, monkeypatch, tamper,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    report = compare_original_owner_r1_shadow(**_params(case))
    assert report.status is R1ShadowStatus.MATCH
    if tamper == "other-self":
        bridge.owners["A"] = bridge.owners["B"]
    elif tamper == "paper-session":
        bridge.paper._session_id = "q-foreign-paper"
    elif tamper == "owner-epoch":
        bridge.cognitive_work._states["A"].epoch += 1
    else:
        owner = bridge.owners["A"]
        owner.files.cognition_file.write_text('{"forged":true}')
    assert not _alive(case, report)
    fresh = compare_original_owner_r1_shadow(**_params(case))
    assert fresh.status is R1ShadowStatus.HOLD
    assert fresh.context is None
    assert fresh.memory_adopted is False


def test_q_original_memory_is_digest_only_and_retired_reference_fails(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    owner = case[1].owners["A"]
    owner.retain_memory(Memory(
        "q-original-memory", "historical fact cannot become current observation",
        Provenance("prior-world", "q-observation"),
        Provenance("original-owner", "q-retain"),
    ))
    save_persistent_cognition(owner.files.cognition_file, owner.retained)
    state = _state(case[1])
    files = _files(case[1])
    report = compare_original_owner_r1_shadow(
        **_params(case), memory_ids=("q-original-memory",),
    )
    assert report.status is R1ShadowStatus.MATCH
    assert _alive(case, report)
    mem = report.context.retrieved.references
    assert len(mem) == 1
    assert mem[0].memory_id == "q-original-memory"
    assert mem[0].status is EpistemicStatus.REMEMBERED
    assert mem[0].applicability == "UNKNOWN"
    assert not hasattr(mem[0], "content")
    assert _state(case[1]) == state and _files(case[1]) == files
    owner.retained = replace(owner.retained, memories=())
    assert not _alive(case, report)


def test_q_unaccepted_inference_reference_cannot_become_recent(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    case[1].owners["A"].pending_questions.add("unadopted-model-timeout")
    before = _files(case[1])
    report = compare_original_owner_r1_shadow(**_params(case))
    assert report.status is R1ShadowStatus.MATCH
    assert report.context.recent.entries == ()
    assert report.accepted_question_refs == ()
    assert _alive(case, report)
    assert _files(case[1]) == before
