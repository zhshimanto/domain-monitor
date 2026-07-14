# Domain Status Board

A small self-updating dashboard that checks a list of domains, follows their
redirects, and shows the live status on a web page. A bot runs on a schedule
(via GitHub Actions), so you don't have to trigger checks manually.

## How it works

```
domains.json              ← you edit this: your brands + domains
      │
      ▼
scripts/check_status.py   ← the "bot" — requests each domain, follows redirects
      │
      ▼
data/status.json           ← generated results (status code, final URL, timing)
      │
      ▼
index.html                 ← the page — fetches data/status.json and renders a table
```

A GitHub Actions workflow (`.github/workflows/check-domains.yml`) runs the bot
twice a day, commits the updated `data/status.json`, and publishes the whole
repo via GitHub Pages so the page always reflects the latest check.

## 1. Add your real domains

Edit `domains.json`:

```json
{
  "brands": [
    {
      "name": "Brand1",
      "domains": ["abc.com", "abc1.com", "abc3.com"],
      "final": "abc4.com"
    },
    {
      "name": "Brand2",
      "domains": ["zak1.com", "zak2.com", "zak3.com"],
      "final": "zak4.com"
    }
  ]
}
```

- `domains`: every domain you want checked for this brand (the redirecting ones).
- `final`: the domain they're supposed to end up on. It's checked too and
  gets a **FINAL** badge on the page. It doesn't need to be repeated inside
  `domains`.
- Add as many brands/domains as you like — the page and bot both just loop
  over whatever is in this file.

## 2. Push to GitHub

```bash
cd domain-monitor
git init
git add .
git commit -m "Initial domain status board"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

## 3. Turn on GitHub Pages

In your repo: **Settings → Pages → Source → GitHub Actions**.

That's it — the workflow that ships in this repo handles the build and
deploy step itself (via `actions/deploy-pages`).

## 4. Let the bot run

- It's already scheduled for **03:00 and 15:00 UTC daily** — edit the `cron`
  line in `.github/workflows/check-domains.yml` to change the times
  (cron is in UTC).
- To run it immediately instead of waiting: go to your repo's **Actions**
  tab → **Check domain redirects** → **Run workflow**.
- Every run overwrites `data/status.json` and commits it with the message
  `Update domain status [skip ci]`, then redeploys the page.

Your page will be live at:
`https://<your-username>.github.io/<your-repo>/`

## Running the bot locally (optional)

```bash
pip install -r requirements.txt
python scripts/check_status.py
```

This regenerates `data/status.json`. Open `index.html` directly in a browser
to check the page (or run a tiny local server, since some browsers block
`fetch()` on local files):

```bash
python -m http.server 8000
# then visit http://localhost:8000
```

## What the page shows, per domain

| Column | Meaning |
|---|---|
| Domain | the domain checked, tagged `FINAL` if it's the intended destination |
| Signal | a quick visual for response time (4 bars = fast, 1 bar = slow) |
| Status | the HTTP status code, or `ERROR` if unreachable |
| Redirect chain | every hop it went through, ending at the final URL |
| Response | response time in ms |

The summary pills at the top count: domains resolving straight to 200 (ok),
domains actively redirecting (as expected), domains worth a second look
(warn — e.g. a "final" domain that's redirecting further, or a non-final
domain returning 200 instead of redirecting), and domains that are down.

## Alternative: hosting on Bluehost instead

This repo is built around GitHub Actions doing the scheduling, since shared
hosting (Bluehost) doesn't reliably support cron-triggered Python jobs. If
you'd rather keep everything on Bluehost:

- You can still use GitHub Actions purely as the **scheduler/checker**, and
  add a step to `check-domains.yml` that uploads `data/status.json` and
  `index.html` to Bluehost over FTP/SFTP (e.g. using the
  `SamKirkland/FTP-Deploy-Action` action) instead of deploying to GitHub Pages.
- Or, if your Bluehost plan supports Python + cron via cPanel, you can skip
  GitHub Actions entirely: upload this whole folder, set up a cron job to run
  `python3 scripts/check_status.py` once or twice daily, and just open
  `index.html` on your domain — no code changes needed either way.

Let me know which route you'd like and I can wire up the FTP deploy step or
the cPanel cron instructions specifically.
