"""R0.6: B + unified I CURRENT alignment remains non-mutating and fail-closed."""
from dataclasses import FrozenInstanceError, replace

import pytest

import relay_self.r06_unified_context_preflight_dev as r06
from relay_self.i_unified_b_exploration_dev import (
    prepare_i_unified_exploration_turn,
)
from relay_self.r0_cognitive_context_dev import read_original_owner_current
from relay_self.r06_unified_context_preflight_dev import (
    R06_EXTERNAL_HOLDS,
    R06UnifiedCurrentAudit,
    audit_r06_unified_b_i_current,
)
from relay_self.three_self_present import EpistemicStatus
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files


def _args(case, sid="A"):
    _, bridge, boot, world, links, _ = case
    return dict(bridge=bridge, boot=boot, world=world, links=links, self_id=sid)


def _state(bridge):
    return {
        sid: (o.retained, o.intent, o.pattern_registry, dict(o.skills),
              set(o.pending_questions))
        for sid, o in bridge.owners.items()
    }


@pytest.mark.parametrize("sid", ("A", "B"))
def test_b_i_same_original_owner_read_only_current_and_schema_need(
    tmp_path, monkeypatch, sid,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    before_files = _files(bridge)
    before_state = _state(bridge)
    before_turns = dict(bridge.cognitive_work._coverage_adoption_turns)
    report = audit_r06_unified_b_i_current(**_args(case, sid))
    assert report.self_id == sid
    assert report.r05_stage28_aligned
    assert report.unified_b_i_current_aligned
    assert report.schema_signal_refs and len(report.schema_signal_refs) == 1
    assert len(report.source_revision_refs) == 2
    assert report.blockers == R06_EXTERNAL_HOLDS
    assert not report.r1_shadow_allowed
    original = bridge.cognitive_work.read_present_cpu(**_args(case, sid))
    current = read_original_owner_current(
        **_args(case, sid), signals=(original.exploration_need.signal,),
    )
    assert current.coverage is EpistemicStatus.UNKNOWN
    assert current.signals[0].envelope.event_id == report.schema_signal_refs[0]
    assert original.present.three_self.source_revision_refs == report.source_revision_refs
    assert _files(bridge) == before_files
    assert _state(bridge) == before_state
    # Unlike prepare_i_unified_exploration_turn, the R0.6 checker does
    # not even register a transient B CoverageAdoptionTurn.
    assert dict(bridge.cognitive_work._coverage_adoption_turns) == before_turns


def test_b_i_without_need_can_compare_but_never_infer_exploration(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch, need=False)
    result = audit_r06_unified_b_i_current(**_args(case))
    assert result.unified_b_i_current_aligned
    assert result.schema_signal_refs == ()
    assert not result.r1_shadow_allowed


@pytest.mark.parametrize("failure", (
    "paper", "native", "registry", "retired", "no_schema",
    "owner_swap", "world_epoch",
))
def test_b_i_stale_or_foreign_source_remains_hold(tmp_path, monkeypatch, failure):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    if failure == "paper":
        bridge.paper._session_id = "other-paper"
    elif failure == "native":
        bridge.owners["A"].current_worldbody_observation = replace(
            bridge.owners["A"].current_worldbody_observation,
        )
    elif failure == "registry":
        owner = bridge.owners["A"]
        owner.pattern_registry = replace(owner.pattern_registry, revision=77)
    elif failure == "retired":
        bridge.cognitive_work.fence_self("A")
    elif failure == "no_schema":
        del bridge.cognitive_work._present_schemas["A"]
    elif failure == "owner_swap":
        bridge.owners["A"] = bridge.owners["B"]
    elif failure == "world_epoch":
        bridge.cognitive_work._states["A"].world_epoch += 1
    result = audit_r06_unified_b_i_current(**_args(case))
    assert not result.unified_b_i_current_aligned
    assert not result.r1_shadow_allowed
    assert set(R06_EXTERNAL_HOLDS).issubset(result.blockers)


def test_r06_rejects_forged_unified_i_native_revision(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    real = r06.read_i_unified_b_current

    def forged(**kw):
        read = real(**kw)
        bad = replace(
            read.context.current,
            source=replace(
                read.context.current.source,
                native_probe_seq=read.context.current.source.native_probe_seq + 1,
            ),
        )
        return replace(read, context=replace(read.context, current=bad))

    monkeypatch.setattr(r06, "read_i_unified_b_current", forged)
    report = audit_r06_unified_b_i_current(**_args(case))
    assert "B_I_UNIFIED_CONTEXT_SOURCE_DIVERGED" in report.blockers
    assert not report.unified_b_i_current_aligned


def test_r06_rechecks_paper_change_between_b_and_i(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    original = r06.read_i_unified_b_current
    bridge = case[1]

    def changed(**kw):
        result = original(**kw)
        bridge.paper._session_id = "changed-during-read"
        return result

    monkeypatch.setattr(r06, "read_i_unified_b_current", changed)
    result = audit_r06_unified_b_i_current(**_args(case))
    assert not result.unified_b_i_current_aligned
    assert "B_I_UNIFIED_CURRENT_UNQUALIFIED" in result.blockers
    assert not result.r1_shadow_allowed


def test_r06_cannot_upgrade_cpu_comparison_to_r1_authorization(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch)
    report = audit_r06_unified_b_i_current(**_args(case))
    assert report.unified_b_i_current_aligned
    with pytest.raises(ValueError):
        replace(report, r1_shadow_allowed=True)
    with pytest.raises(ValueError):
        replace(report, blockers=())
    with pytest.raises(ValueError):
        replace(report, r05_stage28_aligned=False)
    with pytest.raises(FrozenInstanceError):
        report.unified_b_i_current_aligned = False
    for name in ("issue_action", "adopt_question", "retain_memory",
                 "open_gpu_ticket", "start_shadow", "prepare_s2"):
        assert not hasattr(report, name)


def test_r06_does_not_substitute_for_b_original_i_exploration_turn(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    before_files = _files(bridge)
    r06_report = audit_r06_unified_b_i_current(**_args(case))
    assert r06_report.unified_b_i_current_aligned
    # I still requires its separately validated B-owned turn; this is
    # independent CPU fixture evidence, never an R1 admission or L1 GPU POST.
    receipt = prepare_i_unified_exploration_turn(**_args(case))
    assert receipt.context.current.source_revision_refs == r06_report.source_revision_refs
    assert receipt.context.current.signals[0].envelope.event_id == r06_report.schema_signal_refs[0]
    assert receipt.original_owner is bridge.owners["A"]
    assert receipt.question_adopted is False
    assert receipt.memory_writer is False
    assert receipt.physical_issue_authorized is False
    assert _files(bridge) == before_files
