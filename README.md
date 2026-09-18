# ISSUE QUEST

Play: https://issuequest-lab.github.io/issue-quest/

## Daily issues

Google Trends Japan RSS supplies up to 12 topic names. The app builds practice
questions with explicit fictional situations, goals, conditions and individual
answer explanations. These situations do not claim to explain actual news or why
a search trended. No news knowledge or paid AI API is required.

`.github/workflows/daily-issues.yml` fetches data at 03:17 and 05:47 JST daily
(the second run is a recovery opportunity). GitHub may delay scheduled jobs.
Manual recovery: Actions → Update daily issues → Run workflow.

The app reads the JSON directly from this repository's raw main branch, with a
same-origin fallback and local last-success cache. This is intentional: commits
made by GITHUB_TOKEN do not trigger branch-based GitHub Pages builds. No Pages
rebuild is required for daily topic updates. Code changes still use normal Pages
publishing. Fetch failures preserve previous data; the app displays its real date
and a stale notice. Scheduled workflows in inactive public repositories may be
disabled by GitHub; check Actions and re-enable when needed.

Run locally:

```sh
python3 scripts/test_daily.py
python3 scripts/update_daily.py
python3 -m http.server 8765
```

## 2026-09-18 repair

- Added the previously missing daily data and scheduled updater.
- Replaced context-free questions with five self-contained practice situations.
- Added individual reasons for every answer and a stale-data notice.
- Refreshes topics on return to the tab after a Japanese date change; active
  sessions retain their questions until completion.
