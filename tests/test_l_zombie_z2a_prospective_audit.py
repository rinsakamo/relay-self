"""Z2a prospective freeze tests: all rows synthetic, not actual Paper."""
from __future__ import annotations

import hashlib
import json

import pytest

from test_l_zombie_paper_original_audit import raw_lines
from tools.l_zombie_paper_original_audit import PaperZombieSourceRejected
from tools.l_zombie_z2a_prospective_audit import audit_z2a_prospective, main


def fixture(*, offset=10, dx=0.0, move_freeze=False, duplicate=False):
    source = raw_lines()
    lines = source.decode().splitlines()
    freeze = (
        "[12:00:00 INFO]: L_ZOMBIE_CHEAP_FREEZE_V2 "
        "marker=z1-1 session=s1 world=095288da-4414-441b-9cbe-1b35a3a5d1bc "
        "entity_uuid=baf12c70-c261-49f4-a309-ccf0f91c5ae1 "
        "entity_id=42 source_first_tick=1000 issued_tick=1010 target_tick=1030 "
        f"stationary_x={1.0+dx:.12f} stationary_z=0.000000000000 "
        "velocity_x=3.000000000000 velocity_z=0.000000000000"
    )
    # The TICK_V1 offset10 is the 12th marker line including ARM at index0.
    lines.insert(offset + 2, freeze)
    if duplicate:
        lines.insert(offset + 3, freeze)
    return ("\n".join(lines) + "\n").encode()


def audited(raw):
    return audit_z2a_prospective(
        raw, sha256=hashlib.sha256(raw).hexdigest(), marker="z1-1", session="s1",
    )


def test_freeze_is_prospective_and_independently_scored_against_future():
    result = audited(fixture())
    assert result["issued_tick"] == 1010
    assert result["target_tick"] == 1030
    assert result["freeze_before_tick11"]
    assert result["original_freeze_line"] < result["target_observation_line"]
    assert result["stationary_forecast_xz_m"] == [1, 0]
    assert result["velocity_forecast_xz_m"] == [3, 0]
    assert result["stationary_error_m"] == pytest.approx(2.0)
    assert result["constant_velocity_error_m"] == 0
    assert result["forecast_owner"] == "PAPER_CHEAP_NOT_L2"
    assert not result["native_client_tick_join_attested"]
    assert not result["real_gemma_forecast_attested"]
    assert not result["physical_paper_owner_attested_by_this_parser"]


def test_legacy_z1b_paper_original_without_freeze_cannot_claim_prospective():
    with pytest.raises(PaperZombieSourceRejected, match="ONE freeze"):
        audited(raw_lines())


@pytest.mark.parametrize("offset", [9, 11, 25, 31])
def test_freeze_at_wrong_time_or_after_outcome_cannot_score(offset):
    with pytest.raises(PaperZombieSourceRejected, match="forecast after outcome"):
        audited(fixture(offset=offset))


def test_fabricated_future_target_dependent_numeric_fails():
    with pytest.raises(PaperZombieSourceRejected, match="data not available"):
        audited(fixture(dx=1))


def test_duplicate_freeze_fails():
    with pytest.raises(PaperZombieSourceRejected, match="ONE freeze"):
        audited(fixture(duplicate=True))


@pytest.mark.parametrize("kwargs", [
    {"gap": 10}, {"missing": 11}, {"duplicate": 20}, {"changed": True},
    {"end": "ENTITY_REMOVED"},
])
def test_wrong_source_cannot_be_qualified(kwargs):
    original = raw_lines(**kwargs).decode().splitlines()
    freeze = fixture().decode().splitlines()[12]
    original.insert(12, freeze)
    with pytest.raises(PaperZombieSourceRejected):
        audited(("\n".join(original)+"\n").encode())


def test_external_actor_cannot_reuse_another_uuid():
    data = fixture().replace(
        b"entity_uuid=baf12c70-c261-49f4-a309-ccf0f91c5ae1",
        b"entity_uuid=d0755a89-b852-40ed-88c4-07e17255aab7",
        1,
    )
    with pytest.raises(PaperZombieSourceRejected):
        audited(data)


def test_exact_sha_readback_create_only(tmp_path):
    source = tmp_path / "original.log"
    report = tmp_path / "readback.json"
    data = fixture()
    source.write_bytes(data)
    args = [
        "--paper-original", str(source), "--sha256", hashlib.sha256(data).hexdigest(),
        "--marker", "z1-1", "--session", "s1", "--report", str(report),
    ]
    assert main(args) == 0
    assert json.loads(report.read_text())["forecast_owner"] == "PAPER_CHEAP_NOT_L2"
    assert main(args) == 2
    assert source.read_bytes() == data


def test_sha_mismatch_never_creates_report(tmp_path):
    source = tmp_path / "original.log"
    report = tmp_path / "readback.json"
    source.write_bytes(fixture())
    assert main([
        "--paper-original", str(source), "--sha256", "0"*64,
        "--marker", "z1-1", "--session", "s1", "--report", str(report),
    ]) == 2
    assert not report.exists()
