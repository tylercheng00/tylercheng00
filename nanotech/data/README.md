# Biotech news feed

`biotech-news.json` powers the **新聞** section on `insights.html`.

## How the 6-hour refresh works

1. **GitHub Actions** workflow [`.github/workflows/nanotech-biotech-news.yml`](../../.github/workflows/nanotech-biotech-news.yml) runs on a cron schedule: `0 */6 * * *` (00:00 / 06:00 / 12:00 / 18:00 UTC), plus `workflow_dispatch` and when the fetcher script changes.
2. The job runs [`../scripts/fetch_biotech_news.py`](../scripts/fetch_biotech_news.py) (Python stdlib only) which pulls:
   - FDA press releases RSS
   - Nature Biotechnology RSS (+ subject feed)
   - ScienceDaily biotechnology RSS
   - PubMed E-utilities (AI × nanomedicine / LNP / drug delivery)
3. Ranked, deduped items are written to `biotech-news.json` and committed if changed.
4. **insights.html** loads the local JSON and also compares against the GitHub `raw` URL for `main`, so the Cursor-hosted app can show fresher news without an immediate republish. Results are cached in `localStorage`.

## Manual refresh

```bash
python3 nanotech/scripts/fetch_biotech_news.py
```

## Notes

- Items are **third-party**; never treated as Nanotech-owned papers.
- Auto-fetched titles/summaries are in the **source language (English)**; the UI shows a language note.
- Cursor app hosting does not run this cron itself — Actions updates the repo; the page client reads the latest committed feed from GitHub when available.
