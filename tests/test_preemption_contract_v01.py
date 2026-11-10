"""#837 offline-only L2 preemption owner-facing protocol controls.

No native backend calls, GPU access, LLM, real World, Action, or owner grant.
"""

from dataclasses import replace

import pytest

from relay_self.cognitive_profile_contract import (
    BoundCognitiveTask,
    GPUState,
    OriginKind,
    ProfileRoute,
    TaskOrigin,
)
from relay_self.common_io import (
    Clock,
    ClockStamp,
    CognitionResultReceipt,
    CognitiveTask,
    CommonEnvelope,
    CommonIOError,
    FastCue,
    PreemptionPhase,
    PreemptionTrace,
    Profile,
    ProfileDecision,
    ScopeRef,
    TaskRequirement,
    fast_cue_eligible,
    result_is_current,
    select_profile,
)
from relay_self.intent import IntentCommitment
from relay_self.preemption_contract import (
    BackendStopReceipt,
    L1ComputeGrantReceipt,
    L2ComputeLease,
    OutputFenceReceipt,
    PendingReason,
    PreemptionContractError,
    ResourceReleaseReceipt,
    confirm_backend_stopped,
    confirm_l1_compute_grant,
    confirm_output_fence,
    confirm_resource_released,
    l2_result_is_admissible,
    note_preemption_pending,
    request_l2_preemption,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice

SCOPE = ScopeRef("self-A", "world-A")
INTERNAL = Provenance("offline-owner-fixture", "owner-epoch-7")
NATIVE = Provenance("offline-native-fixture", "world-A:seq-41")
BACKEND = Provenance("offline-backend-witness", "backend-request-91")
GPU = Provenance("offline-gpu-owner", "gpu-revision-8")
SOURCE = ("native-seq-41", "present-3")
OWNER_EPOCH = "resource-owner-epoch-7"


def envelope(name: str = "COGNITIVE_TASK", *, scope: ScopeRef = SCOPE) -> CommonEnvelope:
    return CommonEnvelope(
        event_id=f"{name}-evt-3", kind=name, scope=scope,
        occurred_at=ClockStamp(Clock.WORLD_TICK, 41),
        received_at=ClockStamp(Clock.HOST_MONOTONIC_NS, 80),
        provenance=INTERNAL, source_refs=(NATIVE,),
    )


def l1_task() -> CognitiveTask:
    return CognitiveTask(
        envelope=envelope(), task_ref="l1-work",
        requirement=TaskRequirement.SELECT_FINITE,
        source_revision_refs=SOURCE, deadline_ns=190, generation=2,
        question_ref="question-food",
        choices=(BoundedChoice("EAT", "eat known food"),
                 BoundedChoice("INSPECT", "inspect unknown content")),
    )


def l2_task() -> CognitiveTask:
    return CognitiveTask(
        envelope=envelope(), task_ref="l2-work",
        requirement=TaskRequirement.OPEN_REASONING,
        source_revision_refs=SOURCE, deadline_ns=180, generation=4,
        question_ref="question-why",
    )


def l1_route(*, selected: Profile = Profile.DEFER, resource_revision: int = 7):
    task = l1_task()
    binding = BoundCognitiveTask(
        task=task,
        origin=TaskOrigin(OriginKind.QUESTION, "question-food", 3),
        present_revision=3, schema_registry_revision=6,
    )
    decision = ProfileDecision(
        task_ref=task.task_ref, generation=task.generation,
        selected=selected,
        reason="L2_PREEMPTION_REQUIRED" if selected is Profile.DEFER else "FINITE_CHOICES",
        source_revision_refs=SOURCE,
        resource_admission="NOT_REQUESTED" if selected is Profile.DEFER else "PENDING",
    )
    return ProfileRoute(
        binding=binding, decision=decision,
        resource_revision=resource_revision,
        cost_provenance=INTERNAL,
        preemption_target_task_ref="l2-work" if selected is Profile.DEFER else None,
    )


def lease(*, scope: ScopeRef = SCOPE):
    return L2ComputeLease(
        scope=scope, task_ref="l2-work", generation=4,
        lease_ref="lease-l2-91", backend_instance_ref="backend-a",
        gpu_ref="gpu-0", resource_owner_ref="compute-owner",
        resource_revision=7, granted_at_ns=91, provenance=GPU,
    )


def request(*, route=None, l2_lease=None, now_ns: int = 100, **kwargs):
    options = dict(
        route=l1_route() if route is None else route,
        l2_lease=lease() if l2_lease is None else l2_lease,
        owner_epoch_ref=OWNER_EPOCH,
        result_owner_ref="result-admission-owner",
        current_l1_generation=2, current_l2_generation=4,
        current_l1_source_revision_refs=SOURCE,
        current_resource_revision=7,
        l1_required_vram_mib=5120,
        now_ns=now_ns, provenance=INTERNAL,
    )
    options.update(kwargs)
    return request_l2_preemption(**options)


def fence(**kwargs):
    options = dict(
        lease_ref="lease-l2-91", task_ref="l2-work", generation=4,
        result_owner_ref="result-admission-owner",
        at_ns=101, verification_ref="output-fence-verified-1",
        provenance=INTERNAL, rejected_generation=True,
    )
    options.update(kwargs)
    return OutputFenceReceipt(**options)


def stop(**kwargs):
    options = dict(
        lease_ref="lease-l2-91", task_ref="l2-work", generation=4,
        backend_instance_ref="backend-a", at_ns=102,
        verification_ref="backend-terminated-1", provenance=BACKEND,
        stopped_confirmed=True, active_request_count=0,
    )
    options.update(kwargs)
    return BackendStopReceipt(**options)


def released(**kwargs):
    options = dict(
        scope=SCOPE, released_lease_ref="lease-l2-91",
        gpu_ref="gpu-0", resource_owner_ref="compute-owner",
        resource_revision=8, at_ns=103, expires_at_ns=155,
        verification_ref="gpu-observation-8", provenance=GPU,
        gpu_state=GPUState.FREE, released_lease_active=False,
        available_vram_mib=7000,
    )
    options.update(kwargs)
    return ResourceReleaseReceipt(**options)


def grant(**kwargs):
    options = dict(
        scope=SCOPE, task_ref="l1-work", generation=2,
        new_lease_ref="lease-l1-92", resource_owner_ref="compute-owner",
        resource_revision=8, at_ns=104, verification_ref="l1-owner-grant-92",
        provenance=GPU, grant_confirmed=True,
    )
    options.update(kwargs)
    return L1ComputeGrantReceipt(**options)


def phases(review):
    return tuple(event.phase for event in review.trace.events)


def fenced():
    return confirm_output_fence(request(), fence(), current_owner_epoch_ref=OWNER_EPOCH)


def stopped():
    return confirm_backend_stopped(
        fenced(), stop(), current_owner_epoch_ref=OWNER_EPOCH,
    )


def gpu_released():
    return confirm_resource_released(
        stopped(), released(), current_owner_epoch_ref=OWNER_EPOCH, now_ns=106,
    )


def admitted():
    return confirm_l1_compute_grant(
        gpu_released(), grant=grant(), fresh_l1_route=l1_route(
            selected=Profile.L1, resource_revision=8,
        ), current_owner_epoch_ref=OWNER_EPOCH,
        current_l1_generation=2, current_l1_source_revision_refs=SOURCE,
        now_ns=110,
    )


def test_preemption_full_five_step_protocol_no_physical_issuer() -> None:
    x = request()
    assert x.l2_fenced
    assert not x.l1_admitted
    assert phases(x) == (PreemptionPhase.CANCEL_REQUESTED,)
    x = confirm_output_fence(x, fence(), current_owner_epoch_ref=OWNER_EPOCH)
    assert phases(x)[-1] is PreemptionPhase.OUTPUT_FENCED
    x = confirm_backend_stopped(x, stop(), current_owner_epoch_ref=OWNER_EPOCH)
    assert phases(x)[-1] is PreemptionPhase.BACKEND_STOPPED
    x = confirm_resource_released(
        x, released(), current_owner_epoch_ref=OWNER_EPOCH, now_ns=105,
    )
    assert phases(x)[-1] is PreemptionPhase.RESOURCE_RELEASED
    assert x.grant is None and not x.l1_admitted
    x = confirm_l1_compute_grant(
        x, grant=grant(), fresh_l1_route=l1_route(
            selected=Profile.L1, resource_revision=8,
        ), current_owner_epoch_ref=OWNER_EPOCH,
        current_l1_generation=2, current_l1_source_revision_refs=SOURCE,
        now_ns=110,
    )
    assert x.l1_admitted and len(x.trace.events) == 5
    assert phases(x)[-1] is PreemptionPhase.L1_ADMITTED
    assert x.grant.new_lease_ref != x.l2_lease.lease_ref
    assert not hasattr(x, "issue_action")
    assert not hasattr(x, "cancel_backend")


def test_cancel_request_fences_old_l2_result_before_stop_ack() -> None:
    task = l2_task()
    decision = select_profile(
        task, scope=SCOPE, current_source_revision_refs=SOURCE,
        now_ns=99, l2_available=True,
    )
    assert decision.selected is Profile.L2
    result = CognitionResultReceipt(
        task_ref="l2-work", scope=SCOPE, generation=4, profile=Profile.L2,
        source_revision_refs=SOURCE, status="SELECTED", provenance=INTERNAL,
    )
    empty = PreemptionTrace(SCOPE, "l2-work", 4, "l1-work")
    assert result_is_current(
        result, task, decision, scope=SCOPE,
        current_source_revision_refs=SOURCE, now_ns=99,
        compute_admitted=True, preemption=empty,
    )
    x = request()
    assert x.trace.output_fenced
    assert not l2_result_is_admissible(
        x, result=result, l2_task=task, l2_decision=decision,
        current_source_revision_refs=SOURCE, now_ns=100,
        compute_admitted=True,
    )
    assert not l2_result_is_admissible(
        admitted(), result=result, l2_task=task, l2_decision=decision,
        current_source_revision_refs=SOURCE, now_ns=110,
        compute_admitted=True,
    )
    assert not l2_result_is_admissible(
        x, result=replace(result, generation=5), l2_task=task,
        l2_decision=decision, current_source_revision_refs=SOURCE,
        now_ns=100, compute_admitted=True,
    )


@pytest.mark.parametrize("change,match", [
    ({"current_l2_generation": 5}, "stale task generation"),
    ({"current_l1_generation": 3}, "stale task generation"),
    ({"current_l1_source_revision_refs": ("old",)}, "stale L1 source"),
    ({"current_resource_revision": 8}, "resource revision mismatch"),
    ({"now_ns": 200}, "deadline"),
    ({"l1_required_vram_mib": 0}, "positive"),
])
def test_preemption_request_rejects_stale_generation_epoch_or_budget(
    change, match,
) -> None:
    with pytest.raises(PreemptionContractError, match=match):
        request(**change)


def test_preemption_request_requires_qualified_l1_waiting_on_exact_l2() -> None:
    with pytest.raises(PreemptionContractError, match="not qualified"):
        request(route=l1_route(selected=Profile.L1))
    with pytest.raises(PreemptionContractError, match="foreign"):
        request(l2_lease=lease(scope=ScopeRef("self-A", "world-B")))
    with pytest.raises(PreemptionContractError, match="resource revision"):
        request(l2_lease=replace(lease(), resource_revision=6))
    wrong = replace(l1_route(), preemption_target_task_ref="different-l2")
    with pytest.raises(PreemptionContractError, match="not qualified"):
        request(route=wrong)


@pytest.mark.parametrize("tamper", [
    {"lease_ref": "wrong"},
    {"generation": 99},
    {"result_owner_ref": "foreign-owner"},
    {"rejected_generation": False},
])
def test_fence_receipt_must_match_and_prove_generation_rejection(tamper) -> None:
    with pytest.raises(PreemptionContractError, match="fence receipt"):
        confirm_output_fence(
            request(), fence(**tamper), current_owner_epoch_ref=OWNER_EPOCH,
        )


@pytest.mark.parametrize("tamper", [
    {"lease_ref": "wrong-l2-lease"},
    {"task_ref": "another-task"},
    {"generation": 5},
    {"backend_instance_ref": "backend-b"},
    {"stopped_confirmed": False},
    {"active_request_count": 1},
    {"stopped_confirmed": False, "transport_cancelled": True},
])
def test_backend_stop_rejects_foreign_or_http_only_cancellation(tamper) -> None:
    with pytest.raises(PreemptionContractError, match="backend stop not verified"):
        confirm_backend_stopped(
            fenced(), stop(**tamper), current_owner_epoch_ref=OWNER_EPOCH,
        )


def test_backend_must_stop_after_fence_and_clock_must_be_monotonic() -> None:
    with pytest.raises(CommonIOError, match="out-of-order"):
        confirm_backend_stopped(
            request(), stop(), current_owner_epoch_ref=OWNER_EPOCH,
        )
    with pytest.raises(CommonIOError, match="regressed"):
        confirm_backend_stopped(
            fenced(), stop(at_ns=100), current_owner_epoch_ref=OWNER_EPOCH,
        )
    with pytest.raises(PreemptionContractError, match="resource owner epoch"):
        confirm_backend_stopped(
            fenced(), stop(), current_owner_epoch_ref="restarted-epoch",
        )


@pytest.mark.parametrize("tamper", [
    {"scope": ScopeRef("self-B", "world-A")},
    {"scope": ScopeRef("self-A", "world-B")},
    {"released_lease_ref": "foreign-lease"},
    {"gpu_ref": "gpu-1"},
    {"resource_owner_ref": "another-owner"},
    {"resource_revision": 7},
    {"gpu_state": GPUState.UNKNOWN},
    {"gpu_state": GPUState.BUSY_OTHER},
    {"released_lease_active": True},
    {"available_vram_mib": 3000},
])
def test_resource_release_rejects_unavailable_unverified_old_or_foreign(tamper) -> None:
    with pytest.raises(PreemptionContractError, match="GPU release"):
        confirm_resource_released(
            stopped(), released(**tamper),
            current_owner_epoch_ref=OWNER_EPOCH, now_ns=106,
        )


def test_release_requires_stop_is_time_bounded_and_cannot_be_replayed() -> None:
    with pytest.raises(PreemptionContractError, match="stop must precede"):
        confirm_resource_released(
            fenced(), released(), current_owner_epoch_ref=OWNER_EPOCH,
            now_ns=106,
        )
    with pytest.raises(PreemptionContractError, match="GPU release"):
        confirm_resource_released(
            stopped(), released(), current_owner_epoch_ref=OWNER_EPOCH,
            now_ns=155,
        )
    with pytest.raises(CommonIOError, match="regressed"):
        confirm_resource_released(
            stopped(), released(at_ns=101),
            current_owner_epoch_ref=OWNER_EPOCH, now_ns=106,
        )
    with pytest.raises(CommonIOError, match="out-of-order"):
        confirm_resource_released(
            gpu_released(), released(), current_owner_epoch_ref=OWNER_EPOCH,
            now_ns=106,
        )


def test_released_gpu_without_new_owner_grant_does_not_admit_l1() -> None:
    x = gpu_released()
    assert x.trace.events[-1].phase is PreemptionPhase.RESOURCE_RELEASED
    assert x.release.available_vram_mib == 7000
    assert x.grant is None and not x.l1_admitted


@pytest.mark.parametrize("tamper", [
    {"scope": ScopeRef("self-B", "world-A")},
    {"task_ref": "stale-l1"},
    {"generation": 99},
    {"new_lease_ref": "lease-l2-91"},
    {"resource_owner_ref": "foreign-owner"},
    {"resource_revision": 7},
    {"grant_confirmed": False},
])
def test_l1_grant_rejects_fake_or_stale_owner_lease(tamper) -> None:
    with pytest.raises(PreemptionContractError, match="grant not verified"):
        confirm_l1_compute_grant(
            gpu_released(), grant=grant(**tamper),
            fresh_l1_route=l1_route(selected=Profile.L1, resource_revision=8),
            current_owner_epoch_ref=OWNER_EPOCH,
            current_l1_generation=2, current_l1_source_revision_refs=SOURCE,
            now_ns=110,
        )


def test_l1_grant_requires_fresh_profile_route_source_owner_and_deadline() -> None:
    x = gpu_released()
    def check(route, **params):
        options = dict(
            grant=grant(), fresh_l1_route=route,
            current_owner_epoch_ref=OWNER_EPOCH,
            current_l1_generation=2, current_l1_source_revision_refs=SOURCE,
            now_ns=110,
        )
        options.update(params)
        return confirm_l1_compute_grant(x, **options)

    with pytest.raises(PreemptionContractError, match="fresh route"):
        check(l1_route())
    with pytest.raises(PreemptionContractError, match="fresh route"):
        check(l1_route(selected=Profile.L1, resource_revision=7))
    with pytest.raises(PreemptionContractError, match="fresh route"):
        check(l1_route(selected=Profile.L1, resource_revision=8),
              current_l1_generation=3)
    with pytest.raises(PreemptionContractError, match="fresh route"):
        check(l1_route(selected=Profile.L1, resource_revision=8),
              current_l1_source_revision_refs=("old-source",))
    with pytest.raises(PreemptionContractError, match="fresh route"):
        check(l1_route(selected=Profile.L1, resource_revision=8), now_ns=190)
    with pytest.raises(PreemptionContractError, match="fresh route"):
        check(l1_route(selected=Profile.L1, resource_revision=8), now_ns=155)
    with pytest.raises(PreemptionContractError, match="resource owner epoch"):
        check(l1_route(selected=Profile.L1, resource_revision=8),
              current_owner_epoch_ref="new-owner-epoch")
    with pytest.raises(PreemptionContractError, match="grant not verified"):
        check(l1_route(selected=Profile.L1, resource_revision=8),
              grant=grant(at_ns=130))


def test_duplicate_or_skipped_grant_cannot_advance_twice() -> None:
    with pytest.raises(PreemptionContractError, match="fence, stop and GPU release"):
        confirm_l1_compute_grant(
            stopped(), grant=grant(),
            fresh_l1_route=l1_route(selected=Profile.L1, resource_revision=8),
            current_owner_epoch_ref=OWNER_EPOCH,
            current_l1_generation=2, current_l1_source_revision_refs=SOURCE,
            now_ns=110,
        )
    with pytest.raises(CommonIOError, match="already terminal"):
        confirm_l1_compute_grant(
            admitted(), grant=grant(),
            fresh_l1_route=l1_route(selected=Profile.L1, resource_revision=8),
            current_owner_epoch_ref=OWNER_EPOCH,
            current_l1_generation=2, current_l1_source_revision_refs=SOURCE,
            now_ns=110,
        )


def test_failure_note_does_not_force_release_or_revive_l2() -> None:
    x = request()
    pending = note_preemption_pending(
        x, reason=PendingReason.STOP_TIMEOUT, now_ns=105, provenance=INTERNAL,
    )
    assert pending.pending[-1].reason is PendingReason.STOP_TIMEOUT
    assert pending.l2_fenced and not pending.l1_admitted
    assert pending.trace.events == x.trace.events
    with pytest.raises(PreemptionContractError, match="regressed"):
        note_preemption_pending(
            pending, reason=PendingReason.OWNER_UNAVAILABLE,
            now_ns=104, provenance=INTERNAL,
        )
    with pytest.raises(PreemptionContractError, match="after L1 admission"):
        note_preemption_pending(
            admitted(), reason=PendingReason.STOP_TIMEOUT,
            now_ns=120, provenance=INTERNAL,
        )


def test_l0_independent_and_question_and_intent_preserved() -> None:
    cpu_cue = FastCue(
        envelope=envelope("FAST_CUE"), source_revision_ref="native-seq-41",
        installed_rule_ref="installed-cpu-reaction", expires_at_ns=165,
    )
    assert fast_cue_eligible(
        cpu_cue, scope=SCOPE, source_revision_ref="native-seq-41",
        installed_rule_refs=frozenset({"installed-cpu-reaction"}), now_ns=110,
    )
    owner = IntentCommitment()
    owner.commit("intent-survival", objective="remain active", at_ns=1,
                 provenance=INTERNAL)
    prior = owner.events
    review = note_preemption_pending(
        request(), reason=PendingReason.RELEASE_UNVERIFIED,
        now_ns=106, provenance=INTERNAL,
    )
    assert review.waiting_l1_route.binding.task.question_ref == "question-food"
    assert owner.events == prior
    assert owner.current_intent.intent_id == "intent-survival"
    assert not hasattr(review, "memory_revision")
    assert not hasattr(review, "issue_action")
