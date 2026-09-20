from __future__ import annotations

from dataclasses import dataclass, replace

from experiments.flee_memory_retrieval import (
    FleeRetrievalResult,
    reference_cognition,
    retrieve_flee_memories,
)
from experiments.focus_attention_epoch import (
    VIABILITY_INTERRUPT_KEY,
    FleeAttentionResult,
    attend_flee,
)
from experiments.present_relay_engine_seam import (
    build_flee_relay_request,
    model_reference_facts,
    relay_result_to_flee_decision,
)
from experiments.present_skill_epoch import (
    FleeDecision,
    PresentFact,
    PresentProjection,
    build_present,
    narrow_for_flee,
    start_flee_execution,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionDatum,
    RelayEngine,
    RelayEngineResult,
)
from relay_self.skill import SkillExecution


@dataclass(frozen=True, slots=True)
class FleeCognitionPipelineEpoch:
    broad: PresentProjection
    local: PresentProjection
    attention: FleeAttentionResult
    retrieval: FleeRetrievalResult
    request: BoundedChoiceRequest
    cognition: RelayEngineResult
    decision: FleeDecision
    execution: SkillExecution | None


def build_pipeline_present(
    *,
    intent_commitment: IntentCommitment,
    source_revision: int,
    viability_breach_imminent: bool,
) -> PresentProjection:
    facts = (
        *model_reference_facts(revision=source_revision),
        PresentFact(
            VIABILITY_INTERRUPT_KEY,
            viability_breach_imminent,
            Provenance(
                source="fixture.viability",
                reference=f"rev:{source_revision}:viability-breach",
            ),
        ),
        PresentFact(
            "weather",
            "clear",
            Provenance(
                source="fixture.world",
                reference=f"rev:{source_revision}:weather",
            ),
        ),
    )
    return build_present(
        intent_commitment=intent_commitment,
        source_revision=source_revision,
        facts=facts,
    )


def add_retrieved_memories(
    request: BoundedChoiceRequest,
    retrieval: FleeRetrievalResult,
) -> BoundedChoiceRequest:
    memory_context = tuple(
        CognitionDatum.from_value(
            f"memory:{memory.memory_id}",
            {
                "memory_id": memory.memory_id,
                "content": memory.content,
            },
            memory.source_provenance,
        )
        for memory in retrieval.memories
    )
    return replace(
        request,
        context=(*request.context, *memory_context),
    )


def run_flee_cognition_pipeline(
    *,
    engine: RelayEngine,
    intent_commitment: IntentCommitment,
    broad: PresentProjection,
    current_source_revision: int,
    execution_id: str = "flee-cognition-pipeline-1",
    attention_at_ns: int = 2,
    execution_at_ns: int = 3,
) -> FleeCognitionPipelineEpoch:
    local = narrow_for_flee(broad)
    attention = attend_flee(
        broad=broad,
        local=local,
        current_source_revision=current_source_revision,
        intent_commitment=intent_commitment,
        at_ns=attention_at_ns,
    )
    retrieval = retrieve_flee_memories(
        attention=attention,
        cognition=reference_cognition(),
        intent_commitment=intent_commitment,
    )
    request = add_retrieved_memories(
        build_flee_relay_request(
            local,
            current_source_revision=current_source_revision,
            request_id="flee-focus-retrieval:00",
        ),
        retrieval,
    )
    cognition = engine(request)
    decision = relay_result_to_flee_decision(cognition)
    execution = None
    if decision.destination is not None:
        execution = start_flee_execution(
            decision=decision,
            intent_commitment=intent_commitment,
            execution_id=execution_id,
            at_ns=execution_at_ns,
            provenance=Provenance(
                source="focus-retrieval-think-pipeline",
                reference="resolved-flee-binding",
            ),
        )

    return FleeCognitionPipelineEpoch(
        broad=broad,
        local=local,
        attention=attention,
        retrieval=retrieval,
        request=request,
        cognition=cognition,
        decision=decision,
        execution=execution,
    )
