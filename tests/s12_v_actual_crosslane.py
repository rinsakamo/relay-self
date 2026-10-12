"""S12 separate opt-in CI: consume *actual* independent pinned V oracle output.

Runs only when S12 GitHub CI supplies an output path. Never creates real
World data, grants a new physical run, or reads WSL2 S9 originals.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from adapters.mineflayer.self_s12_discrimination_preflight import (
    S12Readiness,
    assess_s12,
)
from test_self_s12_discrimination_preflight import _sources


def test_original_v_two_feature_oracle_requires_no_world_trial():
    path = Path(os.environ["S12_ACTUAL_V_ORACLE"])
    report = json.loads(path.read_text(encoding="utf-8"))
    s10, s11 = _sources()
    result = assess_s12(s10=s10, s11=s11, v_cheap=report)
    assert result.status is S12Readiness.NOT_READY
    assert result.v_two_feature_parity
    assert result.s49_executable_candidate_refs == ("MOVE_AWAY",)
    assert result.s49_nonissuing_refs == ("WAIT",)
    assert result.real_world_actions_issued == 0
    assert not result.action_authority
    assert not result.experiment_ready
    assert not result.fresh_world_permission
    assert not result.science_qualified
