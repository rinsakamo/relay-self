import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_VERSION,
    MineflayerAdapterStarted,
    MineflayerEffectResult,
    MineflayerLaunchConfig,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from adapters.mineflayer.runtime_admission import (
    MineflayerEpochResult,
    coordinate_mineflayer_message,
)
from relay_self.action import ActionLifecycle, ActionState, InvalidTransition
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(source="mineflayer-runtime-test", reference=reference)


def running_path(
    *,
    deadline_ns: int = 100,
) -> tuple[IntentCommitment, SkillExecution, ActionSupervisor]:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-1",
        objective="reach safety",
        at_ns=1,
        provenance=provenance("intent"),
    )
    skill = SkillExecution.start(
        "skill-1",
        skill_id="FLEE",
        intent_commitment=commitment,
        at_ns=2,
        provenance=provenance("skill"),
    )
    action = ActionLifecycle.propose(
        "action-1",
        skill_execution=skill,
        intent_commitment=commitment,
        at_ns=3,
        provenance=provenance("proposal"),
    ).authorize(
        at_ns=4,
        provenance=provenance("authorization"),
        authority="test-authority",
    )
    supervisor = ActionSupervisor()
    supervisor.issue(
        action,
        at_ns=5,
        deadline_ns=deadline_ns,
        provenance=provenance("issue"),
    )
    return commitment, skill, supervisor


def observation(
    kind: str,
    *,
    seq: int = 1,
) -> MineflayerObservation:
    return MineflayerObservation(
        session_id="session-1",
        seq=seq,
        kind=kind,
        snapshot=MineflayerSnapshot(
            health=12,
            food=7,
            oxygen_level=20,
            position=MineflayerPosition(x=1, y=64, z=2),
        ),
    )


def effect_result(
    result: str = "applied",
    *,
    seq: int = 2,
) -> MineflayerEffectResult:
    return MineflayerEffectResult(
        session_id="session-1",
        seq=seq,
        action_id="action-1",
        effect="set_control",
        result=result,
        error=None if result == "applied" else "server-or-client-refusal",
    )


def test_high_frequency_move_observation_is_not_automatically_admitted() -> None:
    _, _, supervisor = running_path()
    model_calls: list[object] = []

    result = coordinate_mineflayer_message(
        observation("move"),
        supervisor,
        at_ns=20,
        decision_step=lambda _message, _closure: {"need": "cognition"},
        relay_engine=lambda request: model_calls.append(request),
    )

    assert result is None
    assert model_calls == []
    assert supervisor.get("action-1").state is ActionState.ISSUED
    assert supervisor.last_at_ns == 5


def test_adapter_started_is_not_a_cognitive_epoch() -> None:
    _, _, supervisor = running_path()

    result = coordinate_mineflayer_message(
        MineflayerAdapterStarted(
            session_id="session-1",
            seq=0,
            mineflayer_version=MINEFLAYER_VERSION,
            config=MineflayerLaunchConfig(),
        ),
        supervisor,
        at_ns=20,
    )

    assert result is None
    assert supervisor.last_at_ns == 5


@pytest.mark.parametrize("kind", ["spawn", "health", "forcedMove", "death", "respawn"])
def test_material_observation_reaches_canonical_coordinator_without_model(
    kind: str,
) -> None:
    _, _, supervisor = running_path()
    seen: list[str] = []

    result = coordinate_mineflayer_message(
        observation(kind),
        supervisor,
        at_ns=20,
        decision_step=lambda message, _closure: seen.append(message.kind),
    )

    assert isinstance(result, MineflayerEpochResult)
    assert seen == [kind]
    assert result.action_closure is None
    assert result.decision_epoch.cognition_requested is False
    assert result.decision_epoch.next_action_deadline_ns == 100
    assert supervisor.get("action-1").state is ActionState.ISSUED


def test_action_supervision_runs_before_material_observation_decision_work() -> None:
    _, skill, supervisor = running_path(deadline_ns=50)
    observed_states: list[ActionState] = []

    result = coordinate_mineflayer_message(
        observation("health"),
        supervisor,
        at_ns=50,
        decision_step=lambda _message, _closure: observed_states.append(
            supervisor.get("action-1").state
        ),
    )

    assert isinstance(result, MineflayerEpochResult)
    assert observed_states == [ActionState.TIMEOUT]
    assert [action.action_id for action in result.decision_epoch.timed_out_actions] == [
        "action-1"
    ]
    assert skill.state is SkillState.STARTED


def test_unresolved_material_observation_uses_supplied_engine_once() -> None:
    _, _, supervisor = running_path()
    request = {"kind": "bounded-choice", "choices": ("left", "right")}
    calls: list[object] = []

    result = coordinate_mineflayer_message(
        observation("health"),
        supervisor,
        at_ns=20,
        decision_step=lambda _message, _closure: request,
        relay_engine=lambda received: calls.append(received) or {"choice": "left"},
    )

    assert isinstance(result, MineflayerEpochResult)
    assert calls == [request]
    assert result.decision_epoch.cognition_requested is True
    assert result.decision_epoch.cognition_result == {"choice": "left"}


@pytest.mark.parametrize("adapter_result", ["applied", "rejected"])
def test_effect_result_closes_action_as_known_outcome_before_decision_epoch(
    adapter_result: str,
) -> None:
    commitment, skill, supervisor = running_path()
    seen: list[tuple[str, ActionState]] = []

    result = coordinate_mineflayer_message(
        effect_result(adapter_result),
        supervisor,
        at_ns=20,
        decision_step=lambda message, closure: seen.append(
            (message.result, closure.state)
        ),
    )

    assert isinstance(result, MineflayerEpochResult)
    assert result.action_closure is not None
    assert result.action_closure.state is ActionState.OUTCOME
    assert result.action_closure.events[-1].provenance.reference == "session-1:2"
    assert seen == [(adapter_result, ActionState.OUTCOME)]
    assert result.decision_epoch.timed_out_actions == ()
    assert skill.state is SkillState.STARTED
    assert commitment.current_intent is not None
    assert commitment.current_intent.intent_id == "intent-1"


def test_applied_effect_is_not_promoted_to_skill_success() -> None:
    _, skill, supervisor = running_path()

    coordinate_mineflayer_message(
        effect_result("applied"),
        supervisor,
        at_ns=20,
    )

    assert supervisor.get("action-1").state is ActionState.OUTCOME
    assert skill.state is SkillState.STARTED


def test_late_effect_result_cannot_rewrite_timeout() -> None:
    _, _, supervisor = running_path(deadline_ns=10)
    supervisor.advance(at_ns=10, provenance=provenance("timeout"))

    with pytest.raises(InvalidTransition, match="timeout to outcome"):
        coordinate_mineflayer_message(
            effect_result("applied"),
            supervisor,
            at_ns=11,
        )

    assert supervisor.get("action-1").state is ActionState.TIMEOUT
