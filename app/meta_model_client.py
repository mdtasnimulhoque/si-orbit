"""Meta model client for SI ORBIT.

Real inference is disabled unless explicitly configured.
Tests should inject a mocked HTTP client.
"""

import os
from typing import Any

import httpx


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
    """Ask a Meta model to analyze collected evidence.

    This function does not claim that a proposed fix is verified.
    Browser-based verification remains a separate step.
    """
    endpoint = (
        base_url or os.getenv("SI_ORBIT_META_ENDPOINT_URL", "")
    ).rstrip("/")
    token = api_key or os.getenv("SI_ORBIT_META_ENDPOINT_TOKEN", "")

    if not endpoint or not token:
        raise MetaModelError(
            "Meta inference is not configured. No request was sent."
        )

    payload = {
        "model": "meta-models/Muse-Spark-Open-816B-A42B",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are SI ORBIT, a cautious software debugging assistant. "
                    "Analyze only the supplied evidence. Distinguish observations "
                    "from hypotheses. Do not claim a fix was tested or verified "
                    "unless the supplied evidence proves it. Return a concise "
                    "root-cause hypothesis, supporting evidence, and a proposed "
                    "next diagnostic step."
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
        "temperature": 0.1,
        "max_tokens": 500,
    }

    url = f"{endpoint}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        if client is not None:
            response = client.post(
                url, headers=headers, json=payload, timeout=30.0
            )
        else:
            with httpx.Client(timeout=30.0) as http_client:
                response = http_client.post(
                    url, headers=headers, json=payload
                )

        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]

        if not isinstance(content, str) or not content.strip():
            raise MetaModelError("Meta model returned an empty response.")

        return {
            "status": "completed",
            "model": payload["model"],
            "analysis": content.strip(),
            "verified": False,
        }

    except MetaModelError:
        raise
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise MetaModelError(
            f"Meta inference failed: {type(exc).__name__}: {exc}"
        ) from exc
