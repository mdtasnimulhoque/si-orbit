
"""Meta Model API client for SI ORBIT.

Analyzes investigation evidence without claiming that a proposed fix
has been tested or verified.
"""

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = "https://api.meta.ai/v1"
MODEL_ID = "muse-spark-1.3"

_PLACEHOLDER_KEYS = {
    "your_actual_meta_api_key_here",
    "your_meta_api_key_here",
    "your_api_key",
}


class MetaModelError(RuntimeError):
    """Raised when Meta model configuration or inference fails."""


def analyze_evidence(
    evidence: dict[str, Any],
    source_check: dict[str, Any],
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    client: Any = None,
) -> dict[str, Any]:
    """Analyze investigation evidence without claiming a fix is verified."""

    endpoint = (
        base_url
        or os.getenv("SI_ORBIT_META_ENDPOINT_URL")
        or DEFAULT_BASE_URL
    ).strip().rstrip("/")

    token = (
        api_key
        or os.getenv("MODEL_API_KEY")
        or os.getenv("SI_ORBIT_META_ENDPOINT_TOKEN")
        or ""
    ).strip()

    if not token or token.casefold() in _PLACEHOLDER_KEYS:
        raise MetaModelError(
            "Meta API key is missing or is a placeholder. No request was sent."
        )

    if not endpoint.startswith("https://"):
        raise MetaModelError(
            "The Meta API endpoint must start with https://."
        )

    if not endpoint.endswith("/v1"):
        endpoint = f"{endpoint}/v1"

    url = f"{endpoint}/chat/completions"

    payload = {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are SI ORBIT, a cautious software debugging assistant. "
                    "Analyze only the supplied evidence. Clearly separate "
                    "observations from hypotheses. Never claim a fix was "
                    "tested or verified unless the supplied evidence proves "
                    "it. Return a concise root-cause hypothesis, supporting "
                    "evidence, and the next diagnostic step."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Analyze this software investigation evidence:\n"
                    f"Browser evidence: {evidence}\n"
                    f"Source analysis: {source_check}"
                ),
            },
        ],
        "max_completion_tokens": 500,
    }

    headers = {"Authorization": f"Bearer {token}"}

    try:
        if client is not None:
            response = client.post(
                url,
                headers=headers,
                json=payload,
                timeout=30.0,
            )
        else:
            with httpx.Client(timeout=30.0) as http_client:
                response = http_client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict):
            raise MetaModelError(
                "Meta model returned an unexpected response format."
            )

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise MetaModelError(
                "Meta model response did not contain any choices."
            )

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise MetaModelError(
                "Meta model returned an invalid choice."
            )

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise MetaModelError(
                "Meta model response did not contain a valid message."
            )

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise MetaModelError(
                "Meta model returned an empty or unsupported response."
            )

        return {
            "status": "completed",
            "model": MODEL_ID,
            "analysis": content.strip(),
            "verified": False,
        }

    except MetaModelError:
        raise
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise MetaModelError(
            f"Meta inference failed: {type(exc).__name__}: {exc}"
        ) from exc
