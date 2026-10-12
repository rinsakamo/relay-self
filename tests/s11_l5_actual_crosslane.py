"""S11 cross-lane CI only: consume *actual* pinned L5 serial advice.

Not discovered by ordinary pytest (filename intentionally not test_*.py);
a dedicated job runs this with L5's separately executed immutable checkout.
No World/Action, source authentication or scientific qualification.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from adapters.mineflayer.self_s10_memory_ablation import compare_shadow_ab
from adapters.mineflayer.self_s11_l5_shadow_intake import (
    L5_EXACT_HEAD,
    S11Disposition,
    S11SourcePointer,
    review_l5_against_s10,
)
from test_self_s10_memory_ablation import _arms


def test_pinned_actual_l5_advice_never_turns_synthetic_options_into_s49():
    file = Path(os.environ["S11_ACTUAL_L5_ADVICE"])
    payload = json.loads(file.read_text(encoding="utf-8"))
    assert payload["producer_head"] == L5_EXACT_HEAD
    arms, _ = _arms()
    paired = compare_shadow_ab(**arms)
    source = S11SourcePointer(
        paired.session_id, paired.probe_seq, "a" * 64, L5_EXACT_HEAD,
    )
    checks = (
        ("distinct", S11Disposition.UNPAIRED_SOURCE),
        ("cheap", S11Disposition.UNPAIRED_SOURCE),
        ("withheld", S11Disposition.L5_ABSTAINED),
    )
    for key, expected in checks:
        result = review_l5_against_s10(
            paired=paired,
            current_probe=arms["probe"],
            source=source,
            admitted_current_probe_sha256=frozenset({"a" * 64}),
            l5_advice=payload[key],
        )
        assert result.status is expected
        assert result.fixed_l0_selection == "MOVE_AWAY"
        assert not result.action_authority
        assert not result.goal_evidence_authenticated_here
        assert not result.source_byte_authenticated_here
        assert not result.science_qualified
        assert not result.memory_causal_benefit_established
        assert result.physical_actions == result.learning_updates == result.habit_grants == 0
