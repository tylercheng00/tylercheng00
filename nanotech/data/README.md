# Biotech news feed

`biotech-news.json` powers the **新聞** section on `insights.html`.
`biotech-notes.json` powers the **評論** section: five notes per Hong Kong date.

## How the 6-hour refresh works

1. **GitHub Actions** workflow [`.github/workflows/nanotech-biotech-news.yml`](../../.github/workflows/nanotech-biotech-news.yml) runs on a cron schedule: `0 */6 * * *` (00:00 / 06:00 / 12:00 / 18:00 UTC), plus `workflow_dispatch` and when the fetcher script changes.
2. The job runs [`../scripts/fetch_biotech_news.py`](../scripts/fetch_biotech_news.py) (Python stdlib only) which pulls:
   - FDA press and biologics RSS
   - Nature Biotechnology RSS (+ subject feed)
   - Fierce Biotech, BioPharma Dive, STAT
   - ScienceDaily biotechnology RSS
   - PubMed E-utilities (AI × nanomedicine / LNP / drug delivery)
3. Items older than about 12 days are dropped. The rest are written to `biotech-news.json`.
4. [`../scripts/write_daily_notes.py`](../scripts/write_daily_notes.py) writes five notes for the Hong Kong date into `biotech-notes.json`. A date with a hand-checked desk set is kept as written. Other days are drafted from that day's wires and do not invent trial numbers. A second cron at 16:30 UTC (00:30 Hong Kong) starts the new day.
5. **insights.html** loads the local JSON and also compares GitHub `raw` and jsDelivr, picking the copy with more recent items. The page prefers that over a newer timestamp full of old wires. Results are cached in `localStorage`.

## Manual refresh

```bash
python3 nanotech/scripts/fetch_biotech_news.py
```

## Notes

- Items are **third-party**; never treated as Nanotech-owned papers.
- Auto-fetched titles/summaries are in the **source language (English)**; the UI shows a language note.
- Cursor app hosting does not run this cron itself — Actions updates the repo; the page client reads the latest committed feed from GitHub when available.
