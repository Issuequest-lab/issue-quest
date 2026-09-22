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


## Newspaper comparison (v4.2)

Open `newspapers.html`. Japanese headlines are primary; originals are collapsed and source links secondary. Select two or three articles to compare. Paper and Web records never substitute for each other. The initial sources are Asahi and Mainichi paper lists, the Guardian paper list, Mainichi Web and Guardian UK Web. These are selected from official listings, not a claim to cover every newspaper. Top placement is not inferred: current records explicitly say paper-listed / web-featured. Local print editions remain unverified except where explicitly supplied by the source.

`newspapers.yml` runs at 08:23 and 17:23 JST, subject to GitHub schedule delays. It shares the existing updater concurrency group to avoid concurrent git writes. Snapshots append to `newspapers/YYYY-MM/YYYY-MM-DD.json`, with an index for month/day selection. Month rollover needs no manual folder creation. Records preserve fetch time separately from print date. A failed source is recorded as unavailable; earlier snapshots remain accessible. Guardian Sunday can retain Saturday's issue, displayed with its true date. Data is read from raw main because bot commits do not rebuild Pages.

Translations use MyMemory's public GET API, cache exact original headlines and show translation failures explicitly. No article bodies or paper images are copied. This is headline comparison, not a factual summary or automatically scored news quiz. Web article publication dates are not inferred from URL strings.

Run `python -m pip install beautifulsoup4==4.14.3`, `python test_newspapers.py`, then `python update_newspapers.py`. Scheduled workflows can be disabled by GitHub after repository inactivity; check Actions when the visible fetch date is old.
