"""Optional AI reasoning stage for SI ORBIT investigations."""

import os
from typing import Any, Callable

from app.meta_model_client import analyze_evidence


def add_ai_reasoning(
    investigation: dict[str, Any],
    *,
    enabled: bool = False,
    analyzer: Callable[..., dict[str, Any]] = analyze_evidence,
) -> dict[str, Any]:
    """Attach AI analysis without changing deterministic verification results."""
    result = dict(investigation)
    result["ai_reasoning"] = {
        "enabled": enabled,
        "status": "not_requested",
        "analysis": None,
        "verified": False,
        "error": None,
    }

    if not enabled:
        return result

    # Real model calls stay blocked unless explicitly enabled by the server.
    # Injected test analyzers remain usable for offline tests.
    if (
        analyzer is analyze_evidence
        and os.getenv("SI_ORBIT_ALLOW_REAL_INFERENCE") != "true"
    ):
        result["ai_reasoning"] = {
            "enabled": True,
            "status": "blocked_by_safety_gate",
            "analysis": None,
            "verified": False,
            "error": "Real inference is disabled by server configuration.",
        }
        return result

    try:
        result["ai_reasoning"] = {
            **analyzer(
                result.get("evidence", {}),
                result.get("source_check", {}),
            ),
            "enabled": True,
            "error": None,
        }
    except Exception as exc:
        # Preserve the original investigation if AI reasoning fails.
        result["ai_reasoning"] = {
            "enabled": True,
            "status": "unavailable",
            "analysis": None,
            "verified": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    return result
