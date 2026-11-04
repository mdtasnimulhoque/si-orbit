from fastapi.testclient import TestClient

import app.main as main


client = TestClient(main.app)


def test_agent_checkout_is_blocked_without_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("SI_ORBIT_ALLOW_REAL_INFERENCE", raising=False)

    def unexpected_repair_call(*args, **kwargs):
        raise AssertionError("Repair cycle must not run while inference is disabled.")

    monkeypatch.setattr(main, "run_repair_cycle", unexpected_repair_call)

    response = client.post(
        "/api/investigate",
        json={"mode": "agent_checkout"},
    )

    assert response.status_code == 503
    assert "Live Muse Spark repair is disabled" in response.json()["detail"]


def test_agent_checkout_runs_when_explicitly_enabled(monkeypatch):
    monkeypatch.setenv("SI_ORBIT_ALLOW_REAL_INFERENCE", "true")

    calls = []

    def fake_repair_cycle(html_path, proposal_provider):
        calls.append(html_path)

        return {
            "final_evidence": {
                "browser_errors": [],
                "message_text": None,
            },
            "source_check": {},
            "verified": False,
            "attempts": [],
            "reason": "Mocked repair cycle.",
        }

    monkeypatch.setattr(main, "run_repair_cycle", fake_repair_cycle)

    response = client.post(
        "/api/investigate",
        json={"mode": "agent_checkout"},
    )

    assert response.status_code == 200
    assert calls == [main.CHECKOUT_PAGE]
    assert response.json()["repair_cycle"]["reason"] == "Mocked repair cycle."


def test_default_investigation_mode_is_deterministic():
    request = main.InvestigationRequest()

    assert request.mode == "checkout"

def test_custom_muse_analysis_is_blocked_without_opt_in(monkeypatch):
    monkeypatch.delenv("SI_ORBIT_ALLOW_REAL_INFERENCE", raising=False)

    def unexpected_model_call(**kwargs):
        raise AssertionError("Model must not be called while inference is disabled.")

    monkeypatch.setattr(main, "diagnose_custom_evidence", unexpected_model_call)

    response = client.post(
        "/api/investigate",
        json={
            "mode": "custom_evidence",
            "problem_description": "The checkout button does not work.",
            "error_logs": "TypeError: Cannot set properties of null",
            "source_code": 'document.getElementById("checkout-message").textContent = "Done";',
            "enable_ai_reasoning": True,
        },
    )

    assert response.status_code == 503
    assert "Live Muse Spark analysis is disabled" in response.json()["detail"]


def test_custom_muse_analysis_receives_all_submitted_evidence(monkeypatch):
    from app.agent.schemas import CustomDiagnosis

    monkeypatch.setenv("SI_ORBIT_ALLOW_REAL_INFERENCE", "true")

    calls = []

    def fake_diagnosis(**kwargs):
        calls.append(kwargs)
        return CustomDiagnosis(
            decision="diagnosis",
            summary="The JavaScript references an element that may be absent.",
            root_cause="The submitted HTML does not contain the referenced element.",
            evidence_refs=["problem_description", "error_logs", "source_code"],
            confidence="medium",
            suggested_fix="Add the missing element or correct the JavaScript ID.",
            replacement_code='<div id="checkout-message"></div>',
            test_plan=["Confirm the element exists before accessing textContent."],
        )

    monkeypatch.setattr(main, "diagnose_custom_evidence", fake_diagnosis)

    response = client.post(
        "/api/investigate",
        json={
            "mode": "custom_evidence",
            "problem_description": "The checkout button does not work.",
            "error_logs": "TypeError: Cannot set properties of null",
            "source_code": 'document.getElementById("checkout-message").textContent = "Done";',
            "enable_ai_reasoning": True,
        },
    )

    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0]["problem_description"] == "The checkout button does not work."
    assert calls[0]["error_logs"] == "TypeError: Cannot set properties of null"
    assert "checkout-message" in calls[0]["source_code"]
    assert isinstance(calls[0]["static_analysis"], dict)

    result = response.json()
    assert result["custom_diagnosis"]["decision"] == "diagnosis"
    assert result["custom_diagnosis"]["replacement_code"] == (
        '<div id="checkout-message"></div>'
    )
    assert result["ai_reasoning"]["verified"] is False
    assert result["fix_verification"]["passed"] is False
