
from pathlib import Path

from playwright.sync_api import sync_playwright


def inspect_checkout(html_path: str | Path) -> dict:
    """Open a local checkout page and collect browser evidence."""

    browser_errors = []
    result = {
        "page_loaded": False,
        "button_clicked": False,
        "browser_errors": browser_errors,
        "message_text": None,
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        try:
            page = browser.new_page()
            page.on("pageerror", lambda error: browser_errors.append(str(error)))

            page.goto(Path(html_path).resolve().as_uri())
            result["page_loaded"] = True

            page.get_by_role(
                "button", name="Complete purchase"
            ).click()
            result["button_clicked"] = True

            result["message_text"] = page.locator("#message").inner_text()

        finally:
            browser.close()

    return result
