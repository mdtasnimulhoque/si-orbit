from pathlib import Path

from app.agent.repair_loop import run_repair_cycle
from app.agent.schemas import RepairProposal


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "buggy_sites"
    / "checkout.html"
)


def local_test_proposal(**kwargs):
    """Deterministic test proposal; this is not a model response."""

    return RepairProposal.model_validate({
        "decision": "propose_patch",
        "summary": "Correct the checkout element reference.",
        "root_cause": "JavaScript references a missing HTML element ID.",
        "evidence_refs": ["source_analysis"],
        "patch": {
            "operation": "replace_exact",
            "path": "checkout.html",
            "old_text": 'getElementById("checkout-message")',
            "new_text": 'getElementById("message")',
        },
        "test_plan": [
            "Replay checkout interaction.",
            "Check for browser errors.",
            "Check the success message.",
        ],
    })


def test_repair_cycle_verifies_local_test_proposal():
    original_before = FIXTURE.read_bytes()

    result = run_repair_cycle(
        FIXTURE,
        local_test_proposal,
    )

    assert result["status"] == "verified"
    assert result["verified"] is True
    assert result["model_generated"] is False
    assert result["attempt_count"] == 1
    assert result["original_unchanged"] is True
    assert result["final_evidence"]["message_text"] == (
        "Purchase completed successfully!"
    )
    assert "checkout-message" in result["patch_diff"]
    assert "getElementById" in result["patch_diff"]

    assert FIXTURE.read_bytes() == original_before


def test_repair_cycle_can_request_more_evidence():
    def provider(**kwargs):
        return RepairProposal.model_validate({
            "decision": "need_more_evidence",
            "summary": "A stack trace is needed.",
            "root_cause": "The current evidence is insufficient.",
            "test_plan": ["Collect a browser trace."],
        })

    result = run_repair_cycle(FIXTURE, provider)

    assert result["status"] == "inconclusive"
    assert result["verified"] is False
    assert result["attempt_count"] == 1
    assert result["attempts"][0]["status"] == "needs_more_evidence"
    assert result["original_unchanged"] is True


def test_repair_cycle_rejects_unsafe_patch():
    def provider(**kwargs):
        proposal = local_test_proposal()
        proposal.patch.path = "../outside.html"
        return proposal

    result = run_repair_cycle(FIXTURE, provider)

    assert result["status"] == "failed"
    assert result["attempts"][0]["status"] == "patch_rejected"
    assert result["original_unchanged"] is True


def test_repair_cycle_enforces_three_attempt_limit():
    try:
        run_repair_cycle(
            FIXTURE,
            local_test_proposal,
            max_attempts=4,
        )
    except ValueError as exc:
        assert "between 1 and 3" in str(exc)
    else:
        raise AssertionError("Expected max-attempt validation to fail.")


def test_repair_cycle_rejects_safe_but_incorrect_patch():
    """A patch can be safely applied but still fail functional verification."""

    def incorrect_proposal(**kwargs):
        return RepairProposal.model_validate({
            "decision": "propose_patch",
            "summary": "Change the missing element reference.",
            "root_cause": "The JavaScript selector is incorrect.",
            "evidence_refs": ["source_analysis", "source_text"],
            "patch": {
                "operation": "replace_exact",
                "path": "checkout.html",
                "old_text": 'getElementById("checkout-message")',
                "new_text": 'getElementById("still-missing")',
            },
            "test_plan": [
                "Replay the checkout interaction.",
                "Check browser errors.",
                "Check the success message.",
            ],
        })

    original_before = FIXTURE.read_bytes()

    result = run_repair_cycle(
        FIXTURE,
        incorrect_proposal,
        max_attempts=1,
    )

    assert result["attempt_count"] == 1
    assert result["attempts"][0]["status"] == "verification_failed"
    assert result["status"] == "failed"
    assert result["verified"] is False
    assert result["final_evidence"]["browser_errors"]
    assert result["final_evidence"]["message_text"] != (
        "Purchase completed successfully!"
    )
    assert result["original_unchanged"] is True
    assert FIXTURE.read_bytes() == original_before
def test_repair_cycle_recovers_after_failed_verification():
    """A failed first repair can be corrected using refreshed evidence."""

    received_context = []

    def retry_provider(**kwargs):
        received_context.append({
            "attempt": kwargs["attempt"],
            "evidence": kwargs["evidence"],
            "previous_attempts": list(kwargs["previous_attempts"]),
        })

        if kwargs["attempt"] == 1:
            old_text = 'getElementById("checkout-message")'
            new_text = 'getElementById("still-missing")'
        else:
            old_text = 'getElementById("still-missing")'
            new_text = 'getElementById("message")'

        return RepairProposal.model_validate({
            "decision": "propose_patch",
            "summary": "Correct the checkout selector.",
            "root_cause": "The JavaScript selector references a missing ID.",
            "evidence_refs": ["source_analysis", "source_text"],
            "patch": {
                "operation": "replace_exact",
                "path": "checkout.html",
                "old_text": old_text,
                "new_text": new_text,
            },
            "test_plan": [
                "Replay the checkout interaction.",
                "Check browser errors.",
                "Check the success message.",
            ],
        })

    original_before = FIXTURE.read_bytes()

    result = run_repair_cycle(
        FIXTURE,
        retry_provider,
        max_attempts=2,
    )

    assert result["status"] == "verified"
    assert result["verified"] is True
    assert result["attempt_count"] == 2

    assert result["attempts"][0]["status"] == "verification_failed"
    assert result["attempts"][1]["status"] == "verified"

    assert received_context[1]["attempt"] == 2
    assert len(received_context[1]["previous_attempts"]) == 1
    assert received_context[1]["previous_attempts"][0]["status"] == (
        "verification_failed"
    )

    assert received_context[1]["evidence"]["browser_errors"]
    assert received_context[1]["evidence"]["message_text"] != (
    "Purchase completed successfully!"
)

    assert result["final_evidence"]["message_text"] == (
        "Purchase completed successfully!"
    )

    assert result["original_unchanged"] is True
    assert FIXTURE.read_bytes() == original_before


def test_repair_cycle_rejects_functional_fix_that_breaks_order_total():
    """Reject a successful checkout interaction that introduces a regression."""

    original_before = FIXTURE.read_bytes()

    old_function = '''function completeCheckout() {
      const message = document.getElementById("checkout-message");
      message.textContent = "Purchase completed successfully!";
    }'''

    regressive_function = '''function completeCheckout() {
      const message = document.getElementById("message");
      message.textContent = "Purchase completed successfully!";
      document.querySelector(".card > p").textContent =
        "Demo order total: $0.00";
    }'''

    def regressive_proposal(**kwargs):
        return RepairProposal.model_validate({
            "decision": "propose_patch",
            "summary": "Fix checkout but accidentally change the order total.",
            "root_cause": "The checkout selector references a missing element.",
            "evidence_refs": ["source_analysis", "source_text"],
            "patch": {
                "operation": "replace_exact",
                "path": "checkout.html",
                "old_text": old_function,
                "new_text": regressive_function,
            },
            "test_plan": [
                "Replay checkout interaction.",
                "Verify success message.",
                "Verify order total remains unchanged.",
            ],
        })

    result = run_repair_cycle(
        FIXTURE,
        regressive_proposal,
        max_attempts=1,
    )

    evidence = result["final_evidence"]

    assert evidence["message_text"] == "Purchase completed successfully!"
    assert evidence["functional_passed"] is True
    assert evidence["regression_checks"]["order_total_unchanged"] is False
    assert evidence["regression_passed"] is False
    assert evidence["browser_healthy"] is True

    assert result["status"] == "failed"
    assert result["verified"] is False
    assert result["attempts"][0]["status"] == "verification_failed"

    assert result["original_unchanged"] is True
    assert FIXTURE.read_bytes() == original_before
