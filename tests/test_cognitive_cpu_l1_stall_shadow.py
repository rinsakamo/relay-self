"""Bounded offline CPU Schema shadow under a deliberately stalled L1.

No real GPU contention, Mineflayer World, Action issuance or FAST deadline
claim; simulated source frames are typed WorldPercepts from one fake owner.
"""
from __future__ import annotations

import asyncio
import threading

import pytest

from experiments.cognitive_cpu_l1_stall_shadow import simulate_cpu_schema_during_l1
from relay_self.cognitive_minimal_dev import (
    MinimalCognitionError,
    Target,
    WorldPercept,
    assemble_l1_select,
    cpu_schema_epoch,
    initial_patterns,
    resolve_l1_choice,
)
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionMode, ProviderDecision, RelayEngine

SKILLS = frozenset({("EAT", 1), ("ATTACK", 1)})


def percept(epoch: int, *, source_session: str = "world-A",
            food: bool = False, zombie: bool = False) -> WorldPercept:
    source = Provenance("simulated-readonly-gateway", f"{source_session}:{epoch}")
    targets: list[Target] = []
    if food:
        targets.append(Target("bread-1", "FOOD", source, source_session, epoch))
    if zombie:
        targets.append(Target("entity-7", "ZOMBIE", source, source_session, epoch))
    return WorldPercept(
        ScopeRef("self-A", source_session), source, epoch,
        hunger=7 if food else 20, fatigue_high=None, targets=tuple(targets),
    )


def test_d5_48_cpu_epochs_and_fast_while_l1_is_blocked() -> None:
    started = threading.Event()
    release = threading.Event()
    owner = IntentCommitment()
    initial = cpu_schema_epoch(
        percept(1, food=True), initial_patterns(), epoch=1,
        allowed_skills=SKILLS,
    )
    round_ = assemble_l1_select(initial, intent_owner=owner)

    def blocked_provider(request, *, mode):
        assert mode is CognitionMode.BOUNDED
        started.set()
        assert release.wait(timeout=5)
        return ProviderDecision.resolved("1")

    def simulated_latest(i: int) -> WorldPercept:
        if i <= 12:
            return percept(i, food=True)
        if i <= 36:
            return percept(i, zombie=True)
        return percept(i, source_session="world-B")

    async def run():
        task = asyncio.create_task(
            asyncio.to_thread(RelayEngine(blocked_provider), round_.request)
        )
        for _ in range(300):
            if started.is_set():
                break
            await asyncio.sleep(.001)
        assert started.is_set()
        try:
            trace = await simulate_cpu_schema_during_l1(
                l1_task=task,
                percept_at_epoch=simulated_latest,
                registry=initial_patterns(),
                allowed_skills=SKILLS,
                epochs=48,
                period_s=.001,
            )
            assert trace.l1_still_pending_at_exit
            assert len(trace.samples) == 48
            assert all(sample.l1_pending_at_sample for sample in trace.samples)
            assert all(sample.pattern_checks >= 3 for sample in trace.samples)
            assert trace.max_schema_elapsed_ns >= trace.p95_schema_elapsed_ns
            assert trace.p95_schema_elapsed_ns >= trace.p50_schema_elapsed_ns
            assert trace.deadline_misses >= 0
            assert trace.session_changes == 1
            assert any(sample.fast_cues == ("ZOMBIE_NEAR",)
                       for sample in trace.samples)
            assert trace.samples[-1].fast_cues == ()
        finally:
            release.set()
        result = await task
        selection = resolve_l1_choice(
            round_, result,
            current_frame=cpu_schema_epoch(
                simulated_latest(48), initial_patterns(),
                epoch=48, allowed_skills=SKILLS,
            ),
            intent_owner=owner,
            available_skills=SKILLS,
        )
        assert selection.status == "REJECTED"
        assert owner.current_intent is None
        assert owner.events == ()
        return trace

    try:
        trace = asyncio.run(run())
    finally:
        release.set()
    assert trace.evidence_class == "OFFLINE_SHADOW_CPU_WHILE_L1_PENDING"


def test_cpu_shadow_caps_work_when_l1_never_finishes_in_window() -> None:
    started = threading.Event()
    release = threading.Event()

    def provider(request, *, mode):
        started.set()
        assert release.wait(timeout=5)
        return ProviderDecision.resolved("1")

    async def run():
        initial = cpu_schema_epoch(
            percept(1, food=True), initial_patterns(), epoch=1,
            allowed_skills=SKILLS,
        )
        round_ = assemble_l1_select(initial, intent_owner=IntentCommitment())
        task = asyncio.create_task(asyncio.to_thread(RelayEngine(provider), round_.request))
        for _ in range(300):
            if started.is_set():
                break
            await asyncio.sleep(.001)
        try:
            trace = await simulate_cpu_schema_during_l1(
                l1_task=task, percept_at_epoch=lambda n: percept(n, zombie=True),
                registry=initial_patterns(), allowed_skills=SKILLS,
                epochs=8, period_s=.001,
            )
            assert len(trace.samples) == 8 and trace.l1_still_pending_at_exit
            assert all("ZOMBIE_NEAR" in sample.fast_cues for sample in trace.samples)
        finally:
            release.set()
        await task
    try:
        asyncio.run(run())
    finally:
        release.set()


def test_cpu_shadow_invalid_frame_fails_without_physical_recovery() -> None:
    started = threading.Event()
    release = threading.Event()

    def provider(request, *, mode):
        started.set()
        assert release.wait(timeout=5)
        return ProviderDecision.resolved("1")

    async def run():
        f = cpu_schema_epoch(percept(1, food=True), initial_patterns(), epoch=1,
                             allowed_skills=SKILLS)
        task = asyncio.create_task(
            asyncio.to_thread(RelayEngine(provider),
                              assemble_l1_select(f, intent_owner=IntentCommitment()).request)
        )
        for _ in range(300):
            if started.is_set():
                break
            await asyncio.sleep(.001)
        try:
            with pytest.raises(MinimalCognitionError, match="source"):
                await simulate_cpu_schema_during_l1(
                    l1_task=task, percept_at_epoch=lambda _: None,
                    registry=initial_patterns(), allowed_skills=SKILLS,
                    epochs=4, period_s=.001,
                )
        finally:
            release.set()
        await task
    try:
        asyncio.run(run())
    finally:
        release.set()
