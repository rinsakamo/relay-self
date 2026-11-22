"""R0.5 hostile CPU-only Stage28 source and provenance compatibility controls."""
from dataclasses import FrozenInstanceError, replace

import pytest

from relay_self.common_io import ScopeRef
from relay_self.persistent_cognition import Memory
from relay_self.provenance import Provenance
from relay_self.r0_cognitive_context_dev import (
    CognitiveContext,
    R0ContextHold,
    Recent3SelfView,
    RecentCognitionEntry,
    RetrievedMemoryBundle,
    RetrievedMemoryRef,
    read_original_owner_current,
)
from relay_self.r05_context_compat_preflight_dev import (
    R1_EXTERNAL_HOLDS,
    R05CompatibilityAudit,
    audit_r05_initial_owner_context,
)
from relay_self.three_self_present import EpistemicStatus, Lens, LensClaim
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files


def _args(case, sid="A"):
    _, bridge, boot, world, links, _ = case
    return dict(bridge=bridge, boot=boot, world=world, links=links, self_id=sid)


@pytest.mark.parametrize("sid", ("A", "B"))
def test_r05_legacy_and_current_match_without_migrating_world_claims(
    tmp_path, monkeypatch, sid,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    before_files = _files(bridge)
    owners_before = {
        key: (o.retained, o.intent, o.pattern_registry, dict(o.skills),
              set(o.pending_questions))
        for key, o in bridge.owners.items()
    }
    result = audit_r05_initial_owner_context(**_args(case, sid))
    assert result.stage28_source_aligned
    assert result.schema_signal_count == 1
    assert result.blockers == R1_EXTERNAL_HOLDS
    assert not result.r1_shadow_allowed
    original = bridge.cognitive_work.read_present_cpu(**_args(case, sid))
    current = read_original_owner_current(
        **_args(case, sid), signals=(original.exploration_need.signal,),
    )
    assert original.source == current.source
    assert original.present.three_self.source_revision_refs == current.source_revision_refs
    assert any(
        claim.status is EpistemicStatus.OBSERVED
        for claim in original.present.three_self.self_body.claims
    )
    assert current.coverage is EpistemicStatus.UNKNOWN
    assert all(not isinstance(s, LensClaim) for s in current.signals)
    assert not hasattr(result, "start_shadow")
    assert not hasattr(result, "approve_r1")
    assert _files(bridge) == before_files
    assert all(
        (o.retained, o.intent, o.pattern_registry, o.skills,
         o.pending_questions) == owners_before[key]
        for key, o in bridge.owners.items()
    )


@pytest.mark.parametrize("failure", (
    "paper", "registry", "world_epoch", "fenced", "foreign_owner",
    "missing_schema", "native",
))
def test_r05_source_drift_stays_hold(tmp_path, monkeypatch, failure):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    if failure == "paper":
        bridge.paper._session_id = "foreign-paper"
    elif failure == "registry":
        owner = bridge.owners["A"]
        owner.pattern_registry = replace(owner.pattern_registry, revision=99)
    elif failure == "world_epoch":
        bridge.cognitive_work._states["A"].world_epoch += 1
    elif failure == "fenced":
        bridge.cognitive_work.fence_self("A")
    elif failure == "foreign_owner":
        bridge.owners["A"] = bridge.owners["B"]
    elif failure == "missing_schema":
        del bridge.cognitive_work._present_schemas["A"]
    elif failure == "native":
        bridge.owners["A"].current_worldbody_observation = replace(
            bridge.owners["A"].current_worldbody_observation,
        )
    report = audit_r05_initial_owner_context(**_args(case))
    assert not report.stage28_source_aligned
    assert not report.r1_shadow_allowed
    assert set(R1_EXTERNAL_HOLDS).issubset(report.blockers)


def test_r05_fails_if_legacy_source_claim_is_forged(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    resident = case[1].cognitive_work
    original = resident.read_present_cpu

    def forged(**kwargs):
        present = original(**kwargs)
        return replace(present, source=replace(
            present.source, native_probe_seq=present.source.native_probe_seq + 1,
        ))

    monkeypatch.setattr(resident, "read_present_cpu", forged)
    report = audit_r05_initial_owner_context(**_args(case))
    assert "LEGACY_R0_SOURCE_OR_SCHEMA_MISMATCH" in report.blockers
    assert not report.stage28_source_aligned


def test_r05_fails_if_paper_changes_between_readers(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    resident = bridge.cognitive_work
    original = resident.read_present_cpu
    calls = 0

    def drift(**kwargs):
        nonlocal calls
        readout = original(**kwargs)
        calls += 1
        if calls == 1:
            bridge.paper._session_id = "interleaved-other-session"
        return readout

    monkeypatch.setattr(resident, "read_present_cpu", drift)
    report = audit_r05_initial_owner_context(**_args(case))
    assert calls >= 1
    assert "ORIGINAL_STAGE28_SOURCE_UNQUALIFIED" in report.blockers
    assert not report.r1_shadow_allowed


def test_r05_rejoin_is_not_silently_requalified_with_initial_witness(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    with pytest.raises(TypeError):
        audit_r05_initial_owner_context(
            **_args(case), initial_receipts=("historical",),
        )
    assert "SCHEMA3_REJOIN_C_I_REGRESSION_NOT_ATTESTED" in (
        audit_r05_initial_owner_context(**_args(case)).blockers
    )


def test_r05_report_cannot_be_rewritten_as_r1_permit(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    report = audit_r05_initial_owner_context(**_args(case))
    assert report.stage28_source_aligned
    with pytest.raises(ValueError):
        replace(report, r1_shadow_allowed=True)
    with pytest.raises(ValueError):
        replace(report, blockers=())
    with pytest.raises(FrozenInstanceError):
        report.blockers = ()
    with pytest.raises(ValueError):
        R05CompatibilityAudit("A", True, 0, (), False)


def test_r05_recent_foreign_world_paper_cannot_mix_into_current(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch)
    current = read_original_owner_current(**_args(case))
    claim = LensClaim(
        ScopeRef("A", "old-world-paper-session"), Lens.SELF_WORLD,
        "prior-world-probe", EpistemicStatus.HYPOTHETICAL,
        (Provenance("cognition", "old-inference"),),
        value_ref="prior-world-subjective-hypothesis",
    )
    recent = Recent3SelfView("A", current.owner_epoch, (
        RecentCognitionEntry(
            "A", current.owner_epoch, "old-task", 0, Lens.SELF_WORLD, claim,
        ),
    ))
    with pytest.raises(R0ContextHold, match="Paper world scope"):
        CognitiveContext(current, recent=recent)
    assert not hasattr(recent, "append")


def test_r05_retrieved_need_selector_must_match_qualified_current(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    current = read_original_owner_current(**_args(case))
    # The forged query is not a source-qualified Need even if Memory SHA is
    # otherwise real. R0 does not add a new retrieval database or C3 verdict.
    forged = RetrievedMemoryBundle("A", current.owner_epoch, ("fake-need",), ())
    with pytest.raises(R0ContextHold, match="Need refs"):
        CognitiveContext(current, retrieved=forged)
    memory = Memory(
        "mem-1", "past unknown",
        Provenance("native", "outcome"), Provenance("owner", "accepted"),
    )
    case[1].owners["A"].retain_memory(memory)
    # Even an apparently well-formed digest reference cannot relabel the Need.
    forged2 = RetrievedMemoryBundle(
        "A", current.owner_epoch, ("other-need",),
        (RetrievedMemoryRef("mem-1", "0" * 64),),
    )
    with pytest.raises(R0ContextHold, match="Need refs"):
        CognitiveContext(current, retrieved=forged2)
