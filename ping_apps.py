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
This script sends an HTTP GET to each URL every 3 days, resetting that
timer so the app is always awake when someone needs it.
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

TIMEOUT_SECONDS = 30

# ── Ping logic ────────────────────────────────────────────────────────────────

def ping(url: str) -> tuple[bool, int, str]:
    """GET the URL and return (success, status_code, message)."""
    try:
        r = requests.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=True)
        # Any 2xx or 3xx is a success — the app responded.
        # The Streamlit sleep page itself returns 200, which still counts as
        # traffic and resets the inactivity timer on Streamlit's side.
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
