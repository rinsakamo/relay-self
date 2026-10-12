"""Pure V two-feature cheap-null controls, no L5/World imports."""
from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.validation.l5_cheap_oracle import (
    CheapOracleRejected,
    SourceShapedSample,
    cheap_two_feature_table,
)


def rows():
    out = []
    idx = 0
    for a in (False, True):
        for b in (False, True):
            winner = "OPTION_B" if a == b else "OPTION_A"
            for action in ("OPTION_A", "OPTION_B"):
                for repeat in (0, 1):
                    tags = tuple(sorted((
                        ("alpha",) if a else ()
                    ) + (("beta",) if b else ())))
                    out.append(SourceShapedSample(
                        session=f"v-synthetic-{idx}",
                        action=action,
                        tags=tags,
                        success=action == winner,
                        evidence_sha256=f"{idx + 1:064x}",
                        goal_sha256=f"{idx + 101:064x}",
                    ))
                    idx += 1
    return out


def test_strongest_cheap_two_feature_table_is_exact_xor_mapping():
    mapping = cheap_two_feature_table(rows())
    assert mapping == {
        (False, False): "OPTION_B",
        (False, True): "OPTION_A",
        (True, False): "OPTION_A",
        (True, True): "OPTION_B",
    }


def test_replayed_session_or_original_source_refused():
    x = rows()
    x[1] = replace(x[1], session=x[0].session)
    with pytest.raises(CheapOracleRejected, match="duplicated"):
        cheap_two_feature_table(x)
    x = rows()
    x[1] = replace(x[1], goal_sha256=x[0].evidence_sha256)
    with pytest.raises(CheapOracleRejected, match="duplicated"):
        cheap_two_feature_table(x)


def test_missing_complete_balanced_cell_cannot_win():
    with pytest.raises(CheapOracleRejected, match="16-episode"):
        cheap_two_feature_table(rows()[:-1])


def test_equivalent_goal_rates_produce_abstention():
    x = rows()
    x[0] = replace(x[0], success=False)
    x[1] = replace(x[1], success=False)
    with pytest.raises(CheapOracleRejected, match="discriminating"):
        cheap_two_feature_table(x)


def test_source_shaped_boolean_not_weakly_accepted():
    x = rows()
    x[0] = replace(x[0], success=1)
    with pytest.raises(CheapOracleRejected, match="duplicated"):
        cheap_two_feature_table(x)


def test_no_unrelated_declaration_accepted():
    with pytest.raises(CheapOracleRejected):
        cheap_two_feature_table(rows(), features=("alpha", "alpha"))
    with pytest.raises(CheapOracleRejected):
        cheap_two_feature_table(rows(), actions=("OPTION_A", "OPTION_A"))
