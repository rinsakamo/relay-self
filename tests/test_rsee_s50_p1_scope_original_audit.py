"""Independent R source-scope negative controls (no S parser, no World)."""
import hashlib
import json

import pytest

from experiments.standard_env import s50_p1_scope_original_audit as extended
from experiments.standard_env import s50_p1_wait_original_audit as prior

SESSION = "s"
ACTION = "m02-paper-walk-1"
MARKER = ACTION + "-" + SESSION


def scope_fixture(monkeypatch):
    rows = []
    for i in range(1, 9):
        now = 60 + i
        rows.append(
            f"S50_DEV_WAIT_TICK marker_id={MARKER} world=world tick={now} "
            f"index={i} combat_events=0 swing_events=0"
        )
        rows.append(
            f"S50_DEV_WAIT_SCOPE marker_id={MARKER} world=world tick={now} "
            f"index={i} loaded_worlds=3 loaded_chunks=220 loaded_entities=23 "
            "other_loaded_entities=22 other_online_players=0 "
            f"census_sha256={'a'*64} movement_events=10 teleport_events=0 "
            "velocity_events=0 damage_events=0 interact_events=0 "
            "combat_events=0 swing_events=0 coverage=LOADED_CHUNK_SAMPLER_ONLY "
            "client_held_controls=NOT_OBSERVED entity_lifecycle=NOT_ATTESTED"
        )
    raw = "\n".join(rows)
    expected = {
        "classification": "S_P1_LOADED_CHUNK_CENSUS_AND_EVENTS_SAMPLE_ONLY",
        "source_scope_rows": 8, "first_world_tick": 61,
        "last_world_tick": 68,
        "activity_counter_changed_after_first_sampler": [],
        "other_loaded_entities_seen_ticks": list(range(61, 69)),
        "other_online_players_seen_ticks": [],
        "wait_ticks_admitted": 0, "p1_fatigue_recovered": 0,
        "independent_R_qualification": False,
    }
    report = {"movement": {"p1_wait_candidate": {"source_scope": expected}}}

    def fake_original(_root, filename):
        return json.dumps(report).encode() if filename == "m02_report.json" else raw.encode()

    monkeypatch.setattr(prior, "original", fake_original)
    monkeypatch.setattr(prior, "review", lambda root, **k: {
        "observed_world_ticks": [61, 68],
        "source_action": ACTION, "native_session": SESSION,
        "original_world_uuid": "world", "sampled_stationary_count": 8,
        "original_paper_sha256": hashlib.sha256(raw.encode()).hexdigest(),
    })
    return rows, report


def test_r_scope_detects_non_solo_and_does_not_issue_wait(monkeypatch):
    scope_fixture(monkeypatch)
    r = extended.review(None)
    assert r["observed_stationary_samples"] == 8
    assert r["other_loaded_entities_seen_ticks"] == list(range(61, 69))
    assert r["p1_fatigue_recovered"] == 0
    assert not r["global_solo_proven"]
    assert not r["true_full_tick_wait_proven"]


@pytest.mark.parametrize("old,new", [
    ("index=3", "index=2"),
    ("tick=63", "tick=62"),
    ("other_loaded_entities=22", "other_loaded_entities=24"),
    ("loaded_chunks=220", "loaded_chunks=0"),
    ("census_sha256=" + "a"*64, "census_sha256=FAIL"),
    ("coverage=LOADED_CHUNK_SAMPLER_ONLY", "coverage=WHOLE_TICK"),
    ("client_held_controls=NOT_OBSERVED", "client_held_controls=false"),
    ("entity_lifecycle=NOT_ATTESTED", "entity_lifecycle=COMPLETE"),
    ("movement_events=10", "movement_events=0"),
    ("world=world", "world=foreign"),
])
def test_adversarial_scope_row_rejected(monkeypatch, old, new):
    rows, report = scope_fixture(monkeypatch)
    # Replace the source in the mocked R original reader but leave the producer
    # declaration intact; no co-report can reconstruct a missing event stream.
    data = "\n".join(rows).replace(old, new, 1)
    monkeypatch.setattr(prior, "original", lambda root, name: (
        json.dumps(report).encode() if name == "m02_report.json"
        else data.encode()
    ))
    with pytest.raises(prior.WaitOriginalRejected):
        extended.review(None)


def test_forged_positive_wait_producer_receipt_rejected(monkeypatch):
    _, report = scope_fixture(monkeypatch)
    report["movement"]["p1_wait_candidate"]["source_scope"]["wait_ticks_admitted"] = 8
    with pytest.raises(prior.WaitOriginalRejected):
        extended.review(None)
