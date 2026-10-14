"""R V6 atomic-food independent source and staged clone boundary negatives."""
from copy import deepcopy
import hashlib
import json

import pytest

from experiments.standard_env.v6_atomic_admission import (
    MAX_SCORE,
    PACK_DIR,
    S_ATOMIC_SOURCE_BLOB,
    S_ATOMIC_SOURCE_HEAD,
    AtomicReviewRejected,
    expected_pack_bytes,
    main,
    plan,
    review_s_atomic_source,
    review_score_claim,
    review_staged_clone,
    review_staged_index,
)


def _synthetic_indexes():
    """Fake indexes are NOT Golden proof or a physical World."""
    base = (
        ("level.dat", 5, hashlib.sha256(b"fake0").hexdigest()),
        ("region/r.0.0.mca", 5, hashlib.sha256(b"fake1").hexdigest()),
    )
    files = tuple(
        (path, len(raw), hashlib.sha256(raw).hexdigest())
        for path, raw in expected_pack_bytes().items()
    )
    return base, tuple(sorted(base + files))


def _score():
    source = expected_pack_bytes()[
        f"{PACK_DIR}/data/relayself_v6/function/atomic_food.mcfunction"
    ]
    sha = hashlib.sha256(source).hexdigest()
    return {
        "before_gametime": 2400, "after_gametime": 2400,
        "source_function_sha256": sha, "summon_success": 1,
        "claimed_invocations": 1, "m0_tick_at_opportunity": 11,
    }


def test_atomic_r_no_read_plan_and_pinned_candidate_only(capsys):
    assert main([]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data == plan()
    assert data["golden_checked"] is False
    assert data["server_function_single_use"] == "UNGUARDED_SOURCE"
    assert data["physical_execution_authorized"] is False
    assert len(S_ATOMIC_SOURCE_BLOB) == 40
    assert len(S_ATOMIC_SOURCE_HEAD) == 40


def test_atomic_r_pack_is_independent_fixed_three_files_with_command_order():
    expected = expected_pack_bytes()
    assert len(expected) == 3
    assert all(path.startswith(PACK_DIR + "/") for path in expected)
    metadata = json.loads(expected[f"{PACK_DIR}/pack.mcmeta"])
    assert metadata["pack"]["pack_format"] == 81
    f = expected[
        f"{PACK_DIR}/data/relayself_v6/function/atomic_food.mcfunction"
    ].decode("utf-8").splitlines()
    assert f[3] == (
        "execute store result score #before rs_v6_tick run time query gametime"
    )
    assert f[4].startswith(
        "execute store success score #ok rs_v6_tick run summon minecraft:item"
    )
    assert f[5] == (
        "execute store result score #after rs_v6_tick run time query gametime"
    )
    assert sum("summon minecraft:item" in line for line in f) == 1
    assert not any("unless score" in line for line in f)  # Replay NOT guarded.


def test_atomic_r_index_exact_overlay_is_never_qualified_world():
    original, staged = _synthetic_indexes()
    result = review_staged_index(original, staged)
    assert result["classification"] == "RSEE_V6_ATOMIC_STAGED_DELTA_SHAPE_REVIEW_ONLY"
    assert result["original_file_count"] == 2
    assert result["added_pack_file_count"] == 3
    assert result["changed_original_bytes"] is False
    assert result["server_function_loaded"] is False
    assert result["single_use_guard_present"] is False
    assert result["exact_summon_effect_tick_attested"] is False
    assert result["physical_execution_authorized"] is False


def test_atomic_r_index_rejects_world_mutation_and_unregistered_pack_files():
    original, staged = _synthetic_indexes()
    extras = [
        tuple(x for x in staged if x[0] != "level.dat"),
        staged + (("fake.extra", 1, "a" * 64),),
        staged + (staged[-1],),
        tuple((p, n + 1, sha) if p == "level.dat" else (p, n, sha)
              for p, n, sha in staged),
        tuple((p, n, "a" * 64) if p.endswith("atomic_food.mcfunction")
              else (p, n, sha) for p, n, sha in staged),
        tuple((p, n, "f" * 64) if p == "level.dat" else (p, n, sha)
              for p, n, sha in staged),
    ]
    for candidate in extras:
        with pytest.raises(AtomicReviewRejected):
            review_staged_index(original, candidate)


def test_atomic_r_score_claim_consistent_but_explicitly_untrusted():
    data = _score()
    result = review_score_claim(
        data, expected_function_sha256=data["source_function_sha256"],
    )
    assert result["classification"] == (
        "RSEE_V6_ATOMIC_REPORTED_SCORE_CLAIM_REVIEW_ONLY"
    )
    assert result["claimed_gametime_tick"] == 2400
    assert result["m0_decision_tick"] == 11
    assert result["original_server_command_bytes_verified"] is False
    assert result["independent_single_use_verified"] is False
    assert result["true_world_effect_tick_attested"] is False
    assert result["world_start_matched"] is False
    assert result["physical_execution_authorized"] is False
    assert result["science_g3"] == "NO_GO"


@pytest.mark.parametrize(("field", "invalid"), [
    ("before_gametime", -1),
    ("before_gametime", True),
    ("before_gametime", MAX_SCORE + 1),
    ("before_gametime", 2399),
    ("after_gametime", 2401),
    ("after_gametime", 1.0),
    ("summon_success", 0),
    ("summon_success", 2),
    ("summon_success", True),
    ("claimed_invocations", 0),
    ("claimed_invocations", 2),
    ("claimed_invocations", True),
    ("m0_tick_at_opportunity", 12),
    ("m0_tick_at_opportunity", "11"),
    ("source_function_sha256", "f" * 64),
])
def test_atomic_r_score_claim_negative_controls(field, invalid):
    data = _score()
    data[field] = invalid
    with pytest.raises(AtomicReviewRejected):
        review_score_claim(
            data, expected_function_sha256=_score()["source_function_sha256"],
        )


def test_atomic_r_score_claim_rejects_missing_and_forged_expected_hash():
    data = _score()
    for mutation in (
        lambda x: x.pop("claimed_invocations"),
        lambda x: x.update(fabricated_original_proof=True),
    ):
        bad = deepcopy(data)
        mutation(bad)
        with pytest.raises(AtomicReviewRejected):
            review_score_claim(
                bad, expected_function_sha256=data["source_function_sha256"],
            )
    with pytest.raises(AtomicReviewRejected):
        review_score_claim(data, expected_function_sha256="0" * 64)


def test_atomic_r_real_clone_requires_actual_qualified_golden_and_s_pin(tmp_path):
    with pytest.raises((AtomicReviewRejected, ValueError, OSError)):
        review_s_atomic_source(tmp_path / "missing")
    with pytest.raises((AtomicReviewRejected, ValueError, OSError)):
        review_s_atomic_source(tmp_path)
    assert main(["--s-checkout", str(tmp_path)]) == 2
    assert main(["--staged-clone", str(tmp_path)]) == 2
    with pytest.raises((AtomicReviewRejected, ValueError, OSError)):
        review_staged_clone(
            jar=tmp_path / "jar", golden=tmp_path / "gold",
            manifest=tmp_path / "manifest",
            initial_evidence=tmp_path / "evidence",
            staged_clone=tmp_path / "clone",
            pinned_s_checkout=tmp_path / "missing",
        )
