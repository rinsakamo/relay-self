"""CLI grant and non-issuing defaults: no local GPU/World calls in CI."""
from __future__ import annotations

import asyncio

import pytest

from experiments.run_cognitive_minimal_world import parser, run
from relay_self.cognitive_minimal_dev import MinimalCognitionError


def test_cli_default_is_shadow_and_refuses_all_real_ends_without_grants() -> None:
    args = parser().parse_args(["--model", "synthetic-model"])
    assert not args.execute_native
    assert not args.grant_real_llm and not args.grant_real_world
    with pytest.raises(MinimalCognitionError, match="both explicit"):
        asyncio.run(run(args))


def test_cli_native_execution_flag_is_not_a_grant_for_real_model_or_world() -> None:
    args = parser().parse_args(["--model", "synthetic-model", "--execute-native"])
    with pytest.raises(MinimalCognitionError, match="both explicit"):
        asyncio.run(run(args))
