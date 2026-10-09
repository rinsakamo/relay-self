"""S52 no remote egress: invalid endpoint rejected before any model IO."""
import pytest

from adapters.mineflayer.local_chat_provider import (
    LocalInferenceUnavailable,
    LoopbackChatProvider,
    LoopbackInferenceConfig,
)
from relay_self.relay_engine import CognitionMode


@pytest.mark.parametrize("url", (
    "https://example.org/v1/chat/completions",
    "http://192.168.1.3/v1/chat/completions",
    "http://127.0.0.1:1234/private",
    "http://localhost:1234/v1/chat/completions?redirect=https://evil.com",
))
def test_provider_rejects_nonlocal_or_noncanonical_endpoint(url):
    with pytest.raises(LocalInferenceUnavailable):
        LoopbackInferenceConfig(model="Gemma", endpoint=url)


def test_missing_typed_request_does_not_contact_provider():
    provider = LoopbackChatProvider(LoopbackInferenceConfig(model="test"))
    with pytest.raises(LocalInferenceUnavailable):
        provider(None, mode=CognitionMode.BOUNDED)


def test_budget_and_model_are_explicit():
    with pytest.raises(LocalInferenceUnavailable):
        LoopbackInferenceConfig(model="", max_tokens=2)
    with pytest.raises(LocalInferenceUnavailable):
        LoopbackInferenceConfig(model="test", max_tokens=10000)
