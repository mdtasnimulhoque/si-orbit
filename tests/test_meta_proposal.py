
import json

import pytest

from app.agent.schemas import RepairProposal
from app.meta_model_client import MetaModelError, propose_repair


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": self.content
                    }
                }
            ]
        }


class FakeHTTPClient:
    def __init__(self, content):
        self.response = FakeResponse(content)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append({
            "url": url,
            **kwargs,
        })
        return self.response


def valid_proposal():
    return {
        "decision": "propose_patch",
        "summary": "Correct the checkout element reference.",
        "root_cause": (
            "JavaScript references an element ID absent from HTML."
        ),
        "evidence_refs": ["source_analysis"],
        "patch": {
            "operation": "replace_exact",
            "path": "checkout.html",
            "old_text": 'getElementById("checkout-message")',
            "new_text": 'getElementById("message")',
        },
        "test_plan": [
            "Replay the checkout interaction."
        ],
    }


def test_structured_proposal_is_validated():
    client = FakeHTTPClient(json.dumps(valid_proposal()))

    result = propose_repair(
        {"browser_errors": ["TypeError"]},
        {"missing_ids": ["checkout-message"]},
        source_text='getElementById("checkout-message")',
        base_url="https://example.invalid",
        api_key="test-token",
        client=client,
    )

    assert isinstance(result, RepairProposal)
    assert result.decision == "propose_patch"
    assert result.patch.path == "checkout.html"
    assert len(client.calls) == 1


def test_malformed_json_is_rejected():
    client = FakeHTTPClient("not JSON")

    with pytest.raises(MetaModelError):
        propose_repair(
            {},
            {},
            base_url="https://example.invalid",
            api_key="test-token",
            client=client,
        )


def test_invalid_schema_is_rejected():
    proposal = valid_proposal()
    proposal["unexpected_field"] = "not allowed"

    client = FakeHTTPClient(json.dumps(proposal))

    with pytest.raises(MetaModelError):
        propose_repair(
            {},
            {},
            source_text='getElementById("checkout-message")',
            base_url="https://example.invalid",
            api_key="test-token",
            client=client,
        )


def test_unsupported_patch_path_is_rejected():
    proposal = valid_proposal()
    proposal["patch"]["path"] = "../outside.html"

    client = FakeHTTPClient(json.dumps(proposal))

    with pytest.raises(MetaModelError):
        propose_repair(
            {},
            {},
            source_text='getElementById("checkout-message")',
            base_url="https://example.invalid",
            api_key="test-token",
            client=client,
        )
