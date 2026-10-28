
from pathlib import Path
from tempfile import TemporaryDirectory

from app.browser_inspector import inspect_checkout
from app.investigation_report import build_investigation_report
from app.root_cause_verifier import verify_element_id_mismatch


def verify_proposed_fix(html_path: str | Path) -> dict:
    """Test whether correcting the element ID resolves the browser error."""

    original_path = Path(html_path)
    original_html = original_path.read_text(encoding="utf-8")
    source_check = verify_element_id_mismatch(original_path)

    result = {
        "attempted": False,
        "passed": False,
        "browser_errors": [],
        "message_text": None,
        "reason": None,
    }

    incorrect_lookup = 'getElementById("checkout-message")'

    if (
        "checkout-message" not in source_check["missing_ids"]
        or incorrect_lookup not in original_html
    ):
        result["reason"] = "The expected element ID mismatch was not found."
        return result

    corrected_html = original_html.replace(
        incorrect_lookup,
        'getElementById("message")',
    )
    result["attempted"] = True

    try:
        with TemporaryDirectory() as temporary_directory:
            corrected_path = Path(temporary_directory) / "checkout_fixed.html"
            corrected_path.write_text(corrected_html, encoding="utf-8")
            browser_result = inspect_checkout(corrected_path)

        result["browser_errors"] = browser_result["browser_errors"]
        result["message_text"] = browser_result["message_text"]
        result["passed"] = (
            browser_result["page_loaded"]
            and browser_result["button_clicked"]
            and not browser_result["browser_errors"]
            and browser_result["message_text"]
            == "Purchase completed successfully!"
        )

        if not result["passed"]:
            result["reason"] = "The corrected page failed browser verification."

    except Exception as error:
        result["reason"] = f"Browser verification failed: {error}"

    return result


def investigate_checkout(html_path: str | Path) -> dict:
    """Collect evidence, inspect the source, and verify a proposed fix."""

    evidence = inspect_checkout(html_path)
    source_check = verify_element_id_mismatch(html_path)
    report = build_investigation_report(evidence)
    fix_verification = verify_proposed_fix(html_path)

    if source_check["mismatch_detected"]:
        report["observations"].append(
            "Source inspection found JavaScript element IDs "
            "that are absent from the HTML."
        )

    if source_check["finding"]:
        report["hypotheses"].append(source_check["finding"])

    if fix_verification["passed"]:
        report["verified_findings"].append(
            "Correcting the element ID made the checkout success message "
            "appear without browser errors in the corrected test page."
        )
        report["verification_status"] = "Fix verified in browser"
    elif fix_verification["attempted"]:
        report["verification_status"] = "Fix not verified"

    return {
        "evidence": evidence,
        "source_check": source_check,
        "fix_verification": fix_verification,
        "report": report,
    }
