"""R2-0 shared Present compatibility: original Owner boundaries, no new writer.

These tests use the original B/A CPU fixtures only. No World, GPU, L1 issue,
Native/Paper launch, persistence adoption or Physical Action is performed.
"""
from dataclasses import replace

import pytest

from relay_self.r0_cognitive_context_dev import read_original_owner_current
from relay_self.r1_owner_context_shadow_dev import (
    R1ShadowStatus,
    compare_original_owner_r1_shadow,
    r1_shadow_is_live,
)
from relay_self.r2_present_responsibility_boundary_dev import (
    R2_LEGACY_CURRENT_DIAGNOSTIC_CODES,
    legacy_current_mismatch_codes,
)
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files


def _args(case, sid="A"):
    _, bridge, boot, world, links, _ = case
    return dict(bridge=bridge, boot=boot, world=world, links=links, self_id=sid)


def _original(case, sid="A"):
    params = _args(case, sid)
    legacy = case[1].cognitive_work.read_present_cpu(**params)
    current = read_original_owner_current(
        **params, signals=legacy.present.signals,
    )
    return legacy, current


def _snapshot(case):
    bridge = case[1]
    return (
        _files(bridge),
        {sid: (owner.retained, owner.intent.events, dict(owner.skills),
               set(owner.pending_questions), owner.pattern_registry)
         for sid, owner in bridge.owners.items()},
        dict(bridge.cognitive_work._coverage_adoption_turns),
    )


@pytest.mark.parametrize("sid", ("A", "B"))
def test_r2_original_a_b_legacy_and_current_have_no_duplicate_owner_or_side_effect(
    tmp_path, monkeypatch, sid,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    before = _snapshot(case)
    legacy, current = _original(case, sid)
    assert legacy_current_mismatch_codes(legacy, current) == ()
    report = compare_original_owner_r1_shadow(**_args(case, sid))
    assert report.status is R1ShadowStatus.MATCH
    assert r1_shadow_is_live(
        report, bridge=case[1], boot=case[2], world=case[3], links=case[4],
    )
    assert report.l1_input_switched is False
    assert report.physical_authorized is False
    assert report.memory_adopted is False
    assert case[1].owners[sid] is case[1].cognitive_work.owners[sid]
    assert before == _snapshot(case)


@pytest.mark.parametrize(("field", "expected"), (
    ("source", "LEGACY_SOURCE_DIFFERS_FROM_R1_CURRENT"),
    ("schema", "LEGACY_SCHEMA_DIFFERS_FROM_R1_CURRENT"),
    ("scope", "LEGACY_SELF_OR_WORLD_SCOPE_MISMATCH"),
    ("revisions", "LEGACY_NATIVE_PAPER_REVISION_MISMATCH"),
    ("frame", "LEGACY_OWNER_EPOCH_MISMATCH"),
    ("registry", "LEGACY_REGISTRY_REVISION_MISMATCH"),
    ("signals", "LEGACY_SCHEMA_SIGNAL_MISMATCH"),
    ("need", "LEGACY_NEED_REFERENCE_MISMATCH"),
    ("attention", "LEGACY_ATTENTION_REFERENCE_MISMATCH"),
))
def test_r2_all_nine_legacy_present_dimensions_refuse_drift(
    tmp_path, monkeypatch, field, expected,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    before = _snapshot(case)
    a, current = _original(case, "A")
    b, _ = _original(case, "B")
    if field == "source":
        changed = replace(a, source=b.source)
    elif field == "schema":
        changed = replace(a, schema=b.schema)
    elif field in ("scope", "revisions"):
        changed = replace(a, present=replace(
            a.present, three_self=b.present.three_self,
        ))
    elif field == "frame":
        changed = replace(a, present=replace(a.present, frame_revision=999))
    elif field == "registry":
        changed = replace(a, present=replace(a.present, registry_revision=998))
    elif field == "signals":
        changed = replace(a, present=replace(a.present, signals=()))
    elif field == "need":
        changed = replace(a, present=replace(
            a.present, need_refs=("stale-original-need",),
        ))
    else:
        changed = replace(a, present=replace(
            a.present, attention_refs=("stale-original-attention",),
        ))
    codes = legacy_current_mismatch_codes(changed, current)
    assert expected in codes
    assert set(codes).issubset(set(R2_LEGACY_CURRENT_DIAGNOSTIC_CODES))
    assert before == _snapshot(case)


@pytest.mark.parametrize("bad_legacy,bad_current", (
    (None, None),
    (object(), None),
    ("untyped-legacy", "untyped-current"),
))
def test_r2_untyped_caller_cannot_obtain_compatibility(bad_legacy, bad_current):
    assert legacy_current_mismatch_codes(
        bad_legacy, bad_current,
    ) == ("LEGACY_OR_CURRENT_TYPE_INVALID",)


def test_r2_compatibility_returns_only_diagnostics_no_admission():
    assert len(R2_LEGACY_CURRENT_DIAGNOSTIC_CODES) == 9
    assert len(set(R2_LEGACY_CURRENT_DIAGNOSTIC_CODES)) == 9
    assert not hasattr(legacy_current_mismatch_codes, "commit")
    assert not hasattr(legacy_current_mismatch_codes, "issue_action")
    assert not hasattr(legacy_current_mismatch_codes, "write_memory")
