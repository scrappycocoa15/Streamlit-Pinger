#!/usr/bin/env python3
"""
Streamlit App Pinger
────────────────────
Keeps Streamlit Community Cloud apps awake by pinging them before the
7-day inactivity sleep kicks in.

Usage
-----
  1. Add your app URLs to the APPS list below.
  2. Run manually:        python ping_apps.py
  3. Or let GitHub Actions run it on a schedule (see ping.yml).

How it works
------------
Streamlit Community Cloud sleeps an app after ~7 days with no traffic.
This script uses a headless Chromium browser to visit each URL every 3
days, exactly as a real user would. If an app is awake, it checks out
fine. If it's sleeping, the browser sees the sleep page (which a plain
HTTP GET cannot), clicks "Yes, get this app back up!", and waits for the
live app to load — resetting the inactivity timer properly.
"""

import sys
from datetime import datetime, timezone

# ── Add your app URLs here ────────────────────────────────────────────────────

APPS = [
    "https://watermark-appglobal-smb.streamlit.app",
    "https://smb-watermark-tool-usclientsales.streamlit.app",
    "https://global-smb-client-sales-performance-dashboard.streamlit.app",
    "https://smb-client-sales-performance-dashboard-fnbeugwlcwmxwvtgwneup3.streamlit.app",
    "https://account-reassignment-app-xbtckvpir.streamlit.app",
    "https://acct-transition-app-bw44z4vo94mqw2mgsubkqc.streamlit.app",
    "https://former-customers-pbmqfhyxzucvgnltgrawxy.streamlit.app",
    "https://smb-account-assignment-validator-v2.streamlit.app",
]

# ── Settings ──────────────────────────────────────────────────────────────────

NAV_TIMEOUT_SECONDS  = 30   # Seconds to wait for the page to load
WAKE_TIMEOUT_SECONDS = 120  # Seconds to wait for a sleeping app to wake up

# ── Ping logic ────────────────────────────────────────────────────────────────

def ping(page, url: str) -> tuple[bool, int, str]:
    """
    Navigate to url with a headless browser page and return (ok, status, msg).

    Streamlit's sleep page is JavaScript-rendered, so a plain HTTP GET
    never sees the "gone to sleep" text — the browser does. Using Playwright
    means we detect sleep reliably and can click the wake-up button.
    """
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_SECONDS * 1_000)
        status_code = response.status if response else 0

        # Wait for React to render — either the live app or the sleep page.
        # "domcontentloaded" fires before React paints anything, so without
        # this wait the sleep text isn't in the DOM yet when we check.
        # NOTE: text= is a Playwright-only selector and can't be mixed with
        # CSS in a single string — use .or_() to combine the two locators.
        try:
            page.locator("[data-testid='stApp']").or_(
                page.locator("text=gone to sleep")
            ).first.wait_for(timeout=15_000)
        except PlaywrightTimeoutError:
            pass  # Neither appeared within 15s — proceed with whatever is there

        # Detect the sleep page from the rendered content
        if page.locator("text=gone to sleep").count() > 0:
            print(f"          App is sleeping — trying to wake it up...")

            # Click "Yes, get this app back up!"
            try:
                page.locator("button:has-text('Yes')").first.click(timeout=5_000)
            except PlaywrightTimeoutError:
                pass  # No button — some versions auto-wake on navigation

            # Wait for the live app's root element to appear
            try:
                page.wait_for_selector(
                    "[data-testid='stApp']",
                    timeout=WAKE_TIMEOUT_SECONDS * 1_000,
                )
                return True, status_code, "Woken up successfully"
            except PlaywrightTimeoutError:
                if "gone to sleep" not in page.content().lower():
                    return True, status_code, "Woken up (app responded)"
                return False, status_code, f"Did not wake within {WAKE_TIMEOUT_SECONDS}s"

        # App is awake
        ok = status_code < 500
        return ok, status_code, f"HTTP {status_code}"

    except PlaywrightTimeoutError:
        return False, 0, f"Timed out after {NAV_TIMEOUT_SECONDS}s"
    except Exception as e:
        return False, 0, str(e)


def main():
    from playwright.sync_api import sync_playwright

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"Streamlit App Pinger  |  {now}")
    print("─" * 55)

    if not APPS:
        print("No apps configured. Add URLs to the APPS list in ping_apps.py.")
        sys.exit(0)

    print(f"Pinging {len(APPS)} app(s)...\n")

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for url in APPS:
            page = browser.new_page()
            try:
                ok, code, msg = ping(page, url)
            finally:
                page.close()
            results.append((url, ok, msg))
            status = "OK  " if ok else "FAIL"
            print(f"  [{status}]  {url}")
            print(f"          {msg}\n")
        browser.close()

    failures = [r for r in results if not r[1]]
    print("─" * 55)
    if failures:
        print(f"  {len(results) - len(failures)}/{len(results)} apps OK")
        print(f"  {len(failures)} failed:")
        for url, _, msg in failures:
            print(f"    • {url}  ({msg})")
        sys.exit(1)
    else:
        print(f"  All {len(results)} apps responded successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
