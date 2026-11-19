"""C Lane: one real Stage28 typed World+A/B generation with a retained C1.

The World, original physical WAL and new Paper/native sources are SYNTHETIC
Stage28 test fixtures. The original checkpoint, recovery, Owner, and source
verification code paths are used without mocking their readers. No Gemma,
real Minecraft, real C2 or physical Action was executed.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from relay_self.c_lane_stage28_typed_continuity_dev import (
    C1TypedCheckpointHold,
    verify_c1_across_stage28_typed_epoch,
)
from relay_self.checkpointed_cognitive_runtime_dev import (
    CognitionOwnerCohort,
    ExternalPhysicalFence,
    ExternalRejoin,
)
from relay_self.cognitive_learning_contract import CurrentCue, RetainedRevisionRead
from relay_self.cognitive_learning_owner_adapter import (
    c3_shadow_l1_context,
    propose_existing_memory,
)
from relay_self.common_io import ScopeRef
from relay_self.persistent_cognition import save_persistent_cognition
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice
from relay_self.stage28_cognitive_recovery_gate_dev import (
    stage28_require_fresh_l1_eligibility,
)
from relay_self.stage28b_retired_resident_typed_cut_dev import (
    capture_retired_resident_typed_world,
)
from relay_self.stage28c2b_execution_copy_dev import create_execution_copy
from relay_self.three_self_present import EpistemicStatus
from test_c_lane_stage28_actual_recovered_owner_dev import (
    _candidate,
    _historical_synthetic_c1,
)
from test_p0d_resident_move_issuer_dev import _probe
from test_stage28b_retired_typed_cut_dev import _setup
from test_stage28c1_inert_restore_dev import _prepare
from test_stage28c2b_fork_paper_epoch_dev import _idle
from test_stage28c2b_native_paper_dual_clock_dev import _clock_context, _link

P = Provenance("c-lane-cross-generation-test", "synthetic-original")


def _case(tmp_path, monkeypatch):
    import test_stage28c2b_native_paper_dual_clock_dev as clock_test

    # Existing original A/B sources and canonical WALs, NOT a new C owner.
    source_bridge, source_paper, store, evidence = _setup(tmp_path, monkeypatch)
    a, b = source_bridge.owners["A"], source_bridge.owners["B"]
    exp = _historical_synthetic_c1()
    # The specific Stage28 fixture uses retired native sessions at its cut.
    old_scope = ScopeRef("A", "native-retired-A")
    exp = replace(
        exp, scope=old_scope,
        before=replace(exp.before, scope=old_scope),
        after=replace(exp.after, scope=old_scope),
    )
    assert exp.memory_id.startswith("c1-skillrun:")
    proposal = propose_existing_memory(a.retained, exp, integration_provenance=P)
    assert proposal is not None
    # Source owner must *explicitly* accept, not the C adapter. This actual
    # CognitionOwnerCohort provides the original owner mutation gate; the
    # world retirement transition itself is a scripted offline fixture.
    cohort = CognitionOwnerCohort(
        owners=(a, b), world_id="world-1", branch_id="source",
        external_close_physical=lambda: ExternalPhysicalFence("synthetic", True, ()),
        external_release_physical=lambda _ref: None,
        external_native_rejoin=lambda _self, _server, _old: ExternalRejoin(
            "unused-new-native", True, True, True,
        ),
    )
    b_before = b.retained
    a.retain_memory(proposal)
    save_persistent_cognition(a.files.cognition_file, a.retained)
    assert proposal in a.retained.memories
    assert b.retained == b_before
    cohort.closed = True  # fixture simulates global retiring before the cut

    for name in ("world_nether", "world_the_end"):
        dimension = tmp_path / name
        dimension.mkdir()
        (dimension / "region").mkdir()
        (dimension / "region" / "r.0.0.mca").write_bytes(
            ("synthetic-" + name).encode(),
        )
    cut = capture_retired_resident_typed_world(
        bridge=source_bridge, paper=source_paper,
        store=store, evidence_dir=evidence,
    )
    generation = cut.generation
    inert = tmp_path / "new-inert-fork"
    prepared = _prepare(generation, inert)
    copy = create_execution_copy(
        generation, inert, tmp_path / "new-execution-copy",
        expected_world_id="world-1",
        expected_source_branch_id="source",
        expected_committed_sha256=prepared.source_commit_sha256,
        expected_fork_branch_id=prepared.restored_branch_id,
    )
    # The Stage28 original test helper now uses THIS exact immutable cut,
    # rather than creating a separate fake generation.
    monkeypatch.setattr(
        clock_test, "_source",
        lambda _path, _monkeypatch: copy,
    )
    actual_copy, paper, _world, boot, live_bridge = _clock_context(
        tmp_path, monkeypatch, native_time=123,
    )
    assert actual_copy is copy
    world, links = _link(copy, paper, boot, live_bridge, monkeypatch)
    eligible = stage28_require_fresh_l1_eligibility(
        copy.recovered.plan, world=world,
        logins=tuple(live_bridge.last_login_evidence[s] for s in ("A", "B")),
        links=links, boot=boot, idle=_idle(),
    )
    owner = live_bridge.owners["A"]
    probe = _probe("new-session-A", 12, "c1-fresh-probe-A", 123, 4.5)
    owner.accept_rejoined_worldbody(probe, request_id=probe.request_id)
    return dict(
        source_generation=generation, copy=copy, eligibility=eligible,
        boot=boot, original_self_id="A", memory_id=proposal.memory_id,
        new_probe=probe,
    ), exp, live_bridge, b_before


def test_one_original_typed_world_a_b_cut_retains_c1_across_fork_and_fresh_l1(
    tmp_path, monkeypatch,
):
    args, exp, bridge, b_before = _case(tmp_path, monkeypatch)
    witness = verify_c1_across_stage28_typed_epoch(**args)
    assert witness.historical_memory_retained
    assert witness.new_l1_reassessment_required
    assert not witness.physical_action_issue_authorized
    assert not witness.real_historical_world_action_attested
    assert witness.generation_id == args["source_generation"].name
    assert witness.original_native_session_id == "native-retired-A"
    assert witness.new_native_session_id == "new-session-A"
    assert witness.new_world_epoch == 1
    a = bridge.owners["A"]
    assert len(a.retained.memories) == 1
    assert len(bridge.owners["B"].retained.memories) == len(b_before.memories) == 0

    candidate = _candidate(exp)
    scope = ScopeRef("A", "new-session-A")
    cue = CurrentCue(
        scope=scope, key="visible-surface", value="stone",
        status=EpistemicStatus.OBSERVED,
        source_revision_refs=("new-native-epoch-1",),
        provenance=(args["new_probe"].provenance,),
    )
    # C2 accepted revision is SYNTHETIC here, not an actual L2 update.
    retained = RetainedRevisionRead(
        proposal_ref="synthetic-c2", semantic_owner_ref="owner-A",
        previous_revision=4, committed_revision=5,
        accepted=True, provenance=P,
    )
    choices = (
        BoundedChoice("1", "original pre-bound MOVE"),
        BoundedChoice("2", "original DEFER"),
    )
    opts = dict(
        candidate=candidate, retained=retained, current_scope=scope,
        current_source_revision_refs=("new-native-epoch-1",),
        cues=(cue,), choice_set=choices, current_owner_revision=5,
        viability_confirmed=True, cost_budget_ns=20,
    )
    # Same original post-fork owner, with memory read masked vs present:
    # only the read-only C3 hint changes; there is no Gemma selection yet.
    masked = replace(a.retained, memories=())
    assert c3_shadow_l1_context(masked, **opts) == (choices, None)
    unchanged, hint = c3_shadow_l1_context(a.retained, **opts)
    assert unchanged == choices and hint is not None
    assert "L1_RETAINED_REUSE" in hint.value_json
    assert a.retained.memories[0].memory_id == exp.memory_id


@pytest.mark.parametrize("fault", [
    "wrong-session", "foreign-self", "stale-probe", "no-l1",
    "other-world", "old-boot", "wrong-memory", "tampered-copy",
    "tampered-source",
])
def test_original_typed_generation_or_current_native_mutation_holds(
    tmp_path, monkeypatch, fault,
):
    args, _exp, _bridge, _ = _case(tmp_path, monkeypatch)
    if fault == "wrong-session":
        args["eligibility"] = replace(
            args["eligibility"], native_sessions=(
                ("A", "fake-new-session"), ("B", "new-session-B"),
            ),
        )
    elif fault == "foreign-self":
        args["original_self_id"] = "B"
    elif fault == "stale-probe":
        args["new_probe"] = replace(
            args["new_probe"], seq=args["new_probe"].seq - 1,
        )
    elif fault == "no-l1":
        args["eligibility"] = replace(
            args["eligibility"], l1_reevaluation_eligible=False,
        )
    elif fault == "other-world":
        args["eligibility"] = replace(
            args["eligibility"], world_id="different-world",
        )
    elif fault == "old-boot":
        args["boot"] = replace(args["boot"], paper_boot_id="old-fork-boot")
    elif fault == "wrong-memory":
        args["memory_id"] = "c1-skillrun:" + "f" * 64
    elif fault == "tampered-copy":
        file = args["copy"].directory / "selves" / "A" / "cognition.json"
        file.write_bytes(b"tampered-restored-c1")
    else:
        file = args["source_generation"] / "selves" / "A" / "cognition.json"
        file.write_bytes(b"tampered-source-c1")
    with pytest.raises(C1TypedCheckpointHold):
        verify_c1_across_stage28_typed_epoch(**args)


def test_world_only_checkpoint_cannot_substitute_for_typed_generation(
    tmp_path, monkeypatch,
):
    args, _exp, _bridge, _ = _case(tmp_path, monkeypatch)
    empty = tmp_path / "world-only-generation"
    empty.mkdir()
    (empty / "WORLD_ONLY_COMMITTED.json").write_text("{}")
    with pytest.raises(C1TypedCheckpointHold):
        verify_c1_across_stage28_typed_epoch(
            **(args | {"source_generation": empty}),
        )
