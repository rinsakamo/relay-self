"""Offline Schema #831 positive and negative controls.

No real World, LLM, action issuer, automatic Goal, or learning update.
"""

from dataclasses import replace

import pytest

from relay_self.appraisal import (
    AppraisalAspect,
    AppraisalBias,
    AppraisalDisposition,
    AppraisalTargetKind,
    project_entity_appraisal,
)
from relay_self.common_io import (
    Clock,
    ClockStamp,
    CommonEnvelope,
    FastCue,
    ScopeRef,
    fast_cue_eligible,
)
from relay_self.innate_schema import (
    CognitiveSignal,
    Engagement,
    ExplorationOpportunity,
    NeedPressure,
    SchemaActivation,
    SchemaContractError,
    SchemaDependency,
    SchemaMode,
    SchemaModuleSpec,
    SchemaSnapshot,
    check_schema_eligibility,
    propose_exploratory_question,
    signal_is_current,
    with_schema_mode,
)
from relay_self.persistent_cognition import IdentitySpecification, Memory, PersistentCognition
from relay_self.provenance import Provenance

SCOPE = ScopeRef("self-A", "world-A")
NATIVE = Provenance("native", "seq-14")
SCHEMA = Provenance("schema-owner", "spec-v1")
CATALOG = Provenance("action-catalog", "revision-5")
CURRENT = ("native-seq-14", "present-5")


def envelope(kind: str, *, scope: ScopeRef = SCOPE) -> CommonEnvelope:
    return CommonEnvelope(
        event_id=f"{kind}-14",
        kind=kind,
        scope=scope,
        occurred_at=ClockStamp(Clock.WORLD_TICK, 14),
        received_at=ClockStamp(Clock.HOST_MONOTONIC_NS, 100),
        provenance=NATIVE,
        source_refs=(NATIVE,),
    )


def module(
    schema_id: str,
    *,
    modes: frozenset[SchemaMode] = frozenset({SchemaMode.FAST, SchemaMode.FULL}),
    depends: tuple[SchemaDependency, ...] = (),
    kinds: tuple[str, ...] = ("QUESTION_CANDIDATE",),
) -> SchemaModuleSpec:
    return SchemaModuleSpec(
        schema_id=schema_id,
        version=1,
        supported_modes=modes,
        signal_kinds=kinds,
        dependencies=depends,
        provenance=SCHEMA,
    )


def snapshot() -> SchemaSnapshot:
    return SchemaSnapshot(
        self_id="self-A",
        revision=7,
        modules=(
            SchemaActivation(module("perceptual", kinds=("ATTENTION_CANDIDATE",)),
                             SchemaMode.FAST),
            SchemaActivation(module("motivational", kinds=("NEED_CANDIDATE",)),
                             SchemaMode.FULL),
            SchemaActivation(
                module("exploratory", depends=(
                    SchemaDependency("perceptual", SchemaMode.FAST),
                    SchemaDependency("motivational", SchemaMode.FULL),
                )),
                SchemaMode.FULL,
            ),
        ),
    )


def opportunity() -> ExplorationOpportunity:
    return ExplorationOpportunity(
        envelope=envelope("PRESENT_FRAME"),
        source_revision_refs=CURRENT,
        target_observation_ref=NATIVE,
        unknown_target_ref="observed-unknown-entity-1",
        reference_action_refs=("action-ref-1", "action-ref-2"),
        action_catalog_provenance=CATALOG,
        engagement=Engagement.IDLE,
        need_pressure=NeedPressure.LOW,
    )


def propose(
    config: SchemaSnapshot | None = None,
    context: ExplorationOpportunity | None = None,
    *,
    signal_envelope: CommonEnvelope | None = None,
    current_revision: int = 7,
    sources: tuple[str, ...] = CURRENT,
) -> CognitiveSignal | None:
    return propose_exploratory_question(
        snapshot=snapshot() if config is None else config,
        schema_id="exploratory",
        opportunity=opportunity() if context is None else context,
        signal_envelope=envelope("COGNITIVE_SIGNAL") if signal_envelope is None
        else signal_envelope,
        current_registry_revision=current_revision,
        current_source_revision_refs=sources,
    )


def test_schema_spec_and_dependency_modes_reuse_common_scope_and_provenance() -> None:
    config = snapshot()
    assert config.get("exploratory").spec.provenance is SCHEMA
    assert check_schema_eligibility(
        config, scope=SCOPE, schema_id="exploratory",
        requested_mode=SchemaMode.FULL, current_registry_revision=7,
    ).allowed
    result = check_schema_eligibility(
        config, scope=SCOPE, schema_id="exploratory",
        requested_mode=SchemaMode.FAST, current_registry_revision=7,
    )
    assert result.allowed and result.reason == "ELIGIBLE"
    # A full-capable module can expose only its declared FAST-compatible signals;
    # this DOES NOT mean a FULL result can be passed off as FAST.


def test_schema_off_invalidates_output_but_retains_memory_and_appraisal() -> None:
    memory = Memory(
        memory_id="experience-1", content="Attested past, not present World truth",
        source_provenance=NATIVE, integration_provenance=SCHEMA,
    )
    identity = IdentitySpecification("self-A", ("Continue to explore.",), SCHEMA)
    seeded = AppraisalDisposition(
        target_kind=AppraisalTargetKind.ENTITY_INSTANCE,
        target_key="observed-unknown-entity-1",
        aspect=AppraisalAspect.HARM_LIKELIHOOD,
        bias=AppraisalBias.NEUTRAL,
        source_provenance=SCHEMA,
        integration_provenance=SCHEMA,
    )
    retained = PersistentCognition(identity=identity).retain_memory(memory)
    retained = retained.seed_appraisal_disposition(seeded)
    config = snapshot()
    signal = propose(config)
    assert signal is not None
    off = with_schema_mode(config, schema_id="exploratory", mode=SchemaMode.OFF)
    assert off.revision == 8
    assert not signal_is_current(
        signal, snapshot=off, scope=SCOPE, source_revision_refs=CURRENT,
        requested_mode=SchemaMode.FULL, current_registry_revision=8,
    )
    assert propose(off, current_revision=8) is None
    assert retained.memories == (memory,)
    current = project_entity_appraisal(
        entity_class="unknown", entity_instance="observed-unknown-entity-1",
        observation_provenance=NATIVE, dispositions=retained.appraisal_dispositions,
    )
    assert current.bias_for(AppraisalAspect.HARM_LIKELIHOOD) is AppraisalBias.NEUTRAL
    assert retained.appraisal_dispositions == (seeded,)


def test_exploration_question_is_only_generic_candidate_with_unselected_actions() -> None:
    signal = propose()
    assert signal is not None
    assert signal.signal_kind == "QUESTION_CANDIDATE"
    assert signal.epistemic_status == "HYPOTHETICAL"
    assert signal.question_candidate.unknown_target_ref == "observed-unknown-entity-1"
    assert signal.question_candidate.reference_action_refs == ("action-ref-1", "action-ref-2")
    assert signal.question_candidate.inquiry == "OBSERVE_UNKNOWN_EFFECT"
    assert signal.execution_mode is SchemaMode.FULL
    assert not hasattr(signal, "action_id")
    assert not hasattr(signal, "intent_id")
    assert not hasattr(signal, "world_outcome")
    assert signal_is_current(
        signal, snapshot=snapshot(), scope=SCOPE, source_revision_refs=CURRENT,
        requested_mode=SchemaMode.FULL, current_registry_revision=7,
    )
    assert not signal_is_current(
        signal, snapshot=snapshot(), scope=SCOPE, source_revision_refs=CURRENT,
        requested_mode=SchemaMode.FAST, current_registry_revision=7,
    )


@pytest.mark.parametrize("engagement,need", [
    (Engagement.BUSY, NeedPressure.LOW),
    (Engagement.UNKNOWN, NeedPressure.LOW),
    (Engagement.IDLE, NeedPressure.URGENT),
    (Engagement.IDLE, NeedPressure.UNKNOWN),
])
def test_exploration_defers_when_idle_or_need_state_not_qualified(
    engagement: Engagement, need: NeedPressure,
) -> None:
    assert propose(context=replace(opportunity(), engagement=engagement,
                                   need_pressure=need)) is None


def test_exploration_rejects_missing_reference_actions_or_stale_world_source() -> None:
    assert propose(context=replace(opportunity(), reference_action_refs=())) is None
    assert propose(sources=("old-native", "present-5")) is None
    assert propose(signal_envelope=envelope("COGNITIVE_SIGNAL", scope=ScopeRef(
        "self-B", "world-A"
    ))) is None
    with pytest.raises(SchemaContractError, match="target observation"):
        replace(opportunity(), target_observation_ref=Provenance("native", "not-observed"))


def test_dependency_off_and_insufficient_full_declared_requirement_fail_closed() -> None:
    config = snapshot()
    no_percept = with_schema_mode(config, schema_id="perceptual", mode=SchemaMode.OFF)
    e = check_schema_eligibility(
        no_percept, scope=SCOPE, schema_id="exploratory",
        requested_mode=SchemaMode.FULL, current_registry_revision=8,
    )
    assert not e.allowed and e.reason == "DEPENDENCY_UNAVAILABLE"
    assert propose(no_percept, current_revision=8) is None

    no_full_need = with_schema_mode(config, schema_id="motivational", mode=SchemaMode.FAST)
    blocked = check_schema_eligibility(
        no_full_need, scope=SCOPE, schema_id="exploratory",
        requested_mode=SchemaMode.FULL, current_registry_revision=8,
    )
    assert not blocked.allowed and blocked.reason == "DEPENDENCY_UNAVAILABLE"


def test_wrong_self_and_registry_epoch_reject_without_mutating_goal() -> None:
    config = snapshot()
    for scope,revision,reason in [
        (ScopeRef("self-B", "world-A"), 7, "FOREIGN_SELF"),
        (SCOPE, 8, "STALE_REGISTRY"),
    ]:
        e = check_schema_eligibility(
            config, scope=scope, schema_id="exploratory",
            requested_mode=SchemaMode.FULL, current_registry_revision=revision,
        )
        assert not e.allowed and e.reason == reason
    signal = propose(config)
    assert signal is not None
    assert not signal_is_current(
        signal, snapshot=config, scope=ScopeRef("self-B", "world-A"),
        source_revision_refs=CURRENT, requested_mode=SchemaMode.FULL,
        current_registry_revision=7,
    )
    assert not signal_is_current(
        signal, snapshot=config, scope=SCOPE, source_revision_refs=("old", "present-5"),
        requested_mode=SchemaMode.FULL, current_registry_revision=7,
    )


def test_old_signal_cannot_be_reused_after_mode_toggle_round_trip() -> None:
    config = snapshot()
    old = propose(config)
    assert old is not None
    off = with_schema_mode(config, schema_id="exploratory", mode=SchemaMode.OFF)
    on = with_schema_mode(off, schema_id="exploratory", mode=SchemaMode.FULL)
    assert on.revision == 9 and on.get("exploratory").mode is SchemaMode.FULL
    assert not signal_is_current(
        old, snapshot=on, scope=SCOPE, source_revision_refs=CURRENT,
        requested_mode=SchemaMode.FULL, current_registry_revision=9,
    )
    assert propose(on, current_revision=9) is not None


def test_module_registry_rejects_cycle_unknown_dependency_and_duplicate() -> None:
    a = module("A", depends=(SchemaDependency("B"),))
    b = module("B", depends=(SchemaDependency("A"),))
    with pytest.raises(SchemaContractError, match="cycle"):
        SchemaSnapshot("self-A", 1, (
            SchemaActivation(a, SchemaMode.FULL), SchemaActivation(b, SchemaMode.FULL)
        ))
    with pytest.raises(SchemaContractError, match="unknown schema dependency"):
        SchemaSnapshot("self-A", 1, (SchemaActivation(a, SchemaMode.FULL),))
    with pytest.raises(SchemaContractError, match="duplicate schema id"):
        SchemaSnapshot("self-A", 1, (
            SchemaActivation(a, SchemaMode.FULL), SchemaActivation(a, SchemaMode.FAST)
        ))


def test_invalid_schema_modes_and_observed_world_signal_are_forbidden() -> None:
    with pytest.raises(SchemaContractError, match="supported_modes"):
        module("invalid", modes=frozenset({SchemaMode.OFF}))
    with pytest.raises(SchemaContractError, match="unsupported activation"):
        SchemaActivation(module("only-full", modes=frozenset({SchemaMode.FULL})),
                         SchemaMode.FAST)
    with pytest.raises(SchemaContractError, match="minimum_mode"):
        SchemaDependency("perceptual", SchemaMode.OFF)
    with pytest.raises(SchemaContractError, match="World fact"):
        replace(propose(), epistemic_status="OBSERVED")


def test_fast_cue_original_installed_cpu_path_not_controlled_by_schema_registry() -> None:
    # An existing S49-validated installed safety rule does not depend on
    # the new schema registry. This helper still never issues the Action.
    cue = FastCue(
        envelope=envelope("FAST_CUE"),
        source_revision_ref="native-seq-14",
        installed_rule_ref="existing-s49-emergency-rule",
        expires_at_ns=150,
    )
    disabled = with_schema_mode(snapshot(), schema_id="exploratory", mode=SchemaMode.OFF)
    assert disabled.get("exploratory").mode is not SchemaMode.FULL
    assert fast_cue_eligible(
        cue, scope=SCOPE, source_revision_ref="native-seq-14",
        installed_rule_refs=frozenset({"existing-s49-emergency-rule"}), now_ns=120,
    )
    assert not fast_cue_eligible(
        cue, scope=SCOPE, source_revision_ref="native-seq-14",
        installed_rule_refs=frozenset({"existing-s49-emergency-rule"}), now_ns=150,
    )
