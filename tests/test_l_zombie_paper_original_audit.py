"""Z1 Paper source-only audit tests: rows are SYNTHETIC, not real JVM evidence."""
import hashlib

import pytest

from tools.l_zombie_paper_original_audit import (
    PaperZombieSourceRejected, audit_paper_zombie_window, report_paper_only,
)

WORLD = "095288da-4414-441b-9cbe-1b35a3a5d1bc"
ENTITY = "baf12c70-c261-49f4-a309-ccf0f91c5ae1"


def raw_lines(*, gap=None, missing=None, changed=None, end="PAPER_WINDOW_COMPLETE",
              duplicate=False, extra=False):
    pre = "[12:00:00 INFO]: "
    arm = (
        f"L_ZOMBIE_ARM_V1 marker=z1-1 session=s1 world={WORLD} entity_uuid={ENTITY} "
        f"entity_id=42 expected_samples=31 pre_offset=10 future_offset=30"
    )
    out = [pre + arm]
    for i in range(31):
        if i == missing:
            continue
        tick = 1000 + i + (1 if gap is not None and i >= gap else 0)
        entity = ENTITY if not changed or i != 21 else (
            "d0755a89-b852-40ed-88c4-07e17255aab7"
        )
        row = (
            f"L_ZOMBIE_TICK_V1 marker=z1-1 session=s1 world={WORLD} entity_uuid={entity} "
            f"entity_id=42 spawn_instance=1 server_tick={tick} offset={i} "
            f"x={i / 10:.12f} y=64.000000000000 z=0.000000000000"
        )
        out.append(pre + row)
        if i == duplicate:
            out.append(pre + row)
    out.append(pre + (
        f"L_ZOMBIE_END_V1 marker=z1-1 session=s1 result={end} "
        f"samples=31 last_offset=30"
    ))
    if extra:
        out.append(pre + "L_ZOMBIE_TICK_V1 marker=z1-1 session=s1 invalid=1")
    return ("\n".join(out) + "\n").encode()


def verified(raw, *, sha=None):
    return audit_paper_zombie_window(
        raw, original_sha256=sha or hashlib.sha256(raw).hexdigest(),
        expected_marker="z1-1", expected_session="s1",
    )


def test_31_paper_tick_original_shaped_rows_and_exact_future_target():
    raw = raw_lines()
    w = verified(raw)
    assert w.total_samples == 31
    assert (w.pre_source_tick, w.forecast_freeze_tick, w.target_tick) == (
        1000, 1010, 1030,
    )
    assert w.pre_source_xz_m == (0, 0)
    assert w.forecast_freeze_xz_m == (1, 0)
    assert w.target_xz_m == (3, 0)
    assert w.entity_uuid == ENTITY
    assert w.entity_spawn_instance == 1
    assert w.paper_only and not w.mineflayer_client_join_attested
    assert not w.qualified_world_claim and not w.learned_state_admitted
    report = report_paper_only(
        raw, sha256=hashlib.sha256(raw).hexdigest(), marker="z1-1", session="s1",
    )
    assert report["classification"] == "PAPER_31_TICK_EXACT_SAME_ZOMBIE_SOURCE_ONLY"
    assert not report["real_java_pid_and_jar_attested_here"]
    assert not report["physical_world_evidence_qualified_here"]


@pytest.mark.parametrize("kwargs", [
    {"gap": 15},
    {"missing": 21},
    {"changed": True},
    {"duplicate": 20},
    {"end": "ENTITY_REMOVED"},
    {"end": "NONCONTIGUOUS_PAPER_TICK"},
    {"end": "DISABLED"},
    {"extra": True},
])
def test_missing_or_changed_zombie_or_paper_tick_rejected(kwargs):
    with pytest.raises(PaperZombieSourceRejected):
        verified(raw_lines(**kwargs))


@pytest.mark.parametrize("str_replace", [
    (b"spawn_instance=1", b"spawn_instance=2"),
    (b"entity_id=42", b"entity_id=43"),
    (b"server_tick=1020", b"server_tick=1009"),
    (b"offset=15", b"offset=14"),
    (b"y=64.000000000000", b"y=NaN"),
    (b"expected_samples=31", b"expected_samples=30"),
    (b"future_offset=30", b"future_offset=31"),
    (b"session=s1", b"session=s2"),
])
def test_invalid_source_fields_are_rejected(str_replace):
    before, after = str_replace
    raw = raw_lines().replace(before, after, 1)
    with pytest.raises(PaperZombieSourceRejected):
        verified(raw)


def test_original_sha_and_full_line_boundary_required():
    raw = raw_lines()
    with pytest.raises(PaperZombieSourceRejected, match="SHA"):
        verified(raw, sha="0"*64)
    with pytest.raises(PaperZombieSourceRejected):
        verified(raw.rstrip(b"\n"))
    with pytest.raises(PaperZombieSourceRejected):
        verified(raw+b"something-not-newline")
    with pytest.raises(PaperZombieSourceRejected):
        verified(raw.replace(b"z1-1", b"z1-2", 1))


def test_paper_only_cannot_claim_mineflayer_client_tick_correlation():
    w = verified(raw_lines())
    assert w.mineflayer_client_join_attested is False
    assert w.l2_model_called is False
    assert w.actor_action_issued is False
    assert w.qualified_world_claim is False
