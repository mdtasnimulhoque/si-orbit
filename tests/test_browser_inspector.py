
from pathlib import Path

from app.browser_inspector import inspect_checkout


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECKOUT_PAGE = (
    PROJECT_ROOT / "fixtures" / "buggy_sites" / "checkout.html"
)


def test_inspector_captures_checkout_bug():
    result = inspect_checkout(CHECKOUT_PAGE)

    assert result["page_loaded"] is True
    assert result["button_clicked"] is True
    assert result["browser_errors"]
    assert "null" in result["browser_errors"][0]
    assert result["message_text"] == ""

    assert result["functional_passed"] is False
    assert result["browser_healthy"] is False


def test_inspector_captures_regression_checks():
    result = inspect_checkout(CHECKOUT_PAGE)

    assert result["regression_passed"] is True

    assert all(result["regression_checks"].values())


def test_inspector_detects_successful_checkout():
    import shutil
    import tempfile

    source = CHECKOUT_PAGE.read_text(encoding="utf-8")
    fixed_source = source.replace(
        'getElementById("checkout-message")',
        'getElementById("message")',
    )

    with tempfile.TemporaryDirectory(prefix="si-orbit-test-") as temp_dir:
        fixed_file = Path(temp_dir) / "checkout.html"
        fixed_file.write_text(fixed_source, encoding="utf-8")

        result = inspect_checkout(fixed_file)

    assert result["functional_passed"] is True
    assert result["regression_passed"] is True
    assert result["browser_healthy"] is True
    assert result["browser_errors"] == []
    assert result["message_text"] == "Purchase completed successfully!"
