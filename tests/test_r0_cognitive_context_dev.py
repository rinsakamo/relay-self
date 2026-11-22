"""R0 contract adversarial controls; synthetic B bridge only (no Paper/Gemma)."""
from dataclasses import replace

import pytest

from relay_self.common_io import (
    Clock,
    ClockStamp,
    CognitionResultReceipt,
    CognitiveTask,
    CommonEnvelope,
    PreemptionEvent,
    PreemptionPhase,
    PreemptionTrace,
    Profile,
    ScopeRef,
    TaskRequirement,
    select_profile,
)
from relay_self.persistent_cognition import Memory
from relay_self.provenance import Provenance
from relay_self.r0_cognitive_context_dev import (
    CognitiveContext,
    R0ContextHold,
    Recent3SelfView,
    RecentCognitionEntry,
    RetrievedMemoryBundle,
    context_is_live,
    read_original_owner_current,
    recent_result_eligible,
    retrieve_original_owner_memory,
)
from relay_self.relay_engine import BoundedChoice
from relay_self.three_self_present import EpistemicStatus, Lens, LensClaim
from test_bd1b_owner_present_dev import _configured, _project
from test_bd1b_owner_source_dev import _files


def _args(case, sid="A"):
    _, bridge, boot, world, links, _ = case
    return dict(bridge=bridge, boot=boot, world=world, links=links, self_id=sid)


def _read(case, sid="A", signals=()):
    return read_original_owner_current(**_args(case, sid), signals=signals)


def _live(case, ctx):
    params = _args(case)
    return context_is_live(ctx, bridge=params["bridge"], boot=params["boot"],
                           world=params["world"], links=params["links"])


def _memory(case):
    bridge = case[1]
    mem = Memory("experience-1", "Earlier bounded action; situation unknown",
                 Provenance("native", "outcome"), Provenance("original-owner", "accept"))
    bridge.owners["A"].retain_memory(mem)
    return mem


def _trial(current, *, level=Profile.L1):
    scope = current.scope
    refs = current.source_revision_refs
    task = CognitiveTask(
        CommonEnvelope("r0-task", "COGNITIVE_TASK", scope,
                       ClockStamp(Clock.WORLD_TICK, current.source.native_world_time_tick),
                       Provenance("cognition", "candidate")),
        "task-r0", TaskRequirement.SELECT_FINITE if level is Profile.L1
        else TaskRequirement.OPEN_REASONING,
        refs, 200, 1,
        choices=(BoundedChoice("A", "Choose A"), BoundedChoice("B", "Choose B"))
        if level is Profile.L1 else (),
    )
    decision = select_profile(
        task, scope=scope, current_source_revision_refs=refs, now_ns=100,
        l1_available=True, l2_available=True,
    )
    result = CognitionResultReceipt(
        task.task_ref, scope, task.generation, level, refs, "SELECTED",
        Provenance("llm", "valid-generation"),
        "A" if level is Profile.L1 else None,
    )
    kw = dict(result=result, task=task, decision=decision, current=current,
              now_ns=120, compute_admitted=True,
              expected_gpu_ticket_ref="owner-ticket-1", actual_gpu_ticket_ref="owner-ticket-1")
    return kw


def test_current_is_independent_of_legacy_three_self_and_empty_context_works(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    before_files = _files(case[1])
    owners = {sid: (o.retained, o.intent, dict(o.skills), o.pattern_registry)
              for sid, o in case[1].owners.items()}
    for sid in ("A", "B"):
        current = _read(case, sid)
        assert current.scope.self_id == sid
        assert current.schema.self_id == sid
        assert current.signals == ()
        assert current.coverage is EpistemicStatus.UNKNOWN
        assert current.need_refs == current.attention_refs == ()
        assert context_is_live(
            CognitiveContext(current), bridge=case[1],
            boot=case[2], world=case[3], links=case[4],
        )
        assert CognitiveContext(current).retrieved is None
        # The existing product Present still projects 3Self and remains intact.
        assert _project(case, sid).present.three_self.scope == current.scope
    assert _files(case[1]) == before_files
    assert all((o.retained, o.intent, o.skills, o.pattern_registry) == owners[sid]
               for sid, o in case[1].owners.items())


def test_qualified_schema_need_can_enter_current_without_raw_world(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    legacy = _project(case)
    signal = legacy.exploration_need.signal
    frame = _read(case, signals=(signal,))
    assert frame.signals == (signal,)
    assert _live(case, CognitiveContext(frame))
    assert frame.coverage is EpistemicStatus.UNKNOWN
    with pytest.raises(R0ContextHold):
        replace(frame, signals=(legacy.present.three_self.self_body.claims[0],))
    with pytest.raises(R0ContextHold):
        replace(frame, signals=(signal, signal))
    with pytest.raises(R0ContextHold):
        replace(frame, need_refs=("unregistered-need",))
    assert replace(frame, need_refs=(signal.envelope.event_id,)).need_refs


@pytest.mark.parametrize("failure", [
    "foreign", "registry", "native", "paper", "world_epoch", "fence", "no_schema",
])
def test_current_rejects_foreign_stale_and_retired_source(tmp_path, monkeypatch, failure):
    case = _configured(tmp_path, monkeypatch, need=True)
    frame = _read(case)
    bridge = case[1]
    if failure == "foreign":
        # Constructor rejects foreign self before it can reach runtime use.
        with pytest.raises(R0ContextHold):
            replace(frame, scope=ScopeRef("B", frame.scope.world_session_id))
    elif failure == "registry":
        bridge.owners["A"].pattern_registry = replace(bridge.owners["A"].pattern_registry, revision=3)
    elif failure == "native":
        bridge.owners["A"].current_worldbody_observation = replace(
            bridge.owners["A"].current_worldbody_observation)
    elif failure == "paper":
        bridge.paper._session_id = "invalid"
    elif failure == "world_epoch":
        bridge.cognitive_work._states["A"].world_epoch += 1
    elif failure == "fence":
        bridge.cognitive_work.fence_self("A")
    else:
        del bridge.cognitive_work._present_schemas["A"]
    if failure != "foreign":
        assert not _live(case, CognitiveContext(frame))


def test_source_and_coverage_cannot_claim_more_than_original_schema(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    frame = _read(case, signals=(_project(case).exploration_need.signal,))
    bad = replace(frame.source, native_probe_seq=frame.source.native_probe_seq + 1)
    # Bound Schema signal is rejected at construction; unbound CURRENT is
    # rejected by the independent original-source reread at consumption.
    with pytest.raises(R0ContextHold, match="unqualified Schema signal"):
        replace(frame, source=bad)
    assert not _live(case, CognitiveContext(replace(_read(case), source=bad)))
    with pytest.raises(R0ContextHold):
        replace(frame, coverage=EpistemicStatus.OBSERVED)
    signal = frame.signals[0]
    with pytest.raises(R0ContextHold):
        replace(frame, signals=(replace(signal, registry_revision=signal.registry_revision + 1),))
    with pytest.raises(R0ContextHold):
        replace(frame, signals=(replace(signal, source_revision_refs=("old-native",)),))
    with pytest.raises(R0ContextHold):
        replace(frame, signals=(replace(signal, envelope=replace(
            signal.envelope, scope=ScopeRef("B", frame.scope.world_session_id))),))
    with pytest.raises(R0ContextHold):
        replace(frame, signals=(replace(signal, envelope=replace(signal.envelope, source_refs=())),))


def test_recent_requires_same_epoch_and_forbids_world_truth_promotion(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    current = _read(case)
    claim = LensClaim(
        current.scope, Lens.SELF_WORLD, "unresolved-target",
        EpistemicStatus.HYPOTHETICAL, (Provenance("cognition", "task-r0"),),
        value_ref="hypothesis-1",
    )
    entry = RecentCognitionEntry("A", current.owner_epoch, "task-r0", 1,
                                 Lens.SELF_WORLD, claim)
    view = Recent3SelfView("A", current.owner_epoch, (entry,))
    assert CognitiveContext(current, recent=view).recent.entries[0].claim.status is EpistemicStatus.HYPOTHETICAL
    # A partial Lens update does not automatically create a Body or MySelf lens.
    assert {e.lens for e in view.entries} == {Lens.SELF_WORLD}
    with pytest.raises(R0ContextHold):
        replace(entry, claim=replace(claim, status=EpistemicStatus.OBSERVED,
                                     source_revision_refs=current.source_revision_refs))
    with pytest.raises(R0ContextHold):
        replace(view, entries=(entry, entry))
    with pytest.raises(R0ContextHold):
        CognitiveContext(current, recent=replace(view, owner_epoch=view.owner_epoch + 1))
    with pytest.raises(R0ContextHold):
        CognitiveContext(current, recent=replace(view, self_id="B"))
    with pytest.raises(R0ContextHold):
        replace(view, entries=(replace(entry, self_id="B"),))
    # Any reJOIN/retirement invalidates future consumption of this snapshot.
    case[1].cognitive_work.fence_self("A")
    assert not _live(case, CognitiveContext(current, recent=view))


@pytest.mark.parametrize("bad", [
    "cancel", "timeout", "partial", "unresolved", "ticket", "generation",
    "foreign", "source", "compute", "deadline", "choice",
])
def test_recent_candidate_negative_controls(tmp_path, monkeypatch, bad):
    case = _configured(tmp_path, monkeypatch)
    kw = _trial(_read(case))
    assert recent_result_eligible(**kw)
    if bad == "cancel":
        kw["decision"] = replace(kw["decision"], selected=Profile.DEFER)
    elif bad == "timeout":
        kw["now_ns"] = 200
    elif bad == "partial":
        kw["result"] = replace(kw["result"], status="PARTIAL")
    elif bad == "unresolved":
        kw["result"] = replace(kw["result"], status="UNRESOLVED")
    elif bad == "ticket":
        kw["actual_gpu_ticket_ref"] = "another-ticket"
    elif bad == "generation":
        kw["result"] = replace(kw["result"], generation=0)
    elif bad == "foreign":
        kw["result"] = replace(kw["result"], scope=ScopeRef("B", kw["current"].scope.world_session_id))
    elif bad == "source":
        kw["result"] = replace(kw["result"], source_revision_refs=("old",))
    elif bad == "compute":
        kw["compute_admitted"] = False
    elif bad == "deadline":
        kw["task"] = replace(kw["task"], deadline_ns=119)
    elif bad == "choice":
        kw["result"] = replace(kw["result"], choice_id="not-an-option")
    assert not recent_result_eligible(**kw)


def test_l2_cancellation_and_delayed_generation_never_auto_append(tmp_path, monkeypatch):
    current = _read(_configured(tmp_path, monkeypatch))
    kw = _trial(current, level=Profile.L2)
    preemption = PreemptionTrace(
        current.scope, kw["task"].task_ref, kw["task"].generation, "urgent-l1",
    )
    assert recent_result_eligible(**(kw | {"preemption": preemption}))
    cancelled = replace(preemption, events=(
        PreemptionEvent(PreemptionPhase.CANCEL_REQUESTED, 125, Provenance("cpu", "cancel")),
    ))
    assert not recent_result_eligible(**(kw | {"preemption": cancelled}))
    assert not recent_result_eligible(**kw)
    assert not recent_result_eligible(**(kw | {"result": replace(kw["result"], generation=2),
                                               "preemption": preemption}))
    # This evaluator cannot create an episode, mutate Intent or retain Memory.
    assert not hasattr(current, "append_recent")
    assert not hasattr(CognitiveContext(current), "adopt_cognition_result")


def test_retrieval_refs_owner_memory_not_independent_db(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    current = _read(case)
    _memory(case)
    before = _files(case[1])
    params = _args(case)
    params.pop("self_id")
    retrieved = retrieve_original_owner_memory(
        **params, current=current, memory_ids=("experience-1",),
    )
    ctx = CognitiveContext(current, retrieved=retrieved)
    assert _live(case, ctx)
    assert retrieved.references[0].status is EpistemicStatus.REMEMBERED
    assert retrieved.references[0].applicability == "UNKNOWN"
    assert retrieved.references[0].memory_id == "experience-1"
    assert not hasattr(retrieved.references[0], "content")
    assert _files(case[1]) == before
    assert _live(case, CognitiveContext(current, retrieved=RetrievedMemoryBundle(
        "A", current.owner_epoch, (), (),
    )))
    with pytest.raises(R0ContextHold):
        retrieve_original_owner_memory(**params, current=current,
                                       memory_ids=("unadopted-c2-proposal",))
    with pytest.raises(R0ContextHold):
        retrieve_original_owner_memory(**params, current=current,
                                       memory_ids=("experience-1", "experience-1"))
    with pytest.raises(R0ContextHold):
        replace(retrieved.references[0], status=EpistemicStatus.OBSERVED)
    with pytest.raises(R0ContextHold):
        replace(retrieved.references[0], applicability="VERIFIED")
    with pytest.raises(R0ContextHold):
        CognitiveContext(current, retrieved=replace(retrieved, self_id="B"))
    with pytest.raises(R0ContextHold):
        CognitiveContext(current, retrieved=replace(retrieved,
                                                    owner_epoch=current.owner_epoch + 1))
    with pytest.raises(R0ContextHold):
        replace(retrieved, references=(retrieved.references[0], retrieved.references[0]))
    case[1].owners["A"].retained = replace(
        case[1].owners["A"].retained, memories=(replace(
            case[1].owners["A"].retained.memories[0], content="changed-memory"),),
    )
    assert not _live(case, ctx)
    # A derived index is not canonical; no index is used by this fallback.
    fresh = retrieve_original_owner_memory(**params, current=current,
                                           memory_ids=("experience-1",))
    assert fresh.references[0].revision_sha256 != retrieved.references[0].revision_sha256


def test_context_has_no_grants_and_owner_old_present_still_works(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    ctx = CognitiveContext(_read(case))
    for forbidden in ("retain_memory", "commit_intent", "complete_intent",
                      "start_skill", "issue_action", "adopt_question",
                      "checkpoint", "gpu_admit"):
        assert not hasattr(ctx, forbidden)
    before = _files(case[1])
    assert _project(case).present.three_self.self_body.claims
    assert _files(case[1]) == before
