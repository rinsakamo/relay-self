"""Independent R four-arm engineering reviewer rejects missing/borrowed evidence."""
from pathlib import Path

import pytest

from experiments.standard_env import m02_v7_four_arm_qualification_audit as q
from experiments.standard_env import m02_v7_remaining_profile_preflight as profile


def test_exact_four_sha_registrations_and_distinct_grants():
    assert all(
        q.CONFIGS[arm] == profile.digest(profile.expected_candidate(
            (Path(__file__).parent / "fixtures" /
             "rsee_m02_v7_tick_base_qualified_config.yml").read_bytes(), arm))
        for arm in q.ARMS
    )
    assert len(set(q.GRANTS.values())) == 4
    assert "BASE_ON" not in q.ARMS
    assert "20261016" not in "".join(q.GRANTS.values())


@pytest.mark.parametrize("arm", list(q.ARMS)+["BASE_ON"])
def test_qualification_never_inferred_without_originals(tmp_path: Path, arm):
    originals = tmp_path / "originals"
    assets = tmp_path / "assets"
    originals.mkdir()
    assets.mkdir()
    witness = tmp_path / "witness.json"
    witness.write_text("{}", encoding="utf-8")
    with pytest.raises(q.NotQualified):
        q.review(originals, assets, witness, "38910000000", arm)


def test_missing_host_evidence_rejected(tmp_path: Path):
    originals = tmp_path / "originals"
    assets = tmp_path / "assets"
    originals.mkdir()
    assets.mkdir()
    with pytest.raises(q.NotQualified):
        q.review(originals, assets, tmp_path / "absent", "38910000000", "SHAM_ON")


def test_original_base_only_grant_must_never_replay():
    assert "USER_M02_V7_TICK_CHORD_BASE_ON_20261016_ONCE" not in q.GRANTS.values()
    assert q.FAIL == "R_M02_V7_REMAINING_ARM_QUALIFICATION_FAILED_OR_UNDETERMINED"
