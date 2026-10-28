from types import SimpleNamespace

import httpx
import pytest

from app.meta_model_client import MetaModelError, analyze_evidence


class FakeResponse:
    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.data


class FakeHTTPClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.response


def test_missing_configuration_sends_no_request(monkeypatch):
    monkeypatch.delenv("SI_ORBIT_META_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("SI_ORBIT_META_ENDPOINT_TOKEN", raising=False)
    client = FakeHTTPClient(FakeResponse())

    with pytest.raises(MetaModelError, match="No request was sent"):
        analyze_evidence({}, {}, client=client)

    assert client.calls == []


def test_successful_response_is_not_marked_verified():
    client = FakeHTTPClient(
        FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "The likely cause is a mismatched element ID."
                        }
                    }
                ]
            }
        )
    )

    result = analyze_evidence(
        {"browser_errors": ["TypeError"]},
        {"missing_ids": ["checkout-message"]},
        base_url="https://example.invalid",
        api_key="test-token",
        client=client,
    )

    assert result["status"] == "completed"
    assert result["verified"] is False
    assert "mismatched element ID" in result["analysis"]
    assert len(client.calls) == 1
    assert client.calls[0]["url"] == (
        "https://example.invalid/v1/chat/completions"
    )


def test_http_error_is_reported():
    client = FakeHTTPClient(
        FakeResponse(error=httpx.HTTPStatusError(
            "server error",
            request=httpx.Request(
                "POST", "https://example.invalid/v1/chat/completions"
            ),
            response=httpx.Response(
                500,
                request=httpx.Request(
                    "POST", "https://example.invalid/v1/chat/completions"
                ),
            ),
        ))
    )

    with pytest.raises(MetaModelError, match="Meta inference failed"):
        analyze_evidence(
            {},
            {},
            base_url="https://example.invalid",
            api_key="test-token",
            client=client,
        )
