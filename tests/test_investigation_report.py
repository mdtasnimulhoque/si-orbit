
from app.investigation_report import build_investigation_report


def test_report_separates_observations_from_hypotheses():
    evidence = {
        "page_loaded": True,
        "button_clicked": True,
        "browser_errors": [
            "Cannot set properties of null (setting 'textContent')"
        ],
        "message_text": "",
    }

    report = build_investigation_report(evidence)

    assert report["project"] == "SI ORBIT"
    assert any("page loaded" in item for item in report["observations"])
    assert any("remained empty" in item for item in report["observations"])
    assert report["hypotheses"]
    assert report["verified_findings"] == []
    assert report["verification_status"] == "Not yet verified"
