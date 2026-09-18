from types import SimpleNamespace

import pytest

from experiments.nld_tri_mode import (
    DEFAULT_MODES,
    MODE_DEFAULTS,
    build_probe_case,
    dispatch_generation,
    dry_run_payload,
    mode_arguments,
    parse_decision_label,
    resolve_modes,
    round_to_block,
)


class FakeTokenizer:
    eos_token_id = 99


class FakeModel:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def ar_generate(self, *args, **kwargs):
        self.calls.append(("ar", args, kwargs))
        return "ar-result"

    def generate(self, *args, **kwargs):
        self.calls.append(("dlm", args, kwargs))
        return "dlm-result"

    def linear_spec_generate(self, *args, **kwargs):
        self.calls.append(("linear_spec", args, kwargs))
        return "linear-spec-result"


def test_mode_defaults_mirror_official_simple_evaluator() -> None:
    assert MODE_DEFAULTS == {
        "ar": {"block_length": 1, "threshold": None},
        "dlm": {"block_length": 8, "threshold": 0.9},
        "linear_spec": {"block_length": 32, "threshold": 0.0},
    }


@pytest.mark.parametrize(
    ("tokens", "block", "expected"),
    [
        (1, 8, 8),
        (31, 8, 24),
        (32, 8, 32),
        (33, 32, 32),
        (64, 32, 64),
    ],
)
def test_round_to_block_matches_official_floor_then_minimum_rule(
    tokens: int,
    block: int,
    expected: int,
) -> None:
    assert round_to_block(tokens, block) == expected


def test_round_to_block_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="max_new_tokens"):
        round_to_block(0, 8)
    with pytest.raises(ValueError, match="block_length"):
        round_to_block(8, 0)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A", "A"),
        ("Decision: B", "B"),
        ("The decision label is **B**. Reasoning considered A.", "B"),
        ("The feasible decision is **C = DEFER**; B is blocked.", "C"),
        ("I considered A, then choose C.", "C"),
        ("CAB", None),
        ("no bounded label", None),
    ],
)
def test_parse_decision_label_prefers_explicit_decision_statement(
    text: str,
    expected: str | None,
) -> None:
    assert parse_decision_label(text) == expected


def test_resolve_modes_defaults_and_rejects_bad_sets() -> None:
    assert resolve_modes(None) == DEFAULT_MODES
    assert resolve_modes(("dlm", "ar")) == ("dlm", "ar")

    with pytest.raises(ValueError, match="unknown modes"):
        resolve_modes(("other",))

    with pytest.raises(ValueError, match="duplicates"):
        resolve_modes(("ar", "ar"))


def test_mode_arguments_keep_mode_specific_native_surface() -> None:
    assert mode_arguments(
        "ar",
        max_new_tokens=32,
        max_thinking_tokens=32,
    ) == {
        "max_new_tokens": 32,
        "block_length": 1,
        "threshold": None,
        "max_thinking_tokens": None,
    }

    assert mode_arguments(
        "dlm",
        max_new_tokens=32,
        max_thinking_tokens=32,
    ) == {
        "max_new_tokens": 32,
        "block_length": 8,
        "threshold": 0.9,
        "max_thinking_tokens": 32,
    }

    assert mode_arguments(
        "linear_spec",
        max_new_tokens=16,
        max_thinking_tokens=32,
    ) == {
        "max_new_tokens": 32,
        "block_length": 32,
        "threshold": 0.0,
        "max_thinking_tokens": 32,
    }


def test_dispatch_generation_uses_native_model_methods() -> None:
    model = FakeModel()
    tokenizer = FakeTokenizer()
    prompt_ids = object()

    assert (
        dispatch_generation(
            model,
            tokenizer,
            prompt_ids,
            mode="ar",
            max_new_tokens=32,
            max_thinking_tokens=32,
        )
        == "ar-result"
    )
    assert model.calls[-1] == (
        "ar",
        (),
        {
            "prompt_ids": prompt_ids,
            "max_new_tokens": 32,
            "eos_token_id": 99,
        },
    )

    assert (
        dispatch_generation(
            model,
            tokenizer,
            prompt_ids,
            mode="dlm",
            max_new_tokens=32,
            max_thinking_tokens=32,
        )
        == "dlm-result"
    )
    name, args, kwargs = model.calls[-1]
    assert name == "dlm"
    assert args == (prompt_ids,)
    assert kwargs["block_length"] == 8
    assert kwargs["threshold"] == 0.9
    assert kwargs["max_thinking_tokens"] == 32

    assert (
        dispatch_generation(
            model,
            tokenizer,
            prompt_ids,
            mode="linear_spec",
            max_new_tokens=32,
            max_thinking_tokens=32,
        )
        == "linear-spec-result"
    )
    name, args, kwargs = model.calls[-1]
    assert name == "linear_spec"
    assert args == (prompt_ids,)
    assert kwargs["block_length"] == 32
    assert "threshold" not in kwargs


def test_dispatch_reports_missing_native_method() -> None:
    tokenizer = FakeTokenizer()

    with pytest.raises(RuntimeError, match="ar_generate"):
        dispatch_generation(
            SimpleNamespace(),
            tokenizer,
            object(),
            mode="ar",
            max_new_tokens=32,
            max_thinking_tokens=32,
        )


def test_probe_case_is_bounded_flee_fixture() -> None:
    case = build_probe_case()

    assert case.case_id == "easy_separable"
    assert case.expected_label == "A"
    assert "A = FLEE(destination=cave)" in case.prompt
    assert "C = DEFER" in case.prompt


def test_dry_run_describes_tri_mode_plan_without_model_claims() -> None:
    payload = dry_run_payload(
        model_id="example/nld",
        modes=None,
        max_new_tokens=32,
        max_thinking_tokens=32,
        seed=7,
        dtype="bf16",
    )

    assert payload["evidence_class"] == "experiment plan only"
    assert payload["model_id"] == "example/nld"
    assert [item["mode"] for item in payload["modes"]] == [
        "ar",
        "dlm",
        "linear_spec",
    ]
    assert payload["runtime"]["trust_remote_code"] is True
    assert payload["runtime"]["lora"] is False
    assert "dry-run output is not model evidence" in payload["non_claims"]
