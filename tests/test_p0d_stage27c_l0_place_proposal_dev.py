"""Stage27c: source-bound L0 PREPARED proposal, not a native MOVE issuer."""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from relay_self.p0d_stage27c_l0_place_proposal_dev import (
    Stage27L0ProposalRefusal,
    propose_stage27c_original_place_move,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalCapability
from relay_self.provenance import Provenance
from test_p0d_real_preset_checkpoint_dev import native_probe
from test_p0d_resident_llama_slot_owner_dev import (
    ResidentFixture,
    _SyntheticLlamaServer,
)
from test_p0d_stage26_gemma_l1_dev import _attach_and_audit
from test_p0d_stage27b_place_motion_dev import _resolve, qualified_a


def cap(*, available=True, target_kind="DESTINATION"):
    return PhysicalCapability("MOVE", 1, "locomotion", target_kind, available)


def prepare(f, pre, handoff, plan, observed, **kwargs):
    args = dict(
        prepared=pre, handoff=handoff, planned=plan, native=observed,
        owner=f.owners[f.names[0]], physical=f.physical,
        world_epoch=pre.world_epoch, capability=cap(), at_ns=200,
        provenance=Provenance("stage27c-original", "source-bound-proposal"),
    )
    args.update(kwargs)
    return propose_stage27c_original_place_move(**args)


def test_original_a_bound_preset_to_l0_proposal_only_b_has_no_mutation(tmp_path):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        pre, handoff, observed = await qualified_a(f, lane)
        plan = _resolve(f, pre, handoff, observed)
        b = f.owners[f.names[1]]
        before_b = (
            b.intent.events, tuple(b.skills.items()),
            PhysicalActionJournal.restore(
                b.files.physical_wal_file, self_id=b.self_id,
            ).digest,
        )
        result = prepare(f, pre, handoff, plan, observed)
        assert result.self_id == f.names[0]
        assert result.native_probe_seq == observed.seq
        assert result.original_invocation_ref == handoff.invocation_ref
        assert result.original_preset_ref == handoff.preset_ref
        assert result.target_contract_ref == plan.target_contract_ref
        assert result.intent_id == handoff.intent_id
        assert result.skill_execution_id == handoff.skill_execution_id
        assert result.proposal.binding.target_ref == handoff.target_ref
        assert result.proposal.binding.target_kind == "DESTINATION"
        assert result.proposal.proposal.state.value == "proposed"
        assert result.status == "PROPOSED_NOT_ISSUABLE_UNTIL_ORIGINAL_PLACE_WAL"
        assert result.ir.invocation is pre.round.frame.options[0].invocation
        assert result.cursor.pending_action_id == result.action_id
        assert result.cursor.action_count == 1
        assert not result.native_grant
        assert not result.journal_prepared
        assert not result.physical_effect_sent
        assert len(http.calls) == 1
        assert (b.intent.events, tuple(b.skills.items()),
                PhysicalActionJournal.restore(
                    b.files.physical_wal_file, self_id=b.self_id,
                ).digest) == before_b
        for sid in f.names:
            assert not f.owners[sid].supervisor.open_actions
            PhysicalActionJournal.restore(
                f.owners[sid].files.physical_wal_file, self_id=sid,
            ).require_clear()
            await f.bridge.logout(sid)

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()


@pytest.mark.parametrize("fault", [
    "foreign-actor", "wrong-epoch", "wrong-invocation",
    "wrong-contract", "wrong-preset", "not-outside", "claim-grant",
    "claim-effect", "wrong-capability", "no-capability", "old-native",
    "old-probe", "wrong-request", "wrong-target", "before-start",
])
def test_stage27c_bounded_proposal_refuses_stale_or_forged_source(tmp_path, fault):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        pre, handoff, observed = await qualified_a(f, lane)
        plan = _resolve(f, pre, handoff, observed)
        args = {}
        if fault == "foreign-actor":
            args["owner"] = f.owners[f.names[1]]
        elif fault == "wrong-epoch":
            args["world_epoch"] = pre.world_epoch + 1
        elif fault == "wrong-invocation":
            plan = replace(plan, invocation_ref="bad-invocation")
        elif fault == "wrong-contract":
            plan = replace(plan, target_contract_ref="bad-contract")
        elif fault == "wrong-preset":
            plan = replace(plan, parameter_preset_ref="bad-preset")
        elif fault == "not-outside":
            plan = replace(plan, observation_status="CONDITION_OBSERVED")
        elif fault == "claim-grant":
            plan = replace(plan, action_granted=True)
        elif fault == "claim-effect":
            plan = replace(plan, native_effect_issued=True)
        elif fault == "wrong-capability":
            args["capability"] = cap(target_kind="RELATIVE")
        elif fault == "no-capability":
            args["capability"] = cap(available=False)
        elif fault == "old-native":
            observed = native_probe(
                f.names[0], observed.seq + 2,
                session=pre.original_native_session,
            )
        elif fault == "old-probe":
            observed = native_probe(
                f.names[0], handoff.rechecked_native_seq - 1,
                session=pre.native_session,
            )
        elif fault == "wrong-request":
            observed = replace(observed, request_id="other-request")
        elif fault == "wrong-target":
            handoff = replace(handoff, target_ref="unknown-destination")
        elif fault == "before-start":
            args["at_ns"] = 1
        with pytest.raises((Stage27L0ProposalRefusal, ValueError)):
            prepare(f, pre, handoff, plan, observed, **args)
        for sid in f.names:
            assert not f.owners[sid].supervisor.open_actions
            PhysicalActionJournal.restore(
                f.owners[sid].files.physical_wal_file, self_id=sid,
            ).require_clear()
            await f.bridge.logout(sid)

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()


def test_stage27c_new_proposal_refuses_logout_after_model_choice(tmp_path):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        pre, handoff, observed = await qualified_a(f, lane)
        plan = _resolve(f, pre, handoff, observed)
        await f.bridge.logout(f.names[0])
        with pytest.raises(Stage27L0ProposalRefusal):
            prepare(f, pre, handoff, plan, observed)
        await f.bridge.logout(f.names[1])

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()
