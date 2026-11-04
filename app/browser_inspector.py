
from pathlib import Path

from playwright.sync_api import sync_playwright


SUCCESS_MESSAGE = "Purchase completed successfully!"


def inspect_checkout(html_path: str | Path) -> dict:
    """Collect functional and regression evidence from a local checkout page."""

    browser_errors = []

    result = {
        "page_loaded": False,
        "button_clicked": False,
        "browser_errors": browser_errors,
        "message_text": None,
        "functional_checks": {},
        "regression_checks": {},
        "functional_passed": False,
        "regression_passed": False,
        "browser_healthy": False,
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        try:
            page = browser.new_page()
            page.on(
                "pageerror",
                lambda error: browser_errors.append(str(error)),
            )

            page.goto(Path(html_path).resolve().as_uri())
            result["page_loaded"] = True

            # Capture the original page state.
            order_total = page.locator(".card > p").nth(0)
            button = page.get_by_role(
                "button",
                name="Complete purchase",
            )

            baseline = {
                "title": page.title(),
                "heading": page.get_by_role(
                    "heading",
                    name="Checkout",
                ).inner_text(),
                "order_total": order_total.inner_text(),
                "button_visible": button.is_visible(),
                "button_enabled": button.is_enabled(),
                "live_region": page.locator("#message").get_attribute(
                    "aria-live"
                ),
            }

            button.click()
            result["button_clicked"] = True

            result["message_text"] = page.locator("#message").inner_text()

            # Read the same element after interaction, even if its text changed.
            after = {
                "title": page.title(),
                "heading": page.get_by_role(
                    "heading",
                    name="Checkout",
                ).inner_text(),
                "order_total": order_total.inner_text(),
                "button_visible": button.is_visible(),
                "button_enabled": button.is_enabled(),
                "live_region": page.locator("#message").get_attribute(
                    "aria-live"
                ),
            }

            result["functional_checks"] = {
                "page_loaded": result["page_loaded"],
                "button_clicked": result["button_clicked"],
                "success_message": (
                    result["message_text"] == SUCCESS_MESSAGE
                ),
            }

            result["regression_checks"] = {
                "page_title_unchanged": (
                    baseline["title"] == after["title"]
                ),
                "heading_unchanged": (
                    baseline["heading"] == after["heading"]
                ),
                "order_total_unchanged": (
                    baseline["order_total"] == after["order_total"]
                ),
                "button_remains_visible": (
                    baseline["button_visible"]
                    and after["button_visible"]
                ),
                "button_remains_enabled": (
                    baseline["button_enabled"]
                    and after["button_enabled"]
                ),
                "live_region_preserved": (
                    baseline["live_region"] == "polite"
                    and after["live_region"] == "polite"
                ),
            }

            result["functional_passed"] = all(
                result["functional_checks"].values()
            )

            result["regression_passed"] = all(
                result["regression_checks"].values()
            )

            result["browser_healthy"] = not browser_errors

        finally:
            browser.close()

    return result
