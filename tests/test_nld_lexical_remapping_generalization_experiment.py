from experiments.nld_lexical_remapping_generalization import (
    FAMILIES,
    build_cases,
    build_schedule,
)


def test_matrix_shape() -> None:
    assert [family.family_id for family in FAMILIES] == [
        "route",
        "color",
        "code",
    ]
    assert len(build_cases()) == 12
    assert len(build_schedule()) == 216
