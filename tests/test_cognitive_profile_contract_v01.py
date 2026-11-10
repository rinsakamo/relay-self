"""Offline-only #835 Task/Profile selection & non-Action negative controls."""

from dataclasses import replace

import pytest

from relay_self.cognitive_profile_contract import (
    GPUState,
    OriginKind,
    ProfileContractError,
    ProfileCostEstimate,
    ResourceReadout,
    TaskOrigin,
    bind_present_task,
    note_l1_abstention,
    route_bound_task,
)
from relay_self.common_io import (
    Clock,
    ClockStamp,
    CognitionResultReceipt,
    CommonEnvelope,
    FastCue,
    Profile,
    ScopeRef,
    TaskRequirement,
    fast_cue_eligible,
    result_is_current,
)

from relay_self.innate_schema import SchemaSnapshot
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import IdentitySpecification, PersistentCognition
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice, DecisionStatus
from relay_self.three_self_present import project_present_frame, project_three_self
SCOPE = ScopeRef("self-A", "world-A")
SOURCE = ("native-seq-71", "present-5")
NATIVE = Provenance("offline-native", "world-A:71")
OWNER = Provenance("offline-self-owner", "origin-revision-4")
COST = Provenance("offline-cost-model", "unmeasured-v1")
RESOURCE = Provenance("offline-resource-owner", "synthetic-v7")


def envelope(kind: str = "COGNITIVE_TASK", scope: ScopeRef = SCOPE) -> CommonEnvelope:
    return CommonEnvelope(
        event_id=f"{kind}-e1", kind=kind, scope=scope,
        occurred_at=ClockStamp(Clock.WORLD_TICK, 71),
        received_at=ClockStamp(Clock.HOST_MONOTONIC_NS, 100),
        provenance=OWNER, source_refs=(NATIVE,),
    )


def present():
    retained = PersistentCognition(
        IdentitySpecification("self-A", ("Remember before acting.",), OWNER)
    )
    views = project_three_self(
        retained=retained, scope=SCOPE,
        epoch_ref="epoch-5", source_revision_refs=SOURCE,
    )
    return project_present_frame(
        three_self=views, snapshot=SchemaSnapshot("self-A", 7, ()),
        current_registry_revision=7, current_source_revision_refs=SOURCE,
        frame_revision=5, active_question_refs=("question-old", "question-new"),
        active_goal_refs=("goal-survive", "goal-explore"),
        active_intent_refs=("intent-1",),
    )


def costs():
    return (
        ProfileCostEstimate(
            Profile.L0, 10, 0, 0, 0, 0, COST,
            installed_l0_rule_ref="installed-evade",
        ),
        ProfileCostEstimate(Profile.L1, 35, 5120, 150, 60, 1024, COST),
        ProfileCostEstimate(Profile.L2, 60, 7800, 300, 150, 8192, COST),
    )


def resources(
    *,
    gpu_state: GPUState = GPUState.FREE,
    revision: int = 7,
    available_vram_mib: int = 12000,
    gpu_l2_owner_task_ref: str | None = None,
):
    return ResourceReadout(
        scope=SCOPE, revision=revision, captured_at_ns=90, expires_at_ns=180,
        provenance=RESOURCE, cpu_l0_ready=True,
        installed_l0_rule_refs=frozenset({"installed-evade"}),
        l1_backend_ready=True, l2_backend_ready=True, gpu_state=gpu_state,
        available_vram_mib=available_vram_mib,
        gpu_l2_owner_task_ref=gpu_l2_owner_task_ref,
    )


def binding(
    requirement: TaskRequirement,
    *,
    kind: OriginKind = OriginKind.QUESTION,
    origin_ref: str = "question-old",
    generation: int = 1,
    choices: tuple[BoundedChoice, ...] = (),
    deadline_ns: int = 200,
):
    return bind_present_task(
        present=present(), envelope=envelope(),
        origin=TaskOrigin(kind, origin_ref, 4),
        task_ref="task-one", requirement=requirement,
        generation=generation, deadline_ns=deadline_ns, choices=choices,
    )


def route(bound, **overrides):
    args = dict(
        present=present(), scope=SCOPE,
        current_source_revision_refs=SOURCE,
        current_owner_revision=4, current_present_revision=5,
        current_registry_revision=7, current_task_generation=bound.task.generation,
        resource=resources(), current_resource_revision=7,
        estimates=costs(), now_ns=120,
    )
    args.update(overrides)
    return route_bound_task(bound, **args)


def choices():
    return (
        BoundedChoice("EAT", "Select already observed food"),
        BoundedChoice("OBSERVE", "Gather more evidence"),
    )


def test_l0_emergency_fast_cue_bypasses_present_and_gpu_without_issuing_action() -> None:
    # No Present/3Self/Memory/GPU resource argument: directly use #829's rule.
    cue = FastCue(
        envelope=envelope("FAST_CUE"),
        source_revision_ref="native-seq-71",
        installed_rule_ref="installed-evade",
        expires_at_ns=130,
    )
    assert fast_cue_eligible(
        cue, scope=SCOPE, source_revision_ref="native-seq-71",
        installed_rule_refs=frozenset({"installed-evade"}), now_ns=120,
    )
    assert not fast_cue_eligible(
        cue, scope=SCOPE, source_revision_ref="native-seq-71",
        installed_rule_refs=frozenset(), now_ns=120,
    )
    assert not fast_cue_eligible(
        cue, scope=SCOPE, source_revision_ref="native-seq-71",
        installed_rule_refs=frozenset({"installed-evade"}), now_ns=130,
    )
    assert not hasattr(cue, "issue")
    # S49 original Intent/Skill/Action authorization is untouched.


def test_l0_bound_work_and_l1_l2_no_gpu_l0_cross_route() -> None:
    l0 = binding(
        TaskRequirement.FAST_REACTION, kind=OriginKind.INTENT, origin_ref="intent-1"
    )
    assert l0.task.intent_ref == "intent-1"
    assert route(l0, resource=resources(gpu_state=GPUState.UNKNOWN)).selected is Profile.L0
    no_rule = replace(resources(), installed_l0_rule_refs=frozenset())
    assert route(l0, resource=no_rule).decision.reason == "CPU_RULE_NOT_INSTALLED_OR_READY"
    assert route(l0, resource=no_rule).selected is Profile.DEFER


def test_known_food_l1_finite_selection_requires_compute_admission() -> None:
    t = binding(
        TaskRequirement.SELECT_FINITE, kind=OriginKind.GOAL,
        origin_ref="goal-survive", choices=choices(),
    )
    assert t.task.question_ref is None and t.task.intent_ref is None
    r = route(t)
    assert r.selected is Profile.L1
    assert r.decision.resource_admission == "PENDING"
    assert r.binding.origin.ref == "goal-survive"
    receipt = CognitionResultReceipt(
        task_ref=t.task.task_ref, scope=SCOPE,
        generation=t.task.generation, profile=Profile.L1,
        source_revision_refs=SOURCE, status="SELECTED",
        provenance=OWNER, choice_id="EAT",
    )
    args = dict(scope=SCOPE, current_source_revision_refs=SOURCE, now_ns=150)
    assert not result_is_current(
        receipt, t.task, r.decision, compute_admitted=False, **args
    )
    assert result_is_current(
        receipt, t.task, r.decision, compute_admitted=True, **args
    )
    assert not result_is_current(
        replace(receipt, choice_id="invented"), t.task,
        r.decision, compute_admitted=True, **args
    )


def test_l1_can_abstain_and_does_not_auto_escalate_to_l2_or_edit_intent() -> None:
    t = binding(TaskRequirement.SELECT_FINITE, choices=choices())
    selected = route(t)
    owner = IntentCommitment()
    owner.commit("intent-1", objective="stay alive", at_ns=1, provenance=OWNER)
    before = owner.events
    report = note_l1_abstention(
        selected, reason="INSUFFICIENT_EVIDENCE", provenance=OWNER
    )
    assert report.status is DecisionStatus.UNRESOLVED
    assert report.task_ref == "task-one"
    assert not hasattr(report, "choice_id")
    assert not hasattr(report, "action_id")
    assert owner.events == before
    assert route(
        t, resource=replace(resources(), l1_backend_ready=False)
    ).selected is Profile.DEFER  # L2 provider ready is not a fallback.
    with pytest.raises(ProfileContractError, match="L1 abstention"):
        note_l1_abstention(
            route(binding(TaskRequirement.OPEN_REASONING)),
            reason="no", provenance=OWNER,
        )


def test_l2_open_question_same_owner_no_automatic_action_or_memory() -> None:
    t = binding(TaskRequirement.OPEN_REASONING, kind=OriginKind.QUESTION)
    r = route(t)
    assert r.selected is Profile.L2
    assert r.binding.origin.ref == "question-old"
    assert t.task.question_ref == "question-old"
    assert t.task.choices == ()
    assert r.decision.resource_admission == "PENDING"
    assert present().active_goal_refs == ("goal-survive", "goal-explore")


def test_l1_conflict_with_l2_emits_hint_not_resource_grant() -> None:
    t = binding(TaskRequirement.SELECT_FINITE, choices=choices())
    occupied = resources(
        gpu_state=GPUState.BUSY_L2, gpu_l2_owner_task_ref="task-l2", available_vram_mib=0,
    )
    r = route(t, resource=occupied)
    assert r.selected is Profile.DEFER
    assert r.decision.reason == "L2_PREEMPTION_REQUIRED"
    assert r.preemption_target_task_ref == "task-l2"
    assert r.decision.resource_admission == "NOT_REQUESTED"
    # #828/05 still must stop backend, fence outputs and verify GPU release.
    next_snapshot = resources(revision=8)
    later = route(
        t, resource=next_snapshot, current_resource_revision=8,
    )
    assert later.selected is Profile.L1
    assert later.decision.resource_admission == "PENDING"
    assert later.preemption_target_task_ref is None


@pytest.mark.parametrize("override,reason", [
    ({"scope": ScopeRef("self-B", "world-A")}, "FOREIGN_SCOPE"),
    ({"current_source_revision_refs": ("native-seq-72",)}, "STALE_SOURCE"),
    ({"current_owner_revision": 5}, "STALE_OWNER"),
    ({"current_present_revision": 6}, "STALE_PRESENT"),
    ({"current_registry_revision": 8}, "STALE_SCHEMA_REGISTRY"),
    ({"current_task_generation": 2}, "STALE_GENERATION"),
    ({"now_ns": 200}, "DEADLINE_EXPIRED"),
    ({"current_resource_revision": 8}, "STALE_RESOURCE"),
    ({"resource": resources(gpu_state=GPUState.UNKNOWN)}, "GPU_UNKNOWN"),
    ({"resource": resources(gpu_state=GPUState.BUSY_OTHER)}, "GPU_BUSY"),
    ({"resource": resources(available_vram_mib=3000)}, "VRAM_INSUFFICIENT"),
    ({"resource": replace(resources(), l1_backend_ready=False)}, "BACKEND_UNAVAILABLE"),
    ({"now_ns": 185}, "STALE_RESOURCE"),
])
def test_l1_routing_fails_closed_for_wrong_owner_budget_source_and_capacity(
    override, reason,
) -> None:
    t = binding(TaskRequirement.SELECT_FINITE, choices=choices())
    r = route(t, **override)
    assert r.selected is Profile.DEFER
    assert r.decision.reason == reason
    assert r.decision.resource_admission == "NOT_REQUESTED"


def test_l2_context_and_runtime_budget_are_not_ignored() -> None:
    t = binding(TaskRequirement.OPEN_REASONING)
    overflow = replace(
        costs()[2], prompt_tokens=8000, output_tokens=400, context_limit_tokens=8192,
    )
    assert route(t, estimates=(overflow,)).decision.reason == "CONTEXT_OVERFLOW"
    short = replace(costs()[2], estimated_duration_ns=80)
    assert route(t, estimates=(short,)).decision.reason == "INSUFFICIENT_SLACK"
    assert route(t, estimates=()).decision.reason == "NO_COST_ESTIMATE"
    with pytest.raises(ProfileContractError, match="duplicate profile estimate"):
        route(t, estimates=(costs()[2], costs()[2]))


def test_question_and_goal_refs_survive_deferral_and_new_generation() -> None:
    one = binding(TaskRequirement.OPEN_REASONING, generation=1)
    blocked = route(
        one, resource=resources(gpu_state=GPUState.UNKNOWN),
    )
    assert blocked.selected is Profile.DEFER
    assert blocked.binding.task.question_ref == "question-old"
    assert present().active_goal_refs == ("goal-survive", "goal-explore")
    two = binding(TaskRequirement.OPEN_REASONING, generation=2)
    assert route(one, current_task_generation=2).decision.reason == "STALE_GENERATION"
    assert route(two, current_task_generation=2).selected is Profile.L2
    assert two.task.question_ref == one.task.question_ref
    assert two.origin.owner_revision == one.origin.owner_revision


def test_invalid_or_unowned_task_cannot_be_forged_from_present() -> None:
    with pytest.raises(ProfileContractError, match="not active"):
        binding(
            TaskRequirement.OPEN_REASONING, kind=OriginKind.QUESTION,
            origin_ref="not-adopted",
        )
    with pytest.raises(ProfileContractError, match="foreign scope"):
        bind_present_task(
            present=present(), envelope=envelope(scope=ScopeRef("self-A", "world-B")),
            origin=TaskOrigin(OriginKind.QUESTION, "question-old", 4),
            task_ref="forged-task", requirement=TaskRequirement.OPEN_REASONING,
            generation=1, deadline_ns=200,
        )
    with pytest.raises(ProfileContractError, match="deadline"):
        binding(TaskRequirement.OPEN_REASONING, deadline_ns=100)
    with pytest.raises(ValueError, match="at least two"):
        binding(
            TaskRequirement.SELECT_FINITE,
            choices=(BoundedChoice("ONLY", "one"),),
        )


def test_invalid_resource_or_cost_estimate_cannot_be_authority() -> None:
    with pytest.raises(ProfileContractError, match="L0 must use"):
        replace(costs()[0], required_vram_mib=1)
    with pytest.raises(ProfileContractError, match="positive GPU"):
        replace(costs()[1], required_vram_mib=0)
    with pytest.raises(ProfileContractError, match="expiry"):
        replace(resources(), expires_at_ns=90)
    with pytest.raises(ProfileContractError, match="gpu_l2_owner_task_ref"):
        replace(resources(), gpu_state=GPUState.BUSY_L2)
    with pytest.raises(ProfileContractError, match="non-L2-busy"):
        replace(resources(), gpu_l2_owner_task_ref="stale-l2")
    with pytest.raises(ProfileContractError, match="must be bool"):
        replace(resources(), l1_backend_ready="yes")


def test_untrusted_resource_snapshot_does_not_mutate_real_intent_owner() -> None:
    owner = IntentCommitment()
    owner.commit("intent-1", objective="survive", at_ns=1, provenance=OWNER)
    events_before = owner.events
    t = binding(TaskRequirement.OPEN_REASONING, kind=OriginKind.GOAL,
                origin_ref="goal-explore")
    assert route(t).selected is Profile.L2
    assert owner.events == events_before
    assert owner.current_intent.intent_id == "intent-1"
