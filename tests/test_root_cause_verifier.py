
from pathlib import Path

from app.browser_inspector import inspect_checkout
from app.root_cause_verifier import verify_element_id_mismatch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECKOUT_PAGE = PROJECT_ROOT / "fixtures" / "buggy_sites" / "checkout.html"


def test_verifier_detects_checkout_element_id_mismatch():
    result = verify_element_id_mismatch(CHECKOUT_PAGE)

    assert result["html_ids"]
    assert "message" in result["html_ids"]
    assert "checkout-message" in result["javascript_ids"]
    assert "checkout-message" in result["missing_ids"]
    assert result["mismatch_detected"] is True
    assert result["finding"] is not None


def test_corrected_checkout_page_works_in_browser(tmp_path):
    # Read the original buggy page without modifying it.
    original_html = CHECKOUT_PAGE.read_text(encoding="utf-8")

    # Correct the mismatched ID in a temporary copy.
    corrected_html = original_html.replace(
        'getElementById("checkout-message")',
        'getElementById("message")',
    )

    corrected_page = tmp_path / "checkout_fixed.html"
    corrected_page.write_text(corrected_html, encoding="utf-8")

    # Run the corrected page in a real Chromium browser.
    result = inspect_checkout(corrected_page)

    # Verify that the correction resolves the observed failure.
    assert result["page_loaded"] is True
    assert result["button_clicked"] is True
    assert result["browser_errors"] == []
    assert result["message_text"] == "Purchase completed successfully!"

    # Confirm that the original buggy page remains unchanged.
    assert CHECKOUT_PAGE.read_text(encoding="utf-8") == original_html
