# Schema Documentation

## 1. Tenders — `sample-output.json` (JSON array / NDJSON)

Each record represents one tender listing.

| Field              | Type           | Example                          | Reason / Notes |
|--------------------|----------------|----------------------------------|----------------|
| `tender_id`        | string (PK)    | `"280322"`                       | Unique numeric ID assigned by the portal. Used as deduplication key across runs. |
| `tender_type`      | enum string    | `"Works"`                        | Classified as Goods / Works / Services via keyword scan of description. Enables type-level filtering and analytics. |
| `title`            | string         | `"76-2025/2026"`                 | IFB / Tender Notice Number from the portal. Preserved as-is because it carries official reference meaning. |
| `organisation`     | string         | `"R&B Division, Mahisagar"`      | Cleaned from the raw department field (prefix code stripped). Normalised for grouping/filtering by issuing body. |
| `publish_date`     | string\|null   | `null`                           | Not exposed by this endpoint; kept null to signal absence rather than omit the field entirely. |
| `closing_date`     | string\|null   | `"2026-03-17"`                   | Normalised to ISO 8601 (YYYY-MM-DD). Raw portal format is DD-MM-YYYY HH:MM:SS. |
| `description`      | string         | `"CONST. OF ANGANWADI..."`       | name_of_work with whitespace collapsed and boilerplate openers stripped. |
| `source_url`       | string         | `"https://tender.nprocure.com/view-nit-home?tenderid=280322"` | Direct link to tender detail page. Enables downstream enrichment without re-scraping the list. |
| `estimated_value`  | float\|null    | `1003246.62`                     | Cast to float for numeric comparisons. Null if zero or missing (portal shows 0.00 for undisclosed values). |
| `attachments`      | integer        | `10`                             | Count of documents attached to the tender. Useful signal for tender completeness. |
| `corrigendum`      | string         | `""`                             | Amendment notice if present; empty string otherwise. |
| `raw_html_snippet` | string         | `"<html><body>..."`              | First 500 chars of raw HTML cell. Retained for debugging parser regressions without re-fetching. |

### Deduplication Strategy

- **Within-run**: `tender_id` uniqueness enforced before writing. If the API returns the same tender on multiple pages, the first occurrence is kept.
- **Cross-run (incremental)**: On each run, existing `tender_id` values are loaded from the output file. New records with matching IDs are skipped. This makes repeated runs safe and additive.

---

## 2. Run Metadata — `runs_metadata.db` (SQLite table `runs_metadata`)

One row is inserted per scraper invocation. Partial runs (interrupted) still
record what was completed.

| Column                   | Type    | Why it matters |
|--------------------------|---------|----------------|
| `run_id`                 | TEXT PK | 8-char UUID prefix. Stamped on every log line — ties logs to the metadata row for debugging. |
| `start_time`             | TEXT    | ISO 8601 UTC. Determines the time window of data freshness. |
| `end_time`               | TEXT    | ISO 8601 UTC. Null if run was killed mid-way — detects crashes. |
| `duration_seconds`       | REAL    | Time between start and end. Tracks performance regression over time. |
| `scraper_version`        | TEXT    | Semver string. Correlates data shape changes with code releases. |
| `config`                 | TEXT    | JSON blob of all CLI/env config used. Reproducibility — re-run with same args. |
| `tender_types_processed` | TEXT    | JSON list e.g. `["Works","Goods","Services"]`. Confirms type classifier fired for all categories. |
| `pages_visited`          | INTEGER | Number of paginated API calls made. Helps estimate expected vs actual coverage. |
| `tenders_parsed`         | INTEGER | Raw HTML records that were successfully parsed (before cleaning). |
| `tenders_saved`          | INTEGER | Records written to output after dedup and cleaning. |
| `failures`               | INTEGER | Count of pages or records that raised exceptions. Non-zero means incomplete data. |
| `deduped_count`          | INTEGER | Records dropped by deduplication. Useful for detecting portal-side data issues. |
| `error_summary`          | TEXT    | JSON list of error messages. First place to look when `failures > 0`. |

### Why SQLite for metadata?

- Zero infrastructure — no server needed for a POC.
- `sqlite3` ships with Python — no install step.
- Simple to query with the sqlite3 CLI or any SQL tool.
- Easy to migrate to Postgres/MySQL by swapping the connection in `persistence.py`.
