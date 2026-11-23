"""Q independent R2-0 adversarial probes on a separate exact target worktree.

Q-owned test never imports the R2 module into the Q checkout. GitHub Actions
copies this into a runner temp path and provides the exact R2-0 target on
PYTHONPATH. All original Owner/Paper/native fixtures are CPU synthetic.
"""
# ruff: noqa: I001 -- the R2-0 source exists only on the pinned target branch.
from __future__ import annotations

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


def _snapshot(bridge):
    return (
        _files(bridge),
        {sid: (o.retained, tuple(o.intent.events), dict(o.skills),
               frozenset(o.pending_questions), o.pattern_registry)
         for sid, o in bridge.owners.items()},
        dict(bridge.cognitive_work._coverage_adoption_turns),
    )


@pytest.mark.parametrize("sid", ("A", "B"))
def test_q_r2_0_original_owners_have_one_read_only_present_boundary(
    tmp_path, monkeypatch, sid,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    before = _snapshot(bridge)
    params = _args(case, sid)
    legacy = bridge.cognitive_work.read_present_cpu(**params)
    current = read_original_owner_current(**params, signals=legacy.present.signals)
    assert legacy_current_mismatch_codes(legacy, current) == ()
    comparison = compare_original_owner_r1_shadow(**params)
    assert comparison.status is R1ShadowStatus.MATCH
    assert comparison.context is not None
    assert r1_shadow_is_live(
        comparison, bridge=bridge, boot=case[2], world=case[3], links=case[4],
    )
    assert comparison.l1_input_switched is False
    assert comparison.physical_authorized is False
    assert comparison.memory_adopted is False
    assert bridge.owners[sid] is bridge.cognitive_work.owners[sid]
    assert _snapshot(bridge) == before


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
def test_q_r2_0_every_present_difference_invalidates_initial_and_cached(
    tmp_path, monkeypatch, field, expected,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    params = _args(case)
    clean = compare_original_owner_r1_shadow(**params)
    assert clean.status is R1ShadowStatus.MATCH
    old_read = bridge.cognitive_work.read_present_cpu
    a = old_read(**params)
    b = old_read(**_args(case, "B"))
    current = read_original_owner_current(**params, signals=a.present.signals)
    before = _snapshot(bridge)
    if field == "source":
        forged = replace(a, source=b.source)
    elif field == "schema":
        forged = replace(a, schema=b.schema)
    elif field in ("scope", "revisions"):
        forged = replace(a, present=replace(
            a.present, three_self=b.present.three_self,
        ))
    elif field == "frame":
        forged = replace(a, present=replace(a.present, frame_revision=71))
    elif field == "registry":
        forged = replace(a, present=replace(a.present, registry_revision=72))
    elif field == "signals":
        forged = replace(a, present=replace(a.present, signals=()))
    elif field == "need":
        forged = replace(a, present=replace(a.present, need_refs=("q-forged-need",)))
    else:
        forged = replace(a, present=replace(
            a.present, attention_refs=("q-forged-attention",),
        ))
    assert expected in legacy_current_mismatch_codes(forged, current)

    def substituted(**kwargs):
        native = old_read(**kwargs)
        return forged if kwargs["self_id"] == "A" else native

    monkeypatch.setattr(bridge.cognitive_work, "read_present_cpu", substituted)
    changed = compare_original_owner_r1_shadow(**params)
    if field == "signals":
        # Initial CURRENT inherits signals from the same qualified legacy
        # Present. A changed but otherwise eligible selector can therefore
        # become a fresh CURRENT; comparing it to the *previous* independent
        # CURRENT above must still detect a difference. Cached old CURRENT
        # must be rejected, but the initial R1 reader cannot invent a second
        # canonical Schema-signal source.
        assert changed.status is R1ShadowStatus.MATCH
        assert changed.context is not None
        assert changed.context.current.signals == ()
    else:
        assert changed.status is R1ShadowStatus.MISMATCH
        assert expected in changed.mismatch_codes
    assert not r1_shadow_is_live(
        clean, bridge=bridge, boot=case[2], world=case[3], links=case[4],
    )
    assert _snapshot(bridge) == before


@pytest.mark.parametrize(("legacy", "current"), (
    (object(), object()),
    (None, None),
    ("foreign", "foreign"),
))
def test_q_r2_0_invalid_inputs_never_compare_equal(legacy, current):
    assert legacy_current_mismatch_codes(
        legacy, current,
    ) == ("LEGACY_OR_CURRENT_TYPE_INVALID",)


def test_q_r2_0_diagnostics_are_not_owner_or_physical_admission():
    assert len(R2_LEGACY_CURRENT_DIAGNOSTIC_CODES) == 9
    assert len(set(R2_LEGACY_CURRENT_DIAGNOSTIC_CODES)) == 9
    for forbidden in ("issue_action", "adopt", "commit_memory", "submit_model"):
        assert not hasattr(legacy_current_mismatch_codes, forbidden)
