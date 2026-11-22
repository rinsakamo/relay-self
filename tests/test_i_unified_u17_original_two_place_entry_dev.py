"""U17 gate tests: no simulated WORLD, no forged original S1 acceptance."""
from __future__ import annotations

import asyncio
import inspect

import pytest

from experiments.i_unified_u17_original_two_place_trial_dev import (
    U17OriginalS1Settled,
    run_original_u17_two_place_trial_dev,
)
from relay_self.i_lane_i4a_s2_owned_native_runner_dev import (
    I4AS2OwnedNativeHold,
    continue_original_s1_to_s2_owned_native_dev,
)


def test_u17_path_uses_original_s1_and_no_independent_sender():
    assert inspect.iscoroutinefunction(run_original_u17_two_place_trial_dev)
    assert inspect.iscoroutinefunction(continue_original_s1_to_s2_owned_native_dev)
    arg_names = set(inspect.signature(
        run_original_u17_two_place_trial_dev,
    ).parameters)
    assert {"bridge", "original_s1", "propose_grant", "issue_grant",
            "operator_permit"}.issubset(arg_names)
    assert not {"session", "native_sender", "physical_issuer"} & arg_names
    assert U17OriginalS1Settled.__dataclass_fields__["loop"] is not None


def test_u17_no_original_bridge_never_calls_s1(tmp_path):
    calls = []

    async def forbidden_s1():
        calls.append("unexpected")
        raise AssertionError("synthetic S1 callback should never start")

    with pytest.raises(I4AS2OwnedNativeHold, match="isolated original"):
        asyncio.run(run_original_u17_two_place_trial_dev(
            bridge=object(), self_id="A", evidence_dir=tmp_path,
            original_s1=forbidden_s1, propose_grant=None,
            issue_grant=None, operator_permit=None, provenance=None,
            real_world_granted=True,
        ))
    assert calls == []
