"""S48 deterministic interrupt/cancellation and stale-context fences."""
from __future__ import annotations

from dataclasses import replace

import pytest

from relay_self.interruption_fence import (
    CognitionContext,
    InterruptEvidence,
    InterruptRejected,
    InterruptStage,
    L2InterruptionFence,
)
from relay_self.provenance import Provenance


def setup():
    owner = L2InterruptionFence()
    context = CognitionContext("world-A", 5, 1, 4)
    ticket = owner.start("l2-1", context)
    return owner, ticket, context


def test_uninterrupted_current_l2_result_can_be_read():
    owner, ticket, context = setup()
    owner.accept_l2_result(ticket, context)
    assert owner.ticket is None
    with pytest.raises(InterruptRejected):
        owner.accept_l2_result(ticket, context)


def test_l0_world_update_invalidates_l2_even_before_cancel():
    owner, ticket, context = setup()
    owner.observe(replace(context, world_seq=6))
    with pytest.raises(InterruptRejected):
        owner.accept_l2_result(ticket, context)
    with pytest.raises(InterruptRejected):
        owner.accept_l2_result(ticket, replace(context, world_seq=6))


def test_cancel_is_not_backend_ack_and_new_l2_cannot_start():
    owner, ticket, context = setup()
    owner.request_interrupt(ticket)
    owner.host_cancelled(ticket)
    assert owner.stage is InterruptStage.HOST_CANCELLED
    with pytest.raises(InterruptRejected):
        owner.retire_interrupted(ticket)
    with pytest.raises(InterruptRejected):
        owner.accept_l2_result(ticket, context)
    with pytest.raises(InterruptRejected):
        owner.start("l2-other", context)


def test_separately_attested_backend_stop_and_resource_release():
    owner, ticket, context = setup()
    owner.request_interrupt(ticket)
    owner.host_cancelled(ticket)
    stop = InterruptEvidence("l2-1", InterruptStage.BACKEND_STOP_ACK, Provenance("backend", "stop-1"))
    release = InterruptEvidence(
        "l2-1", InterruptStage.RESOURCE_RELEASE_EVIDENCED,
        Provenance("runtime", "measured-release-1"),
    )
    owner.backend_stop_ack(ticket, stop)
    owner.evidence_of_release(ticket, release)
    owner.retire_interrupted(ticket)
    assert owner.ticket is None
    next_ticket = owner.start("l2-2", context)
    assert next_ticket.generation > ticket.generation


def test_wrong_task_evidence_does_not_reclassify_cancellation():
    owner, ticket, _ = setup()
    owner.request_interrupt(ticket)
    with pytest.raises(InterruptRejected):
        owner.backend_stop_ack(
            ticket, InterruptEvidence(
                "foreign-l2", InterruptStage.BACKEND_STOP_ACK,
                Provenance("backend", "foreign"),
            ),
        )
    assert owner.stage is InterruptStage.REQUESTED
