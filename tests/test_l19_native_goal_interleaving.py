"""L19 source-shaped S49 native asynchronous Goal-window compatibility.

All fixtures are synthetic source-shaped bytes, never a Minecraft run. Entity
updates are visible native observations, NOT an absence-of-intervention claim.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

import test_l13_independent_goal_receipt as l13
import test_l15_s49_original_goal_preflight as l15
import test_l16_s49_first_action_original_capture as l16
from adapters.mineflayer.l16_first_action_goal_originals import (
    L16SourceRejected,
    inspect_l16_first_action_prefix,
)
from relay_self.l14_original_bridge_goal_window import (
    L14SourceRejected,
    audit_l14_native_goal_window,
)
from relay_self.l17_first_action_goal_handoff import (
    L17IndependentInputs,
    L17HandoffStatus,
    review_l17_first_action_goal,
)


def interleaved(*, insert_kind="entities", count=2):
    """Genuine Mineflayer-shaped stream with extra source seqs.

    One intervening native event after S16 observation; one after first Goal
    probe. Outbound Goal probes remain the exact two original requests.
    """
    args = l16.fixture()
    original = l15.s49_original_source()
    rows = [json.loads(line) for line in args["received_original"].splitlines()]
    first_source = dict(rows[4])
    if insert_kind == "entities":
        first_source["kind"] = "entities"
        first_source.pop("request_id", None)
    elif insert_kind == "effect":
        first_source = {
            "type": "effect_result", "session_id": args["session_id"],
            "action_id": "foreign-action", "effect": "set_control",
            "result": "applied", "error": None,
        }
    elif insert_kind == "hurt":
        first_source = {
            "type": "entity_hurt", "session_id": args["session_id"],
            "entity_id": 7, "source_entity_id": 8, "actor_entity_id": 7,
        }
    elif insert_kind == "shutdown":
        first_source = {
            "type": "connection_end", "session_id": args["session_id"],
            "reason": "synthetic-bridge-end",
        }
    elif insert_kind == "probe":
        first_source["kind"] = "probe"
        first_source["request_id"] = "foreign-unrequested-probe"
    else:
        raise AssertionError(insert_kind)
    # Keep the first Goal probe (original seq5), insert one after Action
    # and another after Goal. Extend a contiguous native stream.
    new = [*rows[:5]]
    for _ in range(count):
        new.append(dict(first_source))
    new.append(rows[5])
    new.append(dict(first_source))
    new.append(rows[6])
    for seq, d in enumerate(new):
        d["seq"] = seq
    first_seq = 5 + count
    second_seq = first_seq + 2
    args["received_original"] = b"".join(l13.raw(x) for x in new)
    args["first_probe_seq"] = first_seq
    args["second_probe_seq"] = second_seq
    args["s7_receipt"] = l15.l14._index(
        args["received_original"], args["sent_original"],
    )
    raw_goal = json.loads(original["item"].raw_external_goal)
    raw_goal["goal_observed_seq"] = first_seq
    goal = l13.raw(raw_goal)
    item = replace(original["item"], raw_external_goal=goal)
    admission = replace(
        original["admission"],
        admitted_goal_sha256=frozenset({hashlib.sha256(goal).hexdigest()}),
    )
    # The L13 Action original stays bound to the same native before and S16
    # after original (only post-S16 frames were added).
    native = dict(
        received_original=args["received_original"],
        sent_original=args["sent_original"],
        s7_source_receipt=args["s7_receipt"],
        external_criterion_original=original["external_criterion_original"],
        independently_admitted_criterion_sha256=original[
            "independently_admitted_criterion_sha256"
        ],
        item=item, admission=admission, current=original["current"],
    )
    external = L17IndependentInputs(
        criterion_original=native["external_criterion_original"],
        admitted_criterion_sha256=native[
            "independently_admitted_criterion_sha256"
        ],
        receipt_triplet=item,
        admission=admission,
        current=original["current"],
    )
    return args, native, external


@pytest.mark.parametrize("count", [1, 2, 8, 15])
def test_interleaved_native_entity_updates_are_visible_but_not_physical_learning(count):
    args, native, external = interleaved(count=count)
    l16_source = inspect_l16_first_action_prefix(**args)
    l14_source = audit_l14_native_goal_window(**native)
    l17_source = review_l17_first_action_goal(**args, external=external)
    assert l16_source.observed_goal_status == "REACHED"
    assert l16_source.goal_probe_seq == 5 + count
    assert l16_source.second_goal_probe_seq == 7 + count
    assert l14_source.goal_probe_seq == l16_source.goal_probe_seq
    assert l14_source.second_stable_probe_seq == l16_source.second_goal_probe_seq
    assert l17_source.status is L17HandoffStatus.SOURCE_SHAPED_L10_CANDIDATE
    assert l17_source.l10_previous_epoch_candidate_available
    assert not l17_source.l14_independent_goal.actual_intervention_absence_proven
    assert not l17_source.l14_independent_goal.independent_physical_goal_authenticated
    assert l17_source.qualified_real_training_pairs == 0
    assert l17_source.s10_updates == l17_source.s11_habit_grants == 0


@pytest.mark.parametrize("kind", ["effect", "hurt", "shutdown", "probe"])
def test_post_s16_nonentity_event_is_not_explained_away(kind):
    args, native, external = interleaved(insert_kind=kind)
    with pytest.raises((ValueError, TypeError)):
        inspect_l16_first_action_prefix(**args)
    with pytest.raises((ValueError, TypeError)):
        audit_l14_native_goal_window(**native)
    with pytest.raises((ValueError, TypeError)):
        review_l17_first_action_goal(**args, external=external)


def test_excessive_intervening_frames_fail_closed():
    args, native, external = interleaved(count=16)
    assert args["second_probe_seq"] - args["first_probe_seq"] == 2
    # Insert sixteen between the Goal probes (17 apart) rather than before.
    rows = [json.loads(x) for x in args["received_original"].splitlines()]
    event = dict(rows[-2])
    assert event["kind"] == "entities"
    for _ in range(15):
        rows.insert(-1, dict(event))
    for i, d in enumerate(rows):
        d["seq"] = i
    args["received_original"] = b"".join(l13.raw(x) for x in rows)
    args["second_probe_seq"] = len(rows) - 1
    args["s7_receipt"] = l15.l14._index(
        args["received_original"], args["sent_original"],
    )
    native["received_original"] = args["received_original"]
    native["s7_source_receipt"] = args["s7_receipt"]
    with pytest.raises(L16SourceRejected):
        inspect_l16_first_action_prefix(**args)
    with pytest.raises(L14SourceRejected):
        audit_l14_native_goal_window(**native)


def test_gap_in_native_sequence_is_not_a_benign_entity_update():
    args, native, _ = interleaved()
    rows = [json.loads(x) for x in args["received_original"].splitlines()]
    rows[5]["seq"] = 99
    args["received_original"] = b"".join(l13.raw(x) for x in rows)
    args["s7_receipt"] = l15.l14._index(
        args["received_original"], args["sent_original"],
    )
    native["received_original"] = args["received_original"]
    native["s7_source_receipt"] = args["s7_receipt"]
    with pytest.raises(L16SourceRejected):
        inspect_l16_first_action_prefix(**args)
    with pytest.raises((L14SourceRejected, ValueError)):
        audit_l14_native_goal_window(**native)


def test_interleaved_without_external_stays_waiting_even_if_reached():
    args, _, _ = interleaved()
    r = review_l17_first_action_goal(**args)
    assert r.status is L17HandoffStatus.WAITING_FOR_EXTERNAL_ORIGINALS
    assert r.l16_first_action.observed_goal_status == "REACHED"
    assert not r.l10_previous_epoch_candidate_available
    assert r.qualified_real_training_pairs == r.s10_updates == 0
