from app.reasoning_stage import add_ai_reasoning


def sample_investigation():
    return {
        "evidence": {"browser_errors": ["example error"]},
        "source_check": {"missing_ids": ["checkout-message"]},
        "fix_verification": {"attempted": True, "passed": True},
        "report": {"verified_findings": ["Browser test passed"]},
    }


def test_reasoning_is_disabled_by_default():
    original = sample_investigation()

    result = add_ai_reasoning(original)

    assert result["ai_reasoning"]["status"] == "not_requested"
    assert result["ai_reasoning"]["verified"] is False
    assert result["fix_verification"] == original["fix_verification"]
    assert result["report"] == original["report"]


def test_reasoning_attaches_analysis_without_changing_verification():
    original = sample_investigation()

    def fake_analyzer(evidence, source_check):
        assert evidence["browser_errors"]
        assert source_check["missing_ids"]
        return {
            "status": "completed",
            "analysis": "The element ID may be mismatched.",
            "verified": False,
        }

    result = add_ai_reasoning(
        original,
        enabled=True,
        analyzer=fake_analyzer,
    )

    assert result["ai_reasoning"]["status"] == "completed"
    assert "mismatched" in result["ai_reasoning"]["analysis"]
    assert result["ai_reasoning"]["verified"] is False
    assert result["fix_verification"]["passed"] is True
    assert result["report"]["verified_findings"] == ["Browser test passed"]


def test_reasoning_failure_does_not_erase_investigation():
    original = sample_investigation()

    def failing_analyzer(evidence, source_check):
        raise RuntimeError("simulated model failure")

    result = add_ai_reasoning(
        original,
        enabled=True,
        analyzer=failing_analyzer,
    )

    assert result["ai_reasoning"]["status"] == "unavailable"
    assert "simulated model failure" in result["ai_reasoning"]["error"]
    assert result["fix_verification"]["passed"] is True
    assert result["report"]["verified_findings"] == ["Browser test passed"]
