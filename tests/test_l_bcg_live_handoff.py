"""L-BCG exact original S49 post-choice handoff: synthetic / nonphysical tests."""
from __future__ import annotations

import asyncio
import inspect
from dataclasses import replace

import pytest

from adapters.mineflayer.self_body_s50_l_bcg_handoff import (
    review_l_bcg_after_original_l0,
)
from relay_self.l1_bcg_motion_shadow import (
    Attention,
    BCGRejected,
    MotorSourceAdmission,
)
from relay_self.world_conditioned_choice import WorldChoiceKind
from test_l1_bcg_motion_shadow import _ctx, _fixture
from test_self_body_s50_l1_motion_shadow import real_type_pair


def test_live_host_default_off_and_requires_existing_route_b(tmp_path, monkeypatch):
    from adapters.mineflayer import self_body_s50_world_dev as host

    signature = inspect.signature(host.qualify)
    assert signature.parameters["l_bcg_shadow_dev"].default is False
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    output = tmp_path / "dev.json"
    assert asyncio.run(host.qualify(
        output, tmp_path / "server.log", l_bcg_shadow_dev=True,
    )) != 0
    assert "L-BCG shadow DEV requires original route B" in output.read_text()


def test_original_completed_l0_requires_abstention_without_full_cues():
    readout, choice = real_type_pair()
    assert choice.selection is WorldChoiceKind.WAIT
    before = choice
    result = review_l_bcg_after_original_l0(readout, choice)
    assert result.advice is Attention.DEFER
    assert result.reason == "CURRENT_GOAL_GAIT_P1_M_OBSTACLE_SOURCE_NOT_ADMITTED"
    assert result.original_selection == "WAIT"
    assert result.original_native_ref == readout.current_body.observation.source_ref
    assert result.conditional is None
    assert result.used_physical_training_worlds == 0
    assert result.source_ceiling == "ROUTE_B_PROVISIONAL_PAPER_NOT_POST_CLEAR_ATTESTED"
    assert not result.action_authority
    assert result.action_issues == result.extra_native_reads == 0
    assert result.learning_updates == result.habit_grants == 0
    assert choice is before


def test_provisional_paper_cannot_be_relabelled_as_training():
    readout, choice = real_type_pair()
    rows, admission = _fixture()
    with pytest.raises(BCGRejected, match="without complete current"):
        review_l_bcg_after_original_l0(
            readout, choice, training=rows, admission=admission,
        )


def test_separately_admitted_current_cues_are_bounded_and_never_execute():
    readout, choice = real_type_pair()
    body, world = readout.current_body, readout.current_world
    current = replace(
        _ctx(99, fast=True, near=False, fatigue=True, energy=False),
        self_id=body.self_id,
        session_id=body.session_id,
        world_id=readout.prior_window.paper_world_uuid,
        body_source_ref=body.observation.source_ref,
        world_source_ref=world.observation.source_ref,
        world_revision=999,
    )
    rows, original_admission = _fixture()
    rows = tuple(replace(
        row, context=replace(row.context, self_id=body.self_id),
    ) for row in rows)
    result = review_l_bcg_after_original_l0(
        readout, choice, current=current,
        training=rows, admission=original_admission,
    )
    assert result.advice is Attention.RECHECK
    assert result.conditional is not None
    assert result.conditional.cheap_exact_cue is Attention.DEFER
    assert result.used_physical_training_worlds == len(rows)
    assert result.source_ceiling.endswith("PHYSICAL_PROOF_EXTERNAL")
    assert result.original_l0_choice_kept
    assert result.action_issues == result.learning_updates == result.habit_grants == 0


def test_wrong_original_native_binding_rejected_even_in_shadow():
    readout, choice = real_type_pair()
    with pytest.raises(ValueError):
        review_l_bcg_after_original_l0(
            readout, replace(choice, probe_seq=choice.probe_seq + 1),
        )


def test_wrong_body_world_join_and_missing_admission_rejected():
    readout, choice = real_type_pair()
    c = _ctx(99, fast=True, near=False)
    with pytest.raises(BCGRejected, match="do not bind"):
        review_l_bcg_after_original_l0(
            readout, choice, current=c,
            training=(), admission=MotorSourceAdmission(frozenset(), frozenset()),
        )
    with pytest.raises(BCGRejected, match="do not bind"):
        review_l_bcg_after_original_l0(
            readout, choice, current=c,
        )
