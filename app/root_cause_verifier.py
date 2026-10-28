
import re
from pathlib import Path


def verify_element_id_mismatch(html_path: str | Path) -> dict:
    """Check whether JavaScript requests an element ID absent from the HTML."""

    html = Path(html_path).read_text(encoding="utf-8")

    # Collect IDs defined in HTML elements.
    html_ids = re.findall(
        r'\bid\s*=\s*["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )

    # Collect IDs requested by JavaScript getElementById() calls.
    javascript_ids = re.findall(
        r'getElementById\(\s*["\']([^"\']+)["\']\s*\)',
        html,
    )

    missing_ids = [
        element_id
        for element_id in javascript_ids
        if element_id not in html_ids
    ]

    if missing_ids:
        finding = (
            "JavaScript requests element ID(s) that do not exist "
            f"in the HTML: {', '.join(missing_ids)}."
        )
    else:
        finding = None

    return {
        "html_ids": html_ids,
        "javascript_ids": javascript_ids,
        "missing_ids": missing_ids,
        "mismatch_detected": bool(missing_ids),
        "finding": finding,
    }
