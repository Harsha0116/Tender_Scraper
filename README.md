# nprocure Tender Scraper — POC

A production-minded scraper for [tender.nprocure.com](https://tender.nprocure.com)
that extracts live tender listings, cleans and normalises the data, and stores
run-level metadata for observability and debugging.

---

## Project Structure

```
tender_scraper/
├── scrape.py           ← CLI entrypoint — orchestrates all stages
├── config.py           ← CLI args + environment variable parsing
├── logger.py           ← Structured logging (run_id on every line)
├── fetcher.py          ← HTTP session, AES-CBC encryption, pagination, retries
├── parser.py           ← HTML field extraction (raw, no cleaning)
├── cleaner.py          ← Normalisation: dates, types, whitespace, dedup
├── persistence.py      ← JSON/NDJSON output + SQLite run metadata
├── requirements.txt    ← Python dependencies
├── sample-output.json  ← Cleaned sample records
├── README.md           ← This file
├── schema.md           ← Data model + metadata key explanations
├── architecture.md     ← Approach justification + encryption breakdown
└── dev_prompts/
    └── notes.md        ← LLM usage log during development
```

---

## Installation

```bash
pip install pycryptodome requests beautifulsoup4
```

---

## Usage

### Demo run — 50 tenders
```bash
python scrape.py --limit 50 --output sample-output.json
```

### Full scrape — all ~3800 tenders
```bash
python scrape.py --output tenders.json
```

### NDJSON output
```bash
python scrape.py --output tenders.ndjson
```

### Dry run — validate connectivity, write nothing
```bash
python scrape.py --limit 20 --dry-run
```

### Custom rate limit and retries
```bash
python scrape.py --limit 200 --rate-limit 2.0 --retries 5 --output tenders.json
```

---

## CLI Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--limit N` | all | Stop after N tenders. Use for demo runs. |
| `--rate-limit SECS` | 1.5 | Minimum seconds between HTTP requests. |
| `--concurrency N` | 1 | Concurrent fetch workers. |
| `--retries N` | 3 | Max retry attempts per failed request. |
| `--timeout SECS` | 60 | Per-request timeout in seconds. |
| `--output PATH` | sample-output.json | Output file (.json or .ndjson). |
| `--metadata-db PATH` | runs_metadata.db | SQLite file for run metadata. |
| `--user-agent UA` | Chrome UA | User-Agent header string. |
| `--page-size N` | 50 | Records per API call (max 100). |
| `--dry-run` | False | Parse but write nothing to disk. |
| `--version` | — | Show version and exit. |

---

## Environment Variables

All CLI flags can also be set via environment variables:

| Variable | Flag | Default |
|----------|------|---------|
| `RATE_LIMIT` | `--rate-limit` | `1.5` |
| `CONCURRENCY` | `--concurrency` | `1` |
| `TIMEOUT_SECONDS` | `--timeout` | `60` |
| `RETRIES` | `--retries` | `3` |
| `OUTPUT_PATH` | `--output` | `sample-output.json` |
| `METADATA_DB` | `--metadata-db` | `runs_metadata.db` |
| `USER_AGENT` | `--user-agent` | Chrome UA string |

CLI flags take precedence over environment variables.

---

## Output

### Tender records (`sample-output.json`)
A JSON array of cleaned, normalised tender records. Re-running with the same
output file is **safe and idempotent** — existing `tender_id` values are
detected and skipped (incremental mode).

### Run metadata (`runs_metadata.db`)
SQLite database with one row per scraper run. Inspect with:

```bash
sqlite3 runs_metadata.db \
  "SELECT run_id, start_time, tenders_saved, failures, duration_seconds FROM runs_metadata;"
```
---

## Running Tests

The test suite validates all four stages of the pipeline — encryption, 
parsing, cleaning, and persistence — without making any real network calls.

### Install test dependencies
```bash
pip install pytest pycryptodome requests beautifulsoup4 cryptography
```

### Run all tests
```bash
cd tender_scraper
pytest
```

---

## Technical Notes

- **SSL**: Certificate validation is disabled — nprocure uses a private NIC India CA
  not in public CA bundles. The connection is still TLS-encrypted.
- **Encryption**: All API request payloads are AES-128-CBC encrypted with
  PBKDF2-SHA1 key derivation. Parameters were reverse-engineered from the
  site's `AesUtil.js`. See `architecture.md` for the full breakdown.
- **No LLM at runtime**: The scraper is fully self-contained with no external
  API or LLM calls.
