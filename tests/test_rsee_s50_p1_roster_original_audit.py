"""Independent R native entity-roster negative controls; no Minecraft World."""
import hashlib
import json

import pytest

from experiments.standard_env import s50_p1_roster_original_audit as audit


SOURCE_HEAD = "c1d1004f8b748b2e848b8db6a89ae6c91599891a"
SELF = "00000000-0000-0000-0000-000000000002"
MOB = "00000000-0000-0000-0000-000000000003"
WORLD = "00000000-0000-0000-0000-000000000001"
MARKER = "action-session"


def make_source():
    paper = []
    canonical = [
        f"{WORLD}:0:0:{SELF}:PLAYER",
        f"{WORLD}:0:0:{MOB}:ZOMBIE",
    ]
    digest = hashlib.sha256(
        "".join(item + "\n" for item in canonical).encode("utf-8")
    ).hexdigest()
    for ix in range(1, 9):
        clock = 40 + ix
        paper.append(f"S50_DEV_WAIT_TICK marker_id={MARKER} world=world "
                     f"tick={clock} index={ix}")
        for i, item in enumerate(canonical, 1):
            wd, cx, cz, uid, kind = item.split(":")
            paper.append(
                f"S50_DEV_WAIT_ENTITY marker_id={MARKER} world=world "
                f"tick={clock} index={ix} roster_index={i} entity_world={wd} "
                f"chunk_x={cx} chunk_z={cz} uuid={uid} type={kind}")
        paper.append(f"S50_DEV_WAIT_SCOPE marker_id={MARKER} world=world "
                     f"tick={clock} index={ix} subject_uuid={SELF} "
                     f"loaded_entities=2 other_loaded_entities=1 other_online_players=0 "
                     f"coverage=LOADED_CHUNK_SAMPLER_ONLY "
                     f"client_held_controls=NOT_OBSERVED entity_lifecycle=NOT_ATTESTED "
                     f"census_sha256={digest}")
    report = {"movement": {"p1_wait_candidate": {"source_scope": {
        "source_entity_rows": 16,
        "native_roster_digests": [digest] * 8,
        "first_sample_entity_types": {"PLAYER": 1, "ZOMBIE": 1},
        "wait_ticks_admitted": 0, "p1_fatigue_recovered": 0,
        "independent_R_qualification": False,
    }}}}
    return "\n".join(paper), report


def prepare(monkeypatch, raw=None, report=None):
    from experiments.standard_env import s50_p1_wait_original_audit as old

    valid, baseline = make_source()
    raw = valid if raw is None else raw
    report = baseline if report is None else report

    def file(_root, filename):
        if filename == "paper_server.log":
            return raw.encode()
        if filename == "m02_report.json":
            return json.dumps(report).encode()
        raise AssertionError(filename)

    monkeypatch.setattr(old, "original", file)
    monkeypatch.setattr(old, "review", lambda root, **kwargs: {
        "observed_world_ticks": [41, 48],
        "source_action": "action",
        "native_session": "session",
        "original_world_uuid": "world",
    })


def evaluate():
    return audit.review(None, run=1, head=SOURCE_HEAD, artifact=10, jar="a" * 64)


def test_original_roster_recomputed_without_wait_promotion(monkeypatch):
    prepare(monkeypatch)
    receipt = evaluate()
    assert receipt["native_roster_rows"] == 16
    assert receipt["roster_same_across_8_samples"]
    assert receipt["sampled_type_histogram_per_tick"][0] == {
        "PLAYER": 1, "ZOMBIE": 1,
    }
    assert receipt["p1_fatigue_recovered"] == 0
    assert receipt["same_world_other_entity_ticks"] == []
    assert receipt["same_world_only_self_at_sample"]
    assert receipt["individual_lifecycle_events"] == "NOT_ATTESTED"


@pytest.mark.parametrize("before,after", [
    ("type=ZOMBIE", "type=CHICKEN"),
    ("roster_index=2", "roster_index=1"),
    ("uuid=" + SELF, "uuid=" + MOB),
    ("subject_uuid=" + SELF, "subject_uuid=" + MOB),
    ("census_sha256=", "census_sha256=FAKE"),
    ("entity_world=" + WORLD, "entity_world=BAD"),
    ("tick=42 index=2", "tick=40 index=2"),
    ("loaded_entities=2", "loaded_entities=1"),
    ("marker_id=action-session", "marker_id=foreign"),
])
def test_edited_original_roster_cannot_be_hidden_by_producer(monkeypatch, before, after):
    raw, report = make_source()
    assert before in raw
    prepare(monkeypatch, raw.replace(before, after, 1), report)
    with pytest.raises(audit.old.WaitOriginalRejected):
        evaluate()


def test_truncated_or_duplicate_rows_fail(monkeypatch):
    raw, report = make_source()
    lines = raw.splitlines()
    one = next(x for x in lines if x.startswith("S50_DEV_WAIT_ENTITY"))
    for altered in ("\n".join(x for x in lines if x != one),
                    raw + "\n" + one):
        prepare(monkeypatch, altered, report)
        with pytest.raises(audit.old.WaitOriginalRejected):
            evaluate()


def test_even_perfect_roster_never_authorizes_fatigue(monkeypatch):
    prepare(monkeypatch)
    receipt = evaluate()
    assert not receipt["r_engineering_qualified"]
    assert not receipt["science_go"]
    assert receipt["s_true_wait_admitted"] == 0
    assert receipt["native_held_motor_controls"] == "NOT_ATTESTED"
