from experiments.nld_gemma_cross_substrate_transaction import (
    GEMMA_MAX_TOKENS,
    GEMMA_SEED,
    _gemma_request_body,
    _fully_adequate,
)


def test_gemma_request_is_bounded_and_deterministic() -> None:
    request = _gemma_request_body(
        model="gemma",
        prompt="Decision label:",
    )
    assert request["max_tokens"] == GEMMA_MAX_TOKENS == 32
    assert request["temperature"] == 0
    assert request["seed"] == GEMMA_SEED == 1
    assert request["reasoning_effort"] == "none"
    assert request["cache_prompt"] is False


def test_fully_adequate_requires_24_clean_correct_rows() -> None:
    assert _fully_adequate(
        {
            "count": 24,
            "correct_count": 24,
            "invalid_output_count": 0,
        }
    )
    assert not _fully_adequate(
        {
            "count": 24,
            "correct_count": 23,
            "invalid_output_count": 0,
        }
    )
