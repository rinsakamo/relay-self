"""Deterministic, offline-only I/O #829 scenarios; no World or model calls."""

from dataclasses import replace

import pytest

from relay_self.action import ActionLifecycle, ActionState, InvalidTransition
from relay_self.common_io import (
    Clock,
    ClockStamp,
    CognitiveTask,
    CognitionResultReceipt,
    CommonEnvelope,
    CommonIOError,
    FastCue,
    PreemptionEvent,
    PreemptionPhase,
    PreemptionTrace,
    Profile,
    ScopeRef,
    TaskRequirement,
    fast_cue_eligible,
    result_is_current,
    select_profile,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import IdentitySpecification, Memory, PersistentCognition
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice, OpenCognitionResult
from relay_self.skill import SkillExecution


SCOPE = ScopeRef("self-A", "world-A")
NATIVE = Provenance("native", "seq-41")
INTERNAL = Provenance("offline-cognition", "epoch-4")
CURRENT = ("native-seq-41", "frame-4")


def envelope(kind: str, scope: ScopeRef = SCOPE) -> CommonEnvelope:
    return CommonEnvelope(
        event_id=f"{kind}-evt-4",
        kind=kind,
        scope=scope,
        occurred_at=ClockStamp(Clock.WORLD_TICK, 41),
        received_at=ClockStamp(Clock.HOST_MONOTONIC_NS, 100),
        provenance=INTERNAL,
        source_refs=(NATIVE,),
        cause_event_refs=("earlier-event",),
    )


def task(
    requirement: TaskRequirement,
    *,
    choices: tuple[BoundedChoice, ...] = (),
    deadline_ns: int = 200,
    generation: int = 1,
) -> CognitiveTask:
    return CognitiveTask(
        envelope=envelope("COGNITIVE_TASK"),
        task_ref="task-1",
        requirement=requirement,
        source_revision_refs=CURRENT,
        deadline_ns=deadline_ns,
        generation=generation,
        choices=choices,
        question_ref="question-1",
    )


def receipt(t: CognitiveTask, profile: Profile, choice_id: str | None = None):
    return CognitionResultReceipt(
        task_ref=t.task_ref,
        scope=t.envelope.scope,
        generation=t.generation,
        profile=profile,
        source_revision_refs=t.source_revision_refs,
        status="SELECTED",
        provenance=Provenance("provider", "generation-1"),
        choice_id=choice_id,
    )


def decision(t: CognitiveTask, **kwargs):
    return select_profile(
        t,
        scope=SCOPE,
        current_source_revision_refs=CURRENT,
        now_ns=120,
        **kwargs,
    )


def preemption(t: CognitiveTask) -> PreemptionTrace:
    return PreemptionTrace(
        scope=SCOPE, l2_task_ref=t.task_ref, l2_generation=t.generation,
        l1_task_ref="urgent-l1",
    )


def test_scenario_1_fast_cpu_cue_still_requires_original_action_authorization() -> None:
    cue = FastCue(
        envelope=envelope("FAST_CUE"),
        source_revision_ref="native-seq-41",
        installed_rule_ref="known-evade-rule",
        expires_at_ns=140,
    )
    assert fast_cue_eligible(
        cue, scope=SCOPE, source_revision_ref="native-seq-41",
        installed_rule_refs=frozenset({"known-evade-rule"}), now_ns=110,
    )
    t = task(TaskRequirement.FAST_REACTION, deadline_ns=140)
    assert decision(t, l0_rule_ready=True).selected is Profile.L0

    # The common I/O helper does NOT emit actions. This existing lifecycle
    # still requires original Intent -> Skill -> PROPOSED -> AUTHORIZED -> ISSUED.
    intent = IntentCommitment()
    intent.commit("evade-intent", objective="avoid observed danger", at_ns=1, provenance=INTERNAL)
    skill = SkillExecution.start(
        "evade-skill-exec", skill_id="evade", intent_commitment=intent,
        at_ns=2, provenance=INTERNAL,
    )
    proposed = ActionLifecycle.propose(
        "evade-action", skill_execution=skill, intent_commitment=intent,
        at_ns=3, provenance=INTERNAL,
    )
    with pytest.raises(InvalidTransition):
        proposed.issue(at_ns=5, deadline_ns=50, provenance=INTERNAL)
    issued = proposed.authorize(
        at_ns=4, provenance=INTERNAL, authority="existing-action-policy"
    ).issue(at_ns=5, deadline_ns=50, provenance=INTERNAL)
    assert issued.state is ActionState.ISSUED
    assert issued.mark_unknown(at_ns=6, provenance=NATIVE).state is ActionState.UNKNOWN


def test_scenario_1_expired_foreign_or_uninstalled_cues_rejected() -> None:
    cue = FastCue(envelope("FAST_CUE"), "rev-1", "cpu-rule", 120)
    args = dict(scope=SCOPE, source_revision_ref="rev-1",
                installed_rule_refs=frozenset({"cpu-rule"}), now_ns=110)
    assert fast_cue_eligible(cue, **args)
    assert not fast_cue_eligible(cue, **(args | {"now_ns": 120}))
    assert not fast_cue_eligible(cue, **(args | {"scope": ScopeRef("self-B", "world-A")}))
    assert not fast_cue_eligible(cue, **(args | {"source_revision_ref": "rev-2"}))
    assert not fast_cue_eligible(cue, **(args | {"installed_rule_refs": frozenset()}))
    with pytest.raises(CommonIOError, match="native source"):
        FastCue(replace(envelope("FAST_CUE"), source_refs=()), "rev-1", "cpu-rule", 120)


def test_scenario_2_known_food_l1_requires_bounded_choices_and_admitted_compute() -> None:
    remembered = Memory(
        memory_id="food-v3",
        content="Earlier food acquisition; applicability must be checked.",
        source_provenance=NATIVE,
        integration_provenance=INTERNAL,
    )
    assert remembered.source_provenance is NATIVE
    choices = (BoundedChoice("EAT", "Eat held food"), BoundedChoice("SEARCH", "Seek food"))
    t = task(TaskRequirement.SELECT_FINITE, choices=choices)
    d = decision(t, l1_available=True)
    assert d.selected is Profile.L1 and d.resource_admission == "PENDING"
    r = receipt(t, Profile.L1, choice_id="EAT")
    args = dict(scope=SCOPE, current_source_revision_refs=CURRENT, now_ns=130)
    assert result_is_current(r, t, d, compute_admitted=True, **args)
    assert not result_is_current(r, t, d, compute_admitted=False, **args)
    assert not result_is_current(
        replace(r, choice_id="INVENTED_FOOD"), t, d, compute_admitted=True, **args
    )
    assert not result_is_current(
        r, t, d, compute_admitted=True,
        **(args | {"current_source_revision_refs": ("old-native", "frame-4")}),
    )


def test_scenario_3_l2_exploration_is_question_preserving_but_not_auto_learning() -> None:
    identity = IdentitySpecification(
        self_id="self-A", directives=("Observe before learning.",), provenance=INTERNAL
    )
    cognition = PersistentCognition(identity=identity)
    t = task(TaskRequirement.OPEN_REASONING)
    assert t.question_ref == "question-1" and t.intent_ref is None
    d = decision(t, l2_available=True)
    assert d.selected is Profile.L2
    expression = OpenCognitionResult(
        request_id=t.task_ref, text="Hypothesis: investigate a new reference action.",
        provenance=INTERNAL,
    )
    assert expression.text.startswith("Hypothesis:")
    r = receipt(t, Profile.L2)
    active = preemption(t)
    assert result_is_current(
        r, t, d, scope=SCOPE, current_source_revision_refs=CURRENT,
        now_ns=130, compute_admitted=True, preemption=active,
    )
    assert not result_is_current(
        r, t, d, scope=SCOPE, current_source_revision_refs=CURRENT,
        now_ns=130, compute_admitted=True, preemption=None,
    )
    # Model text and simulated receipt do not create an Intent, World outcome,
    # retained Memory, qualified C1 experience or accepted C2 revision.
    assert cognition.memories == ()


def test_scenario_4_l1_preemption_fences_late_l2_and_requires_real_release_receipts() -> None:
    t = task(TaskRequirement.OPEN_REASONING)
    d = decision(t, l2_available=True)
    r = receipt(t, Profile.L2)
    x = preemption(t)
    args = dict(scope=SCOPE, current_source_revision_refs=CURRENT, now_ns=130,
                compute_admitted=True)
    assert result_is_current(r, t, d, preemption=x, **args)

    # Request revokes old-generation output admission immediately.
    x = x.append(PreemptionEvent(PreemptionPhase.CANCEL_REQUESTED, 131, INTERNAL))
    assert x.output_fenced and not x.l1_admitted
    assert not result_is_current(r, t, d, preemption=x, **args)
    with pytest.raises(CommonIOError, match="out-of-order"):
        x.append(PreemptionEvent(PreemptionPhase.RESOURCE_RELEASED, 132, INTERNAL,
                                 verification_ref="not-a-stop"))
    x = x.append(PreemptionEvent(PreemptionPhase.OUTPUT_FENCED, 132, INTERNAL))
    with pytest.raises(CommonIOError, match="verification"):
        PreemptionEvent(PreemptionPhase.BACKEND_STOPPED, 133, INTERNAL)
    assert not x.l1_admitted
    x = x.append(PreemptionEvent(
        PreemptionPhase.BACKEND_STOPPED, 133, INTERNAL, verification_ref="backend-stop-1"
    ))
    assert not x.l1_admitted
    x = x.append(PreemptionEvent(
        PreemptionPhase.RESOURCE_RELEASED, 134, INTERNAL, verification_ref="vram-free-1"
    ))
    assert not x.l1_admitted
    x = x.append(PreemptionEvent(
        PreemptionPhase.L1_ADMITTED, 135, INTERNAL, verification_ref="l1-grant-1"
    ))
    assert x.l1_admitted and len(x.events) == 5
    assert not result_is_current(r, t, d, preemption=x, **args)


@pytest.mark.parametrize("reason,override", [
    ("FOREIGN_SCOPE", {"scope": ScopeRef("self-B", "world-A")}),
    ("STALE_SOURCE", {"current_source_revision_refs": ("seq-42", "frame-4")}),
    ("DEADLINE_EXPIRED", {"now_ns": 200}),
])
def test_profile_selection_fails_closed(reason: str, override: dict) -> None:
    t = task(TaskRequirement.OPEN_REASONING)
    options = dict(scope=SCOPE, current_source_revision_refs=CURRENT,
                   now_ns=120, l2_available=True)
    d = select_profile(t, **(options | override))
    assert d.selected is Profile.DEFER and d.reason == reason
    assert d.resource_admission == "NOT_REQUESTED"


def test_incompatible_clocks_versions_unknown_and_inadequate_choices() -> None:
    with pytest.raises(CommonIOError, match="unknown time"):
        ClockStamp(Clock.UNKNOWN, 0)
    with pytest.raises(CommonIOError, match="unsupported"):
        replace(envelope("FAST_CUE"), schema_version=2)
    with pytest.raises(CommonIOError, match="at least two"):
        task(TaskRequirement.SELECT_FINITE, choices=(BoundedChoice("only", "one"),))
    with pytest.raises(CommonIOError, match="duplicates"):
        replace(task(TaskRequirement.OPEN_REASONING), source_revision_refs=("dup", "dup"))
    with pytest.raises(CommonIOError, match="host monotonic"):
        replace(envelope("FAST_CUE"), received_at=ClockStamp(Clock.WORLD_TICK, 40))


def test_preemption_cannot_advance_without_verified_stop_and_release() -> None:
    x = preemption(task(TaskRequirement.OPEN_REASONING))
    x = x.append(PreemptionEvent(PreemptionPhase.CANCEL_REQUESTED, 10, INTERNAL))
    x = x.append(PreemptionEvent(PreemptionPhase.OUTPUT_FENCED, 11, INTERNAL))
    with pytest.raises(CommonIOError, match="out-of-order"):
        x.append(PreemptionEvent(
            PreemptionPhase.L1_ADMITTED, 12, INTERNAL, verification_ref="fake-grant"
        ))
    with pytest.raises(CommonIOError, match="verification"):
        PreemptionEvent(PreemptionPhase.RESOURCE_RELEASED, 12, INTERNAL)
    assert not x.l1_admitted


def test_l2_result_rejects_old_generation_wrong_session_and_expired_deadline() -> None:
    t = task(TaskRequirement.OPEN_REASONING)
    d = decision(t, l2_available=True)
    r = receipt(t, Profile.L2)
    args = dict(scope=SCOPE, current_source_revision_refs=CURRENT, now_ns=130,
                compute_admitted=True, preemption=preemption(t))
    assert not result_is_current(replace(r, generation=0), t, d, **args)
    assert not result_is_current(
        replace(r, scope=ScopeRef("self-A", "world-old")), t, d, **args
    )
    assert not result_is_current(r, t, d, **(args | {"now_ns": 200}))
