
from pathlib import Path

from app.browser_inspector import inspect_checkout


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECKOUT_PAGE = PROJECT_ROOT / "fixtures" / "buggy_sites" / "checkout.html"


def test_inspector_captures_checkout_bug():
    result = inspect_checkout(CHECKOUT_PAGE)

    assert result["page_loaded"] is True
    assert result["button_clicked"] is True
    assert result["browser_errors"]
    assert "null" in result["browser_errors"][0]
    assert result["message_text"] == ""
