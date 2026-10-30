"""L13 offline source-bound independent Goal triplets, never live evidence."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path

import pytest

import test_experience_bridge as l1
import test_l10_world_body_cue_learning as l10
from adapters.mineflayer.l12_archived_action_progress_no_reward_dev import (
    audit_l12_real_action_goal_gate,
)
from relay_self.contextual_shadow import ContextualStatus
from relay_self.habit_shadow import GoalSourceAdmission
from relay_self.l10_world_body_cue_learning import (
    evaluate_l10_next_epoch_shadow,
    project_admitted_world_body_cues,
)
from relay_self.l13_independent_goal_receipt import (
    L13IndependentSourceAdmission,
    L13ReceiptRejected,
    L13ReceiptStatus,
    L13ReceiptTriplet,
    join_independent_action_goal_source,
    review_l12_g413_archive_no_per_action_goal,
)
from relay_self.provenance import Provenance


def raw(payload):
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(v):
    return hashlib.sha256(v).hexdigest()


def native_line(native):
    """Source-shaped fixture that is parsed by the real adapter decoder."""
    p = native.observation
    snap = p.snapshot
    c = snap.nearby_entities_coverage
    return raw({
        "type": "observation", "session_id": p.session_id,
        "seq": p.seq, "kind": "probe", "request_id": p.request_id,
        "snapshot": {
            "health": snap.health,
            "food": snap.food,
            "food_saturation": snap.food_saturation,
            "oxygen_level": snap.oxygen_level,
            "position": {
                "x": snap.position.x, "y": snap.position.y,
                "z": snap.position.z,
            },
            "time": (
                None if snap.time is None else {
                    "time_of_day": snap.time.time_of_day,
                    "day": snap.time.day, "is_day": snap.time.is_day,
                }
            ),
            "inventory": [
                {"name": v.name, "count": v.count, "slot": v.slot}
                for v in snap.inventory
            ],
            "nearby_entities": [
                {
                    "id": v.entity_id, "name": v.name,
                    "type": v.entity_type, "distance": v.distance,
                    "position": {
                        "x": v.position.x, "y": v.position.y,
                        "z": v.position.z,
                    },
                }
                for v in snap.nearby_entities
            ],
            "nearby_entities_coverage": {
                "source_scope": c.source_scope,
                "max_distance": c.max_distance,
                "max_entities": c.max_entities,
                "candidate_count": c.candidate_count,
                "truncated": c.truncated,
            },
        },
    })


def fixture(*, result="REACHED", session="old-session", seq=24,
            distance=2.0, food=7.0, action_ref="MOVE_AWAY",
            goal_owner="goal-issuer", current_revision=128,
            action_id=None):
    native, world, body = l10.source(
        distance_m=distance, food=food, session=session, seq=seq,
    )
    aid = action_id or f"source-action-{seq}"
    action, outcome = l1.terminal(
        action_id=aid, session=session, action_ref=action_ref,
    )
    pre = native_line(native)
    a = raw({
        "schema": "L13_S16_TERMINAL_SOURCE_V1",
        "session_id": session, "action_id": aid,
        "binding_id": outcome.binding_id,
        "action_ref": action_ref,
        "pre_probe_sha256": sha(pre),
        "before_seq": seq, "after_seq": seq+1,
        "source_revision": 4,
        "source_status": "executed", "disposition": "outcome",
        "reason_code": outcome.reason_code,
        "world_source": outcome.world_provenance.source,
        "world_reference": outcome.world_provenance.reference,
    })
    g = raw({
        "schema": "L13_EXTERNAL_PER_ACTION_GOAL_V1",
        "session_id": session, "action_id": aid,
        "source_action_sha256": sha(a),
        "source_pre_probe_sha256": sha(pre),
        "action_end_seq": seq+1,
        "goal_observed_seq": seq+2,
        "goal_status": result,
        "criterion_id": "independent-spatial-criterion-001",
        "external_goal_owner_ref": goal_owner,
        "no_intervening_action_attested": True,
    })
    entry = L13ReceiptTriplet(
        native=native, world=world, body=body,
        action=action, outcome=outcome,
        raw_native_probe=pre, raw_s16_action=a, raw_external_goal=g,
        self_id="test-self", source_revision=4,
    )
    admitted = L13IndependentSourceAdmission(
        admitted_present_sha256=frozenset({sha(pre)}),
        admitted_action_sha256=frozenset({sha(a)}),
        admitted_goal_sha256=frozenset({sha(g)}),
        present_owner="native-capture", action_owner="s16-action-owner",
        goal_owner=goal_owner, review_provenance=Provenance(
            "separate-v-review", "synthetic-source-shaped-only",
        ),
    )
    current_native, current_world, current_body = l10.source(
        distance_m=2.0, food=7.0, session="later-current-session", seq=400,
    )
    current = project_admitted_world_body_cues(
        native=current_native, world=current_world, body=current_body,
        owner_self_id="test-self", source_revision=current_revision,
        original_probe_sha256="a"*64,
        admitted_probe_sha256=frozenset({"a"*64}),
    )
    return entry, admitted, current


@pytest.mark.parametrize(("result", "value"), [
    ("REACHED", True), ("NOT_REACHED", False),
])
def test_three_separate_source_byte_owners_create_only_l10_candidate(result, value):
    item, admission, current = fixture(result=result)
    reading = join_independent_action_goal_source(item, admission, current=current)
    assert reading.status is L13ReceiptStatus.SOURCE_SHAPED_GOAL_CANDIDATE
    assert reading.goal_label.goal_reached is value
    assert reading.prior_l10.goal is reading.goal_label
    assert reading.prior_l10.outcome is reading.qualified_episode
    assert reading.prior_l10.witness is reading.witness
    assert reading.qualified_episode.episode.action_ref == "MOVE_AWAY"
    assert reading.qualified_episode.episode.evidence_sha256 == sha(item.raw_s16_action)
    assert reading.witness.original_probe_sha256 == sha(item.raw_native_probe)
    assert reading.goal_label.goal_source_sha256 == sha(item.raw_external_goal)
    assert reading.goal_source_admission.admitted_action_sha256 == frozenset({
        sha(item.raw_s16_action),
    })
    assert reading.goal_source_admission.admitted_goal_sha256 == frozenset({
        sha(item.raw_external_goal),
    })
    assert reading.per_action_goal_source_candidate_count == 1
    assert not reading.real_original_authenticated_by_l13
    assert not reading.goal_improvement_attested
    assert not reading.action_authority
    assert reading.s10_learning_updates == reading.s11_habit_grants == 0
    assert reading.world_reads == reading.new_actions == 0


def test_undetermined_goal_does_not_become_false_label():
    item, admission, current = fixture(result="UNDETERMINED")
    r = join_independent_action_goal_source(item, admission, current=current)
    assert r.status is L13ReceiptStatus.UNKNOWN_NO_GOAL_LABEL
    assert r.qualified_episode is not None  # S16 execution stays factual
    assert r.goal_label is None and r.prior_l10 is None
    assert r.goal_source_admission is None
    assert r.per_action_goal_source_candidate_count == 0


@pytest.mark.parametrize("fault", [
    "present_missing", "action_missing", "goal_missing", "owners_same",
    "review_owner_same", "changed_native_food", "changed_native_session",
    "changed_native_request", "changed_current_self", "current_session_replay",
    "future_revision", "action_id", "action_binding", "action_ref",
    "action_pre_sha", "action_seq", "action_revision", "action_terminal_unknown",
    "action_world_ref", "goal_session", "goal_action_id", "goal_action_sha",
    "goal_present_sha", "goal_action_end_seq", "goal_observed_before",
    "goal_owner", "goal_no_intervening", "goal_status_fake", "goal_criterion",
    "goal_unknown_key", "goal_nonbool_intervening", "invalid_raw_newline",
    "unknown_s16", "wrong_action_state", "same_source_bytes",
    "duplicate_source_json_key",
])
def test_negative_separate_sources_and_no_hindsight_action_goal(fault):
    item, adm, current = fixture()
    if fault == "present_missing":
        adm = replace(adm, admitted_present_sha256=frozenset())
    elif fault == "action_missing":
        adm = replace(adm, admitted_action_sha256=frozenset())
    elif fault == "goal_missing":
        adm = replace(adm, admitted_goal_sha256=frozenset())
    elif fault == "owners_same":
        with pytest.raises(L13ReceiptRejected):
            replace(adm, goal_owner=adm.action_owner)
        return
    elif fault == "review_owner_same":
        with pytest.raises(L13ReceiptRejected):
            replace(adm, review_provenance=Provenance(adm.goal_owner, "fake"))
        return
    elif fault == "changed_current_self":
        current = replace(current, self_id="foreign")
    elif fault == "current_session_replay":
        current = replace(current, session_id=item.native.observation.session_id)
    elif fault == "future_revision":
        current = replace(current, source_revision=4)
    elif fault == "unknown_s16":
        from relay_self.action_outcome import ActionOutcomeDisposition
        item = replace(item, outcome=replace(
            item.outcome, disposition=ActionOutcomeDisposition.UNKNOWN,
        ))
    elif fault == "wrong_action_state":
        item = replace(item, action=replace(
            item.action, action_id="other-action-id",
        ))
    elif fault == "same_source_bytes":
        item = replace(item, raw_external_goal=item.raw_s16_action)
    elif fault == "invalid_raw_newline":
        item = replace(item, raw_native_probe=item.raw_native_probe.rstrip(b"\n"))
    elif fault == "duplicate_source_json_key":
        bad_goal = item.raw_external_goal.replace(
            b'"goal_status":"REACHED",',
            b'"goal_status":"REACHED","goal_status":"REACHED",',
        )
        assert bad_goal != item.raw_external_goal
        item = replace(item, raw_external_goal=bad_goal)
        adm = replace(adm, admitted_goal_sha256=frozenset({sha(bad_goal)}))
    else:
        if fault.startswith("changed_native"):
            data = json.loads(item.raw_native_probe)
            if fault == "changed_native_food":
                data["snapshot"]["food"] = 11
            elif fault == "changed_native_session":
                data["session_id"] = "foreign"
            else:
                data["request_id"] = "forged-id"
            item = replace(item, raw_native_probe=raw(data))
        elif fault.startswith("action_"):
            data = json.loads(item.raw_s16_action)
            changes = {
                "action_id": ("action_id", "other"),
                "action_binding": ("binding_id", "other"),
                "action_ref": ("action_ref", "WAIT"),
                "action_pre_sha": ("pre_probe_sha256", "b"*64),
                "action_seq": ("before_seq", 900),
                "action_revision": ("source_revision", 400),
                "action_terminal_unknown": ("disposition", "unknown"),
                "action_world_ref": ("world_reference", "bad"),
            }
            key, value = changes[fault]
            data[key] = value
            item = replace(item, raw_s16_action=raw(data))
        else:
            data = json.loads(item.raw_external_goal)
            changes = {
                "goal_session": ("session_id", "foreign"),
                "goal_action_id": ("action_id", "other"),
                "goal_action_sha": ("source_action_sha256", "b"*64),
                "goal_present_sha": ("source_pre_probe_sha256", "b"*64),
                "goal_action_end_seq": ("action_end_seq", 900),
                "goal_observed_before": ("goal_observed_seq", 1),
                "goal_owner": ("external_goal_owner_ref", "s16-action-owner"),
                "goal_no_intervening": ("no_intervening_action_attested", False),
                "goal_status_fake": ("goal_status", "REACHED_FROM_MOVEMENT"),
                "goal_criterion": ("criterion_id", ""),
                "goal_unknown_key": ("forged_goal_bonus", True),
                "goal_nonbool_intervening": ("no_intervening_action_attested", "true"),
            }
            key, value = changes[fault]
            data[key] = value
            item = replace(item, raw_external_goal=raw(data))
        adm = replace(
            adm,
            admitted_present_sha256=frozenset({sha(item.raw_native_probe)}),
            admitted_action_sha256=frozenset({sha(item.raw_s16_action)}),
            admitted_goal_sha256=frozenset({sha(item.raw_external_goal)}),
        )
    with pytest.raises((ValueError, TypeError)):
        join_independent_action_goal_source(item, adm, current=current)


def test_source_shaped_future_contract_does_not_rewrite_original_s_l10():
    item, admission, current = fixture()
    r = join_independent_action_goal_source(item, admission, current=current)
    assert r.prior_l10.witness.original_physical_source_attested is False
    assert r.qualified_episode.feedback is None
    assert r.goal_label.provenance.source == "external-goal-claimed"
    assert not r.action_authority


def test_archived_real_g413_remains_zero_goal_labels():
    original = os.getenv("L11_REAL_ORIGINAL_ZIP")
    if not original:
        pytest.skip("saved real source artifact unavailable")
    historical = audit_l12_real_action_goal_gate(Path(original))
    r = review_l12_g413_archive_no_per_action_goal(historical)
    assert r.status is L13ReceiptStatus.ARCHIVED_G413_NO_ACTION_GOAL
    assert historical.original_s49_action_rows == 11
    assert r.per_action_goal_source_candidate_count == 0
    assert r.goal_label is None and r.prior_l10 is None
    assert r.qualified_episode is None
    assert r.goal_source_admission is None
    assert not r.action_authority and not r.real_original_authenticated_by_l13
    with pytest.raises(L13ReceiptRejected):
        review_l12_g413_archive_no_per_action_goal(replace(
            historical, independent_per_action_goal_receipts=1,
        ))
    with pytest.raises(L13ReceiptRejected):
        review_l12_g413_archive_no_per_action_goal(replace(
            historical, qualified_l10_training_pairs=11,
        ))



def test_16_source_shaped_triplets_feed_existing_l10_only_with_cheap_null():
    """Real existing L6/L8 classes, but every receipt is synthetically authored."""
    args, s_epoch, supervisor = l10.fixture()
    before_clock = supervisor.last_at_ns
    reviewed = []
    present = []
    actions = []
    goals = []
    for sample in args["training"]:
        ep = sample.outcome.episode
        n = sample.native
        s = n.observation.snapshot
        status = "REACHED" if sample.goal.goal_reached else "NOT_REACHED"
        item, admission, current = fixture(
            result=status, session=ep.session_id,
            seq=n.observation.seq,
            distance=n.distance_m,
            food=s.food, action_ref=ep.action_ref,
            action_id=ep.action_id,
        )
        result = join_independent_action_goal_source(
            item, admission, current=current,
        )
        assert result.goal_label.goal_reached == sample.goal.goal_reached
        assert result.prior_l10.witness.cue_tags == sample.witness.cue_tags
        reviewed.append(result.prior_l10)
        present.append(result.source_present_sha256)
        actions.append(result.source_action_sha256)
        goals.append(result.source_goal_sha256)
    with_memory = evaluate_l10_next_epoch_shadow(
        s_epoch, **{
            **args, "training": tuple(reviewed),
            "admitted_prior_probe_sha256": frozenset(present),
            "source_admission": GoalSourceAdmission(
                frozenset(actions), frozenset(goals),
            ),
        }
    )
    without = evaluate_l10_next_epoch_shadow(
        s_epoch, **{
            **args, "training": tuple(reviewed),
            "admitted_prior_probe_sha256": frozenset(present),
            "source_admission": GoalSourceAdmission(
                frozenset(actions), frozenset(goals),
            ),
            "retention_enabled": False,
        }
    )
    assert with_memory.source_bounded_training == 16
    assert len(with_memory.learning.cognition.memories) == 16
    assert with_memory.learning.advice.status is ContextualStatus.CHEAP_EQUIVALENT
    assert with_memory.learning.candidate_action_ref == "WAIT"
    assert with_memory.cheap_exact_ref == "WAIT"
    assert without.learning.candidate_action_ref == "MOVE_AWAY"
    assert without.learning.advice.status is ContextualStatus.NO_GOAL_DATA
    assert supervisor.last_at_ns == before_clock
    assert supervisor.open_actions == ()
    assert not with_memory.action_authority
    assert not with_memory.physical_learning_attested
    assert with_memory.action_issues == with_memory.native_reads == 0
