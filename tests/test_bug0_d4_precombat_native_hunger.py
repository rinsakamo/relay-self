"""DEV precombat hunger observation: never grants EAT or ATTACK."""

from dataclasses import replace

import pytest

import test_bug0_s49_attack_owner as cases
from tools.bug0_d4_oneworld import S49D3Rejected, qualified_native_precombat_hunger


def _hunger(food: float):
    _, observation = cases._pair()
    return replace(
        observation,
        snapshot=replace(observation.snapshot, food=food),
    )


def test_real_native_food_must_cross_existing_exclusive_14_threshold():
    probe = _hunger(13)
    assert qualified_native_precombat_hunger(probe, probe.session_id) is True
    for food in (20, 16, 14, 0):
        p = _hunger(food)
        assert qualified_native_precombat_hunger(p, p.session_id) is False


@pytest.mark.parametrize("break_it", [
    lambda p: replace(p, session_id="other-world"),
    lambda p: replace(p, request_id=""),
    lambda p: replace(p, kind="invalid-kind"),
    lambda p: replace(
        p, snapshot=replace(p.snapshot, health=15),
    ),
    lambda p: replace(
        p, snapshot=replace(p.snapshot, oxygen_level=0),
    ),
    lambda p: replace(
        p, snapshot=replace(
            p.snapshot,
            nearby_entities_coverage=replace(
                p.snapshot.nearby_entities_coverage, truncated=True,
            ),
        ),
    ),
])
def test_untrusted_or_unsafe_native_source_cannot_authorize_precombat(break_it):
    p = _hunger(13)
    with pytest.raises(S49D3Rejected):
        qualified_native_precombat_hunger(break_it(p), p.session_id)
