"""Synthetic original-owner S49 WAIT fence: never full-tick P1 authority."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_wait_owner_fence_dev import (
    S49WaitFenceDev,
    review_s49_owner_wait_fence,
)
from relay_self.action_supervision import ActionSupervisor

SESSION = "native-one-session"
MARKER = "action-session-marker"
WORLD = "paper-world-uuid"


def source(*, first_tick: int = 61):
    owner = object()
    other = object()
    supervisor = ActionSupervisor()
    fence = S49WaitFenceDev(
        owner=owner, supervisor=supervisor, session_id=SESSION,
        marker_id=MARKER, world=WORLD,
    )
    fence.arm(
        owner, closed_action_id="prior-move",
        terminal_outcome_ref="owned-outcome-original",
        controls_clear_ref="owned-clear-readback-original",
    )
    for tick in range(first_tick, first_tick + 8):
        fence.observe_paper_tick(
            owner, world_tick=tick, source_ref=f"paper-sample-{tick}",
        )
    return fence, owner, other, supervisor


def review(rows):
    return review_s49_owner_wait_fence(
        rows, session_id=SESSION, marker_id=MARKER, world=WORLD,
        first_world_tick=61, last_world_tick=68,
    )


def test_owner_fence_samples_and_seals_but_cannot_mint_p1_wait():
    fence, owner, _, _ = source()
    rows = fence.seal(owner, seal_source_ref="local-fence-seal")
    result = review(rows)
    assert result["same_owner_local_action_window_screened"]
    assert result["global_issuer_absence"] == "NOT_ATTESTED"
    assert result["paper_world_clock_bound_to_owner"] == "NOT_ATTESTED"
    assert result["whole_tick_physical_inactivity"] == "NOT_ATTESTED"
    assert result["wait_interval_ref"] is None
    assert result["wait_ticks_admitted"] == 0
    assert result["p1_fatigue_recovered"] == 0.0
    assert result["original_source_authenticated_by_r"] is False
    assert not result["science_go"]
    fence.before_issue(owner, action_id="next-action", attempted_source_ref="next")


def test_action_attempt_while_fenced_invalidates_source():
    owner = object()
    fence = S49WaitFenceDev(
        owner=owner, supervisor=ActionSupervisor(), session_id=SESSION,
        marker_id=MARKER, world=WORLD,
    )
    fence.arm(owner, closed_action_id="prior",
              terminal_outcome_ref="outcome", controls_clear_ref="controls")
    with pytest.raises(BoundaryRejected, match="Action attempted"):
        fence.before_issue(owner, action_id="move-during-wait",
                           attempted_source_ref="issued-attempt")
    assert fence.phase == "ABORTED"
    assert fence.original_rows[-1]["kind"] == "BLOCKED_ISSUE"
    with pytest.raises(BoundaryRejected):
        fence.seal(owner, seal_source_ref="false-seal")


def test_foreign_owner_fails_closed():
    fence, owner, foreign, _ = source()
    with pytest.raises(BoundaryRejected, match="owner"):
        fence.seal(foreign, seal_source_ref="other")
    assert fence.phase == "ABORTED"
    with pytest.raises(BoundaryRejected):
        fence.seal(owner, seal_source_ref="after-foreign")


@pytest.mark.parametrize("first", [0, -1, True])
def test_invalid_native_tick_fails_closed(first):
    owner = object()
    f = S49WaitFenceDev(
        owner=owner, supervisor=ActionSupervisor(), session_id=SESSION,
        marker_id=MARKER, world=WORLD,
    )
    f.arm(owner, closed_action_id="move", terminal_outcome_ref="outcome",
          controls_clear_ref="clear")
    with pytest.raises(BoundaryRejected):
        f.observe_paper_tick(owner, world_tick=first, source_ref="sample")
    assert f.phase == "ABORTED"


def test_lost_tick_duplicate_or_overlong_window_is_rejected():
    for ticks in ([61, 62, 64], [61, 61], list(range(61, 70))):
        owner = object()
        fence = S49WaitFenceDev(
            owner=owner, supervisor=ActionSupervisor(), session_id=SESSION,
            marker_id=MARKER, world=WORLD,
        )
        fence.arm(owner, closed_action_id="prior",
                  terminal_outcome_ref="outcome", controls_clear_ref="controls")
        with pytest.raises(BoundaryRejected):
            for tick in ticks:
                fence.observe_paper_tick(owner, world_tick=tick,
                                         source_ref=f"tick-{tick}")
            fence.seal(owner, seal_source_ref="seal")
        assert fence.phase == "ABORTED"


def test_partial_window_cannot_seal():
    fence, owner, _, _ = source()
    partial = list(fence.original_rows[:-1])
    with pytest.raises(BoundaryRejected):
        review(partial)
    with pytest.raises(BoundaryRejected):
        review(list(fence.original_rows))


@pytest.mark.parametrize(("idx", "field", "value"), [
    (0, "action_id", None),
    (0, "source_ref", ""),
    (0, "controls_clear_ref", ""),
    (0, "kind", "PAPER_SAMPLE"),
    (1, "world_tick", 62),
    (3, "ordinal", 2),
    (7, "session_id", "foreign"),
    (8, "marker_id", "other"),
    (9, "world_tick", 69),
    (9, "source", "R_QUALIFIED"),
    (9, "action_id", "hidden-action"),
    (9, "kind", "BLOCKED_ISSUE"),
])
def test_any_spliced_fence_row_fails_closed(idx, field, value):
    fence, owner, _, _ = source()
    rows = list(fence.seal(owner, seal_source_ref="seal"))
    rows = deepcopy(rows)
    rows[idx][field] = value
    with pytest.raises(BoundaryRejected):
        review(rows)


def test_original_rows_are_defensive_copies():
    fence, owner, _, _ = source()
    rows = list(fence.seal(owner, seal_source_ref="seal"))
    rows[0]["action_id"] = "tampered"
    assert review(fence.original_rows)["owner_original_rows"] == 10
