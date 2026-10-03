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
This script sends an HTTP GET to each URL every 3 days. If the app is
awake, that's all it takes. If the app is sleeping (Streamlit returns a
"gone to sleep" page), a headless Chromium browser is launched to click
the wake-up button and wait for the app to fully load — exactly as a
real user would.
"""

import sys
import requests
from datetime import datetime, timezone

# ── Add your app URLs here ────────────────────────────────────────────────────

APPS = [
    # "https://your-first-app.streamlit.app",
    # "https://your-second-app.streamlit.app",
    # "https://your-third-app.streamlit.app",
]

# ── Settings ──────────────────────────────────────────────────────────────────

TIMEOUT_SECONDS = 30       # HTTP GET timeout
WAKE_TIMEOUT_SECONDS = 120  # How long to wait for a sleeping app to wake up

# ── Wake-up logic (headless browser) ──────────────────────────────────────────

def wake_up_sleeping_app(url: str, wake_timeout: int = WAKE_TIMEOUT_SECONDS) -> tuple[bool, str]:
    """
    Launch a headless Chromium browser to wake a sleeping Streamlit app.

    Streamlit's sleep page returns HTTP 200 but is a static HTML page with a
    "Yes, get this app back up!" button. A plain HTTP GET never executes that
    button, so the app stays sleeping. This function does what a real browser
    would: click the button and wait for the live app to appear.

    Returns (success, message).
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)

            # Click the wake-up button ("Yes, get this app back up!")
            try:
                page.locator("button:has-text('Yes')").first.click(timeout=5_000)
            except PlaywrightTimeoutError:
                pass  # No button found — some versions auto-wake on navigation

            # Wait until Streamlit's root element appears (live app is running)
            try:
                page.wait_for_selector(
                    "[data-testid='stApp']",
                    timeout=wake_timeout * 1_000,
                )
                return True, "Woken up successfully"
            except PlaywrightTimeoutError:
                # Fallback: accept it if the sleep text has at least disappeared
                if "gone to sleep" not in page.content().lower():
                    return True, "Woken up (app responded)"
                return False, f"App did not wake within {wake_timeout}s"

        except PlaywrightTimeoutError:
            return False, "Timed out navigating to the app"
        except Exception as e:
            return False, f"Browser error — {e}"
        finally:
            browser.close()

# ── Ping logic ────────────────────────────────────────────────────────────────

def ping(url: str) -> tuple[bool, int, str]:
    """GET the URL. If the app is sleeping, wake it with a headless browser."""
    try:
        r = requests.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=True)

        # Detect Streamlit's sleep page — it returns 200 but is not the live app
        if r.status_code == 200 and "gone to sleep" in r.text.lower():
            print(f"          App is sleeping — launching browser to wake it up...")
            ok, msg = wake_up_sleeping_app(url)
            return ok, r.status_code, msg

        ok = r.status_code < 500
        return ok, r.status_code, f"HTTP {r.status_code}"
    except requests.exceptions.Timeout:
        return False, 0, f"Timed out after {TIMEOUT_SECONDS}s"
    except requests.exceptions.ConnectionError as e:
        return False, 0, f"Connection error — {e}"
    except Exception as e:
        return False, 0, str(e)


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"Streamlit App Pinger  |  {now}")
    print("─" * 55)

    if not APPS:
        print("No apps configured. Add URLs to the APPS list in ping_apps.py.")
        sys.exit(0)

    print(f"Pinging {len(APPS)} app(s)...\n")

    results = []
    for url in APPS:
        ok, code, msg = ping(url)
        results.append((url, ok, msg))
        status = "OK  " if ok else "FAIL"
        print(f"  [{status}]  {url}")
        print(f"          {msg}\n")

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
