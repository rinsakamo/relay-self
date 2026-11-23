"""Normal original resident CPU Present/Inquiry after actual Bridge A reJOIN.

Synthetic Native decoder and owned Paper process fixture; not real-world qualification.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, replace

import pytest

import relay_self.bd1b_owner_present_dev as projection
from relay_self.b_np1b_continuing_b_composite_dev import ContinuingCompositeHold
from relay_self.b_np1b_rejoin_composite_source_dev import RejoinCompositeHold
from relay_self.b_np1b_rejoin_present_dev import RejoinedOwnerSource
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkError
from test_b_np1b_current_composite_source_dev import current as current_fixture
from test_b_np1b_fresh_native_update_dev import files
from test_b_np1b_owner_bound_rejoin_dev import rejoined as rejoined


@pytest.fixture
def rejoined_present(request):
    """Reuse original Fresh Schema bootstrap performed before first Bridge login."""
    assert current_fixture is not None and rejoined is not None
    f = request.getfixturevalue("rejoined")
    assert all(
        f[0].cognitive.present_schema(sid).revision
        == f[0].owners[sid].pattern_registry.revision
        for sid in ("A", "B")
    )
    return f


def arguments(rejoined_present):
    f, initial, _, old_composite, _, _, _ = rejoined_present
    return dict(
        bridge=f.bridge, self_id="A", initial_receipts=initial,
        historical_composite=old_composite,
    )


def _state(f):
    return {sid: (owner.retained, owner.intent, owner.pattern_registry,
                  dict(owner.skills), set(owner.pending_questions))
            for sid, owner in f.owners.items()}


def test_original_normal_present_inquiry_survive_bridge_rejoin_read_only(rejoined_present):
    f, initial, _, old_composite, old_session, _, b_before = rejoined_present
    args = arguments(rejoined_present)
    before_files = files(f)
    before_state = _state(f)

    source = f.cognitive.read_present_cpu(**args)
    assert type(source.source) is RejoinedOwnerSource
    composite = source.source.composite_receipt
    assert composite.native_session_id != old_session
    assert composite.old_native_session_id == old_session
    assert composite.native_session_id == f.bridge.sessions["A"].started.session_id
    assert composite.native_request_id == f.owners["A"].current_worldbody_observation.request_id
    assert composite.paper_revision != old_composite.paper_revision
    assert composite.native_revision != old_composite.native_revision
    assert source.source.native_probe_source_ref == composite.native_source_ref
    assert source.source.native_world_time_tick == composite.native_world_time
    assert source.source.paper_log_sha256 == composite.paper_log_sha256
    assert source.source.resident_epoch == composite.resident_epoch
    assert source.schema == f.cognitive.present_schema("A")
    assert source.present.frame_revision == composite.resident_epoch
    assert source.present.three_self.scope.self_id == "A"
    refs = source.present.three_self.source_revision_refs
    assert len(refs) == 3
    assert refs[0].startswith("native:" + composite.native_session_id)
    assert refs[1].startswith("paper:" + composite.paper_session_id)
    assert refs[2] == "composite:rejoin:" + composite.composite_revision
    assert source.exploration_need is not None
    assert source.exploration_need.signal.source_revision_refs == refs
    assert source.present.signals == (source.exploration_need.signal,)
    assert source.no_candidate_reason == "NO_VERIFIED_ACTION_CATALOG"

    again = f.cognitive.read_present_cpu(**args)
    inquiry = f.cognitive.read_coverage_inquiry_cpu(**args)
    assert again == source
    assert inquiry is not None
    assert inquiry.self_id == "A"
    assert inquiry.source_revision_refs == refs
    assert inquiry.coverage_claim_ref == source.exploration_need.basis[0].present_ref
    assert inquiry == f.cognitive.read_coverage_inquiry_cpu(**args)
    assert not hasattr(inquiry, "target")
    assert not hasattr(inquiry, "action_refs")
    assert f.owners["B"].current_worldbody_observation is b_before[1]
    assert f.cognitive.current_scope("B") == b_before[2]
    assert initial[0].native_session_id == old_session
    assert old_composite.native_session_id == old_session
    assert asdict(old_composite)["initial_receipt_ref"] != composite.composite_revision
    assert files(f) == before_files
    assert _state(f) == before_state


@pytest.mark.parametrize("variant", ["none", "initial_only", "old_only", "mix_boot",
                                      "mix_world", "mix_links", "foreign_self"])
def test_no_implicit_legacy_fallback_or_foreign_receipt(rejoined_present, variant):
    f = rejoined_present[0]
    args = arguments(rejoined_present)
    if variant == "none":
        args.pop("initial_receipts")
        args.pop("historical_composite")
    elif variant == "initial_only":
        args.pop("historical_composite")
    elif variant == "old_only":
        args.pop("initial_receipts")
    elif variant in ("mix_boot", "mix_world", "mix_links"):
        args[variant.removeprefix("mix_")] = object()
    else:
        args["self_id"] = "B"
    with pytest.raises((ResidentCognitiveWorkError, RejoinCompositeHold,
                        ContinuingCompositeHold, ValueError)):
        f.cognitive.read_present_cpu(**args)
    with pytest.raises((ResidentCognitiveWorkError, RejoinCompositeHold,
                        ContinuingCompositeHold, ValueError)):
        f.cognitive.read_coverage_inquiry_cpu(**args)


@pytest.mark.parametrize("fault", [
    "native_observation", "native_request", "resident_epoch", "world_epoch",
    "logout", "paper_pid", "paper_log", "old_receipt", "schema_registry",
    "schema_missing", "owner_swap", "session_b", "old_session_reuse",
])
def test_rejoin_cpu_present_and_inquiry_fail_closed(rejoined_present, monkeypatch, fault):
    f = rejoined_present[0]
    args = arguments(rejoined_present)
    bridge = f.bridge
    if fault == "native_observation":
        bridge.owners["A"].current_worldbody_observation = replace(
            bridge.owners["A"].current_worldbody_observation,
            seq=bridge.owners["A"].current_worldbody_observation.seq + 1,
        )
    elif fault == "native_request":
        bridge.last_login_evidence["A"] = replace(
            bridge.last_login_evidence["A"], observation_ref="foreign-request",
        )
    elif fault == "resident_epoch":
        f.cognitive._states["A"].epoch += 1
    elif fault == "world_epoch":
        f.cognitive._states["A"].world_epoch += 1
    elif fault == "logout":
        asyncio.run(bridge.logout("A"))
    elif fault == "paper_pid":
        process = f.paper._assert_owned
        monkeypatch.setattr(
            f.paper, "_assert_owned",
            lambda: type("ChangedPaper", (), {"pid": process().pid + 1})(),
        )
    elif fault == "paper_log":
        contents = f.paper._log_path.read_text()
        f.paper._log_path.write_text(
            contents.replace("P0D_TICK_ACK nonce=88888888", "BAD_TICK_ACK nonce=88888888"),
        )
    elif fault == "old_receipt":
        args["historical_composite"] = replace(
            args["historical_composite"], native_request_id="not-original",
        )
    elif fault == "schema_registry":
        owner = f.owners["A"]
        owner.pattern_registry = replace(owner.pattern_registry,
                                         revision=owner.pattern_registry.revision + 1)
    elif fault == "schema_missing":
        del f.cognitive._present_schemas["A"]
    elif fault == "owner_swap":
        bridge.owners["A"] = bridge.owners["B"]
    elif fault == "session_b":
        bridge.sessions["B"]._started = replace(
            bridge.sessions["B"].started, session_id="foreign-b",
        )
    else:
        bridge.forbidden_native_sessions = frozenset()
    with pytest.raises((RuntimeError, ValueError)):
        f.cognitive.read_present_cpu(**args)
    with pytest.raises((RuntimeError, ValueError)):
        f.cognitive.read_coverage_inquiry_cpu(**args)


def test_old_projected_source_rejected_after_later_logout(rejoined_present):
    f = rejoined_present[0]
    args = arguments(rejoined_present)
    first = f.cognitive.read_present_cpu(**args)
    original = first.source.composite_receipt
    asyncio.run(f.bridge.logout("A"))
    with pytest.raises(RuntimeError):
        f.cognitive.read_present_cpu(**args)
    with pytest.raises(RuntimeError):
        f.cognitive.read_coverage_inquiry_cpu(**args)
    assert first.source.composite_receipt == original


def test_projection_cannot_publish_changed_schema_or_native(rejoined_present, monkeypatch):
    f = rejoined_present[0]
    args = arguments(rejoined_present)
    before = files(f)
    initial_state = _state(f)
    old = projection.project_present_frame

    def change_after_project(**kwargs):
        result = old(**kwargs)
        f.cognitive._states["A"].epoch += 1
        return result

    monkeypatch.setattr(projection, "project_present_frame", change_after_project)
    with pytest.raises(RuntimeError):
        f.cognitive.read_present_cpu(**args)
    assert files(f) == before
    assert _state(f) == initial_state
