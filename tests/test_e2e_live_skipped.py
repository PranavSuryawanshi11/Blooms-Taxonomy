"""
Live end-to-end integration test runner.
Automatically skipped unless RUN_LIVE_E2E=1 and active LLM API keys are provided.
"""

import os
import pytest

RUN_LIVE = os.getenv("RUN_LIVE_E2E") == "1"
HAS_LLM_KEY = any(
    bool(os.getenv(k))
    for k in ["GROQ_API_KEY", "OPENROUTER_API_KEY", "CEREBRAS_API_KEY", "MISTRAL_API_KEY"]
)


@pytest.mark.e2e
@pytest.mark.skipif(
    not (RUN_LIVE and HAS_LLM_KEY),
    reason="Skipping live LLM E2E test: set RUN_LIVE_E2E=1 and API keys to enable."
)
def test_live_llm_e2e_connectivity():
    """Verify live connectivity against configured provider."""
    from core import llm_client
    assert llm_client.is_available() is True
    reply = llm_client.complete(
        "You are an academic test runner.",
        "Reply with 'OK'."
    )
    assert reply is not None
    assert len(reply) > 0
