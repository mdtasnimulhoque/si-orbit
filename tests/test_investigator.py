
from pathlib import Path

from app.investigator import investigate_checkout


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECKOUT_PAGE = PROJECT_ROOT / "fixtures" / "buggy_sites" / "checkout.html"


def test_investigator_collects_evidence_and_builds_report():
    result = investigate_checkout(CHECKOUT_PAGE)

    evidence = result["evidence"]
    source_check = result["source_check"]
    fix_verification = result["fix_verification"]
    report = result["report"]

    assert evidence["page_loaded"] is True
    assert evidence["button_clicked"] is True
    assert evidence["browser_errors"]

    assert source_check["mismatch_detected"] is True
    assert "checkout-message" in source_check["missing_ids"]

    assert fix_verification["attempted"] is True
    assert fix_verification["passed"] is True
    assert fix_verification["browser_errors"] == []
    assert (
        fix_verification["message_text"]
        == "Purchase completed successfully!"
    )

    assert report["observations"]
    assert report["hypotheses"]
    assert report["verified_findings"]
    assert report["verification_status"] == "Fix verified in browser"
