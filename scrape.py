"""
scrape.py
---------
CLI entrypoint. Orchestrates the four stages:
  fetch -> parse -> clean -> persist

Usage:
    python scrape.py --help
    python scrape.py --limit 50 --dry-run
    python scrape.py --limit 200 --rate-limit 1.0 --output tenders.ndjson
    python scrape.py --output sample-output.json
"""

import sys
import uuid
from collections import Counter
from datetime import datetime, timezone

# Bootstrap logger before importing anything else
import logger as _logger_mod

RUN_ID = str(uuid.uuid4())[:8]
_logger_mod.setup_logger(RUN_ID)
log = _logger_mod.get_logger("scrape")

from config import parse_args, build_config
from fetcher import make_session, iter_raw_pages
from parser import parse_page
from cleaner import clean_records
from persistence import (
    save_records,
    start_run_metadata,
    finish_run_metadata,
)

SCRAPER_VERSION = "1.0.0"


def main() -> int:
    args   = parse_args()
    config = build_config(args)

    log.info("=" * 60)
    log.info("nprocure.com Tender Scraper  v%s", SCRAPER_VERSION)
    log.info("run_id=%s  dry_run=%s  limit=%s", RUN_ID, config["dry_run"], config["limit"])
    log.info("rate_limit=%.1fs  retries=%d  timeout=%ds",
             config["rate_limit"], config["retries"], config["timeout"])
    log.info("output=%s  metadata_db=%s", config["output"], config["metadata_db"])
    log.info("=" * 60)

    start_time = datetime.now(timezone.utc)
    start_run_metadata(config["metadata_db"], RUN_ID, config, config["dry_run"])

    all_clean      = []
    pages_visited  = 0
    tenders_parsed = 0
    failures       = 0
    error_summary  = []
    type_counter   = Counter()

    session = make_session(config["user_agent"], config["timeout"])

    try:
        for raw_items, total in iter_raw_pages(session, config):
            pages_visited += 1

            try:
                parsed = parse_page(raw_items)
            except Exception as exc:
                log.error("Parse error on page %d: %s", pages_visited, exc)
                failures += 1
                error_summary.append(f"page {pages_visited}: parse error -- {exc}")
                continue

            tenders_parsed += len(parsed)
            cleaned, skipped = clean_records(parsed)

            if skipped:
                log.debug("Skipped %d records on page %d", skipped, pages_visited)

            for r in cleaned:
                type_counter[r["tender_type"]] += 1

            all_clean.extend(cleaned)

            log.info(
                "Page %d: %d raw -> %d parsed -> %d cleaned",
                pages_visited, len(raw_items), len(parsed), len(cleaned),
            )

    except KeyboardInterrupt:
        log.warning("Interrupted -- saving what we have...")
    except Exception as exc:
        log.error("Fatal fetch error: %s", exc)
        failures += 1
        error_summary.append(f"fatal: {exc}")

    saved   = 0
    deduped = 0

    if config["dry_run"]:
        log.info("[dry-run] Would write %d records. Nothing saved.", len(all_clean))
        saved = len(all_clean)
    else:
        try:
            saved, deduped = save_records(all_clean, config["output"])
        except Exception as exc:
            log.error("Failed to save records: %s", exc)
            failures += 1
            error_summary.append(f"save: {exc}")

    finish_run_metadata(
        db_path        = config["metadata_db"],
        run_id         = RUN_ID,
        start_time     = start_time,
        pages_visited  = pages_visited,
        tenders_parsed = tenders_parsed,
        tenders_saved  = saved,
        failures       = failures,
        deduped_count  = deduped,
        error_summary  = error_summary,
        tender_types   = list(type_counter.keys()),
        dry_run        = config["dry_run"],
    )

    log.info("Tender type breakdown: %s", dict(type_counter))
    log.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
