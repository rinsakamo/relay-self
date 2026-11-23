"""Independent Q R2-1: read-only original Owner Context, no L1/Physical grant.

Uses the pinned R2-1 product through genuine existing Original Owner
CPU fixtures. Synthetic Paper/Node source fixtures are not real World proof.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from relay_self.persistent_cognition import Memory, save_persistent_cognition
from relay_self.provenance import Provenance
from relay_self.r1_owner_context_shadow_dev import (
    R1ShadowComparison,
    R1ShadowStatus,
    compare_original_owner_r1_shadow,
    r1_shadow_is_live,
)
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkError
from relay_self.three_self_present import EpistemicStatus
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files
from test_r1_owner_context_shadow_dev import (
    _args,
    _seed_original_accepted_question,
    _snapshot,
)


@pytest.mark.parametrize("sid", ["A", "B"])
def test_q_r2_1_same_original_owner_gate_and_read_only_sources(tmp_path, monkeypatch, sid):
    case = _configured(tmp_path, monkeypatch, need=True)
    _, bridge, boot, world, links, _ = case
    resident = bridge.cognitive_work
    before = (_files(bridge), _snapshot(bridge))
    old_events = {
        k: tuple(v.intent.events) for k, v in resident.owners.items()
    }
    old_turns = dict(resident._coverage_adoption_turns)
    readout = resident.read_context_shadow_cpu(**_args(case, sid))
    assert type(readout) is R1ShadowComparison
    assert readout == compare_original_owner_r1_shadow(**_args(case, sid))
    assert readout.self_id == sid
    assert readout.status is R1ShadowStatus.MATCH
    assert readout.context.current.scope.self_id == sid
    assert readout.context.current.coverage is EpistemicStatus.UNKNOWN
    assert readout.context.recent.entries == ()
    assert readout.context.retrieved.references == ()
    assert readout.l1_input_switched is False
    assert readout.physical_authorized is False
    assert readout.memory_adopted is False
    assert resident.owners[sid] is bridge.owners[sid]
    assert r1_shadow_is_live(
        readout, bridge=bridge, boot=boot, world=world, links=links,
    )
    assert before == (_files(bridge), _snapshot(bridge))
    assert dict(resident._coverage_adoption_turns) == old_turns
    assert old_events == {
        k: tuple(v.intent.events) for k, v in resident.owners.items()
    }
    assert all(not x.supervisor.open_actions for x in resident.owners.values())


@pytest.mark.parametrize("fault", [
    "swapped-original-owner", "foreign-resident", "foreign-self",
    "missing-registered-schema", "registry-revision", "paper-swapped",
    "native-stale", "resident-epoch", "world-epoch", "resident-offline",
    "invalid-boot", "invalid-world", "corrupted-retained-disk",
    "unaccepted-memory", "duplicate-memory", "bad-limit",
    "boolean-limit", "malformed-selector",
])
def test_q_r2_1_original_source_and_selector_fail_closed(tmp_path, monkeypatch, fault):
    case = _configured(tmp_path, monkeypatch, need=True)
    _, bridge, _boot, _world, _links, _ = case
    resident = bridge.cognitive_work
    args = _args(case)
    if fault == "swapped-original-owner":
        bridge.owners["A"] = bridge.owners["B"]
    elif fault == "foreign-resident":
        from types import SimpleNamespace

        args["bridge"] = SimpleNamespace(
            cognitive_work=object(), owners=dict(bridge.owners),
        )
    elif fault == "foreign-self":
        args["self_id"] = "not-A-or-B"
    elif fault == "missing-registered-schema":
        del resident._present_schemas["A"]
    elif fault == "registry-revision":
        owner = bridge.owners["A"]
        owner.pattern_registry = replace(owner.pattern_registry, revision=700)
    elif fault == "paper-swapped":
        bridge.paper._session_id = "foreign-paper"
    elif fault == "native-stale":
        bridge.owners["A"].current_worldbody_observation = (
            bridge.last_login_observations["B"]
        )
    elif fault == "resident-epoch":
        resident._states["A"].epoch += 1
    elif fault == "world-epoch":
        resident._states["A"].world_epoch += 1
    elif fault == "resident-offline":
        resident._states["A"].mode = "OFFLINE"
    elif fault == "invalid-boot":
        args["boot"] = object()
    elif fault == "invalid-world":
        args["world"] = object()
    elif fault == "corrupted-retained-disk":
        bridge.owners["A"].files.cognition_file.write_text("{}")
    elif fault == "unaccepted-memory":
        args["memory_ids"] = ("unknown-previous-World",)
    elif fault == "duplicate-memory":
        args["memory_ids"] = ("same", "same")
    elif fault == "bad-limit":
        args["recent_limit"] = 17
    elif fault == "boolean-limit":
        args["recent_limit"] = True
    elif fault == "malformed-selector":
        args["memory_ids"] = ["untrusted-list"]
    before = _files(bridge)
    with pytest.raises(ResidentCognitiveWorkError):
        resident.read_context_shadow_cpu(**args)
    assert _files(bridge) == before


def test_q_r2_1_fresh_owner_read_rejects_semantic_schema_mismatch(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    resident = case[1].cognitive_work
    original = resident.read_present_cpu

    def forged_legacy(**kwargs):
        legacy = original(**kwargs)
        return replace(
            legacy, present=replace(
                legacy.present,
                attention_refs=("foreign-subjective-attention",),
            ),
        )

    monkeypatch.setattr(resident, "read_present_cpu", forged_legacy)
    with pytest.raises(ResidentCognitiveWorkError):
        resident.read_context_shadow_cpu(**_args(case))


def test_q_r2_1_owner_pointer_replaced_between_legacy_reads(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    resident = bridge.cognitive_work
    original = resident.read_present_cpu
    count = 0

    def changed_owner_after_first_read(**kwargs):
        nonlocal count
        present = original(**kwargs)
        count += 1
        if count == 1:
            bridge.owners["A"] = bridge.owners["B"]
        return present

    monkeypatch.setattr(resident, "read_present_cpu", changed_owner_after_first_read)
    with pytest.raises(ResidentCognitiveWorkError):
        resident.read_context_shadow_cpu(**_args(case))


@pytest.mark.parametrize("change", ["paper", "owner-question", "memory-disk"])
def test_q_r2_1_cached_return_is_not_an_admission_token(
    tmp_path, monkeypatch, change,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    owner = bridge.owners["A"]
    args = _args(case)
    if change == "owner-question":
        qref = _seed_original_accepted_question(case)
    elif change == "memory-disk":
        memory = Memory(
            "original-archived", "historical not live World truth",
            Provenance("previous-world", "historical"),
            Provenance("original-owner", "stored"),
        )
        owner.retain_memory(memory)
        save_persistent_cognition(owner.files.cognition_file, owner.retained)
        args["memory_ids"] = (memory.memory_id,)
    baseline = _files(bridge)
    report = bridge.cognitive_work.read_context_shadow_cpu(**args)
    assert report.status is R1ShadowStatus.MATCH
    assert not report.physical_authorized
    assert not report.l1_input_switched
    assert not report.memory_adopted
    if change == "paper":
        bridge.paper._session_id = "paper-new-external"
    elif change == "owner-question":
        cont = owner.retained.exploration_continuity
        new = replace(
            cont, revision=cont.revision + 1,
            questions=(replace(cont.questions[0], open=False),),
        )
        owner.retained = replace(owner.retained, exploration_continuity=new)
        owner.pending_questions.remove(qref)
        save_persistent_cognition(owner.files.cognition_file, owner.retained)
    else:
        owner.files.cognition_file.write_text('{"tampered":true}')
    assert not r1_shadow_is_live(
        report, bridge=bridge, boot=case[2], world=case[3], links=case[4],
    )
    with pytest.raises(ResidentCognitiveWorkError):
        bridge.cognitive_work.read_context_shadow_cpu(**args)
    if change == "paper":
        assert _files(bridge) == baseline
    for field in ("physical_authorized", "l1_input_switched", "memory_adopted"):
        with pytest.raises(ValueError):
            replace(report, **{field: True})
    with pytest.raises(FrozenInstanceError):
        report.status = R1ShadowStatus.HOLD


def test_q_r2_1_original_memory_cannot_become_observed_world_truth(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    owner = bridge.owners["A"]
    mem = Memory(
        "original-Q-indirect", "old subjective conclusion",
        Provenance("previous-world", "old-forecast"),
        Provenance("original-owner", "historical-archive"),
    )
    owner.retain_memory(mem)
    save_persistent_cognition(owner.files.cognition_file, owner.retained)
    before = _files(bridge)
    report = bridge.cognitive_work.read_context_shadow_cpu(
        **_args(case), memory_ids=(mem.memory_id,),
    )
    assert report.status is R1ShadowStatus.MATCH
    item, = report.context.retrieved.references
    assert item.status is EpistemicStatus.REMEMBERED
    assert item.applicability == "UNKNOWN"
    assert not hasattr(item, "content")
    assert report.context.current.coverage is EpistemicStatus.UNKNOWN
    assert report.accepted_question_refs == ()
    assert _files(bridge) == before
