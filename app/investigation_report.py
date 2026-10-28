
def build_investigation_report(browser_evidence: dict) -> dict:
    """Turn browser observations into a structured investigation report."""

    browser_errors = browser_evidence.get("browser_errors", [])
    message_text = browser_evidence.get("message_text")
    page_loaded = browser_evidence.get("page_loaded", False)
    button_clicked = browser_evidence.get("button_clicked", False)

    observations = []

    if page_loaded:
        observations.append("The checkout page loaded successfully.")

    if button_clicked:
        observations.append("The checkout button was clicked.")

    if message_text == "":
        observations.append("The checkout message remained empty.")

    for error in browser_errors:
        observations.append(f"Browser reported a JavaScript error: {error}")

    hypotheses = []

    if any("textContent" in error and "null" in error for error in browser_errors):
        hypotheses.append(
            "The JavaScript may be trying to update an HTML element "
            "that it could not find."
        )

    return {
        "project": "SI ORBIT",
        "observations": observations,
        "hypotheses": hypotheses,
        "verified_findings": [],
        "verification_status": "Not yet verified",
    }
