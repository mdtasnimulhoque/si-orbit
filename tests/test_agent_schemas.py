import pytest
from pydantic import ValidationError

from app.agent.schemas import PatchOperation, RepairProposal


def valid_proposal():
    return {
        "decision": "propose_patch",
        "summary": "Correct the mismatched checkout element reference.",
        "root_cause": (
            "The JavaScript references an element ID that is absent "
            "from the supplied HTML."
        ),
        "evidence_refs": [
            "browser_evidence",
            "source_analysis",
        ],
        "patch": {
            "operation": "replace_exact",
            "path": "checkout.html",
            "old_text": 'getElementById("checkout-message")',
            "new_text": 'getElementById("message")',
        },
        "test_plan": [
            "Replay the checkout interaction.",
            "Confirm the success message appears.",
            "Confirm no browser errors are reported.",
        ],
    }


def test_valid_patch_proposal_is_accepted():
    proposal = RepairProposal.model_validate(valid_proposal())

    assert proposal.decision == "propose_patch"
    assert proposal.patch.operation == "replace_exact"
    assert proposal.patch.path == "checkout.html"


def test_patch_cannot_be_omitted_from_patch_decision():
    data = valid_proposal()
    data["patch"] = None

    with pytest.raises(ValidationError):
        RepairProposal.model_validate(data)


def test_patch_is_rejected_for_need_more_evidence():
    data = valid_proposal()
    data["decision"] = "need_more_evidence"

    with pytest.raises(ValidationError):
        RepairProposal.model_validate(data)


def test_identical_replacement_is_rejected():
    with pytest.raises(ValidationError):
        PatchOperation(
            operation="replace_exact",
            path="checkout.html",
            old_text="same",
            new_text="same",
        )


def test_unknown_patch_operation_is_rejected():
    data = valid_proposal()
    data["patch"]["operation"] = "execute_shell"

    with pytest.raises(ValidationError):
        RepairProposal.model_validate(data)


def test_unexpected_fields_are_rejected():
    data = valid_proposal()
    data["shell_command"] = "some command"

    with pytest.raises(ValidationError):
        RepairProposal.model_validate(data)


def test_need_more_evidence_without_patch_is_valid():
    proposal = RepairProposal.model_validate({
        "decision": "need_more_evidence",
        "summary": "The available evidence is insufficient.",
        "root_cause": "The failure cannot yet be isolated.",
        "test_plan": ["Collect a browser trace."],
    })

    assert proposal.patch is None
