# Streamlit App Pinger

Keeps your Streamlit Community Cloud apps awake by pinging them every 3 days,
before the 7-day inactivity sleep kicks in.

---

## Quick setup (GitHub Actions — recommended)

GitHub Actions is free and runs in the cloud with no server required.

### Step 1 — Create a GitHub repo

Create a new repo (can be private). Name it anything, e.g. `streamlit-pinger`.

### Step 2 — Add the files

Upload both files to the **root** of the repo:

```
your-repo/
├── ping_apps.py
└── .github/
    └── workflows/
        └── ping.yml
```

> The `.github/workflows/` folder must be at the root. GitHub looks for
> workflow files there automatically.

### Step 3 — Add your app URLs

Open `ping_apps.py` and fill in the `APPS` list:

```python
APPS = [
    "https://my-redistribution-app.streamlit.app",
    "https://my-deficit-calculator.streamlit.app",
    "https://my-other-app.streamlit.app",
]
```

Commit and push. That's it.

### Step 4 — Verify it's working

Go to your repo → **Actions** tab. You should see the "Ping Streamlit Apps"
workflow. Click **Run workflow** to trigger it manually and confirm everything
works before waiting 3 days for the first scheduled run.

A green checkmark means all apps responded. A red X means at least one failed
— click into the run to see which one and why.

---

## Changing the schedule

The default is every 3 days at 10:00 AM UTC. To change it, edit the `cron`
line in `ping.yml`:

```yaml
- cron: '0 10 */3 * *'   # every 3 days at 10:00 UTC
- cron: '0 10 */2 * *'   # every 2 days
- cron: '0 10 * * 1'     # every Monday
```

Use [crontab.guru](https://crontab.guru) to generate the right expression.

---

## Alternative: cron-job.org (no GitHub needed)

If you don't want to use GitHub, [cron-job.org](https://cron-job.org) is a
free web service that does the same thing with no code at all:

1. Sign up at cron-job.org (free)
2. Click **Create cronjob**
3. Paste your app URL in the URL field
4. Set schedule to every 3 days
5. Repeat for each app

---

## How it works

Streamlit Community Cloud sleeps an app after approximately 7 days with no
traffic. This script sends a plain HTTP GET request to each URL every 3 days.
That request registers as traffic and resets the inactivity timer, so the app
is always awake when someone needs it.

Any HTTP response under 500 (including the sleep page itself returning 200)
counts as a successful ping.
