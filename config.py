import argparse
import os
import uuid


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="scrape.py",
        description="nprocure.com Tender Scraper — POC",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N tenders (omit for all). Useful for demo runs.",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=float(os.environ.get("RATE_LIMIT", "1.5")),
        metavar="SECONDS",
        help="Minimum seconds between HTTP requests.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.environ.get("CONCURRENCY", "1")),
        metavar="N",
        help="Number of concurrent fetch workers (keep ≤2 for polite scraping).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=int(os.environ.get("RETRIES", "3")),
        metavar="N",
        help="Max retry attempts per failed request.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("TIMEOUT_SECONDS", "60")),
        metavar="SECONDS",
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--output",
        default=os.environ.get("OUTPUT_PATH", "sample-output.json"),
        metavar="PATH",
        help="Output file path (.json = pretty array, .ndjson = one record per line).",
    )
    parser.add_argument(
        "--metadata-db",
        default=os.environ.get("METADATA_DB", "runs_metadata.db"),
        metavar="PATH",
        help="SQLite DB file to store run-level metadata.",
    )
    parser.add_argument(
        "--user-agent",
        default=os.environ.get(
            "USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36",
        ),
        metavar="UA",
        help="User-Agent header sent with every request.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=50,
        metavar="N",
        help="Records to request per API call (max 100).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Fetch and parse but do NOT write output or metadata. "
             "Useful for validating connectivity.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="nprocure-scraper 1.0.0",
    )

    return parser.parse_args()


def build_config(args: argparse.Namespace) -> dict:
    """
    Merge parsed CLI args into a single config dict that gets logged
    and stored verbatim in run metadata.
    """
    return {
        "limit":        args.limit,
        "rate_limit":   args.rate_limit,
        "concurrency":  args.concurrency,
        "retries":      args.retries,
        "timeout":      args.timeout,
        "output":       args.output,
        "metadata_db":  args.metadata_db,
        "user_agent":   args.user_agent,
        "page_size":    args.page_size,
        "dry_run":      args.dry_run,
    }
