import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from logger import get_logger

log = get_logger(__name__)



def _load_existing_ids(output_path: str) -> set[str]:
    if not os.path.exists(output_path):
        return set()
    existing = set()
    try:
        ext = os.path.splitext(output_path)[1].lower()
        if ext == ".ndjson":
            with open(output_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        obj = json.loads(line)
                        if obj.get("tender_id"):
                            existing.add(obj["tender_id"])
        else:
            with open(output_path, "r", encoding="utf-8") as f:
                records = json.load(f)
            existing = {r["tender_id"] for r in records if r.get("tender_id")}
        log.info("Loaded %d existing tender_ids from %s (incremental dedup)", len(existing), output_path)
    except Exception as exc:
        log.warning("Could not read existing output file %s: %s", output_path, exc)
    return existing


def deduplicate(records: list[dict]) -> tuple[list[dict], int]:
    
    seen   = set()
    unique = []
    dupes  = 0
    for r in records:
        tid = r.get("tender_id", "")
        if tid and tid in seen:
            dupes += 1
        else:
            seen.add(tid)
            unique.append(r)
    if dupes:
        log.info("Deduplicated %d duplicate tender_ids within this run", dupes)
    return unique, dupes


def save_records(
    records: list[dict],
    output_path: str,
    dry_run: bool = False,
) -> tuple[int, int]:
    
    records, within_dupes = deduplicate(records)

    existing_ids  = _load_existing_ids(output_path)
    new_records   = [r for r in records if r.get("tender_id") not in existing_ids]
    cross_dupes   = len(records) - len(new_records)

    total_deduped = within_dupes + cross_dupes
    if cross_dupes:
        log.info("%d records already in output file — skipping (incremental)", cross_dupes)

    if dry_run:
        log.info("[dry-run] Would save %d records to %s", len(new_records), output_path)
        return len(new_records), total_deduped

    if not new_records:
        log.info("No new records to save.")
        return 0, total_deduped

    ext = os.path.splitext(output_path)[1].lower()

    if ext == ".ndjson":
        with open(output_path, "a", encoding="utf-8") as f:
            for r in new_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    else:
        all_records = list({r["tender_id"]: r for r in (
            _read_json(output_path) + new_records
        )}.values())
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_records, f, ensure_ascii=False, indent=2)

    log.info("Saved %d new records → %s", len(new_records), output_path)
    return len(new_records), total_deduped


def _read_json(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []



_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS runs_metadata (
    run_id              TEXT PRIMARY KEY,
    start_time          TEXT NOT NULL,
    end_time            TEXT,
    duration_seconds    REAL,
    scraper_version     TEXT,
    config              TEXT,          -- JSON blob of config dict
    tender_types_processed TEXT,       -- JSON list
    pages_visited       INTEGER,
    tenders_parsed      INTEGER,
    tenders_saved       INTEGER,
    failures            INTEGER,
    deduped_count       INTEGER,
    error_summary       TEXT           -- JSON list of error messages
);
"""


def _get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


def start_run_metadata(
    db_path: str,
    run_id: str,
    config: dict,
    dry_run: bool = False,
) -> None:
    if dry_run:
        return
    try:
        conn = _get_conn(db_path)
        conn.execute(
            """INSERT OR REPLACE INTO runs_metadata
               (run_id, start_time, scraper_version, config)
               VALUES (?, ?, ?, ?)""",
            (
                run_id,
                datetime.now(timezone.utc).isoformat(),
                "1.0.0",
                json.dumps(config),
            ),
        )
        conn.commit()
        conn.close()
        log.debug("Run metadata row inserted for run_id=%s", run_id)
    except Exception as exc:
        log.warning("Could not write start metadata: %s", exc)


def finish_run_metadata(
    db_path: str,
    run_id: str,
    start_time: datetime,
    pages_visited: int,
    tenders_parsed: int,
    tenders_saved: int,
    failures: int,
    deduped_count: int,
    error_summary: list[str],
    tender_types: list[str],
    dry_run: bool = False,
) -> None:
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    log.info(
        "Run complete | pages=%d parsed=%d saved=%d deduped=%d failures=%d duration=%.1fs",
        pages_visited, tenders_parsed, tenders_saved, deduped_count, failures, duration,
    )

    if dry_run:
        log.info("[dry-run] Metadata would be: %s", json.dumps({
            "pages_visited": pages_visited,
            "tenders_parsed": tenders_parsed,
            "tenders_saved": tenders_saved,
            "failures": failures,
            "deduped_count": deduped_count,
            "duration_seconds": round(duration, 2),
        }, indent=2))
        return

    try:
        conn = _get_conn(db_path)
        conn.execute(
            """UPDATE runs_metadata SET
               end_time=?, duration_seconds=?, tender_types_processed=?,
               pages_visited=?, tenders_parsed=?, tenders_saved=?,
               failures=?, deduped_count=?, error_summary=?
               WHERE run_id=?""",
            (
                end_time.isoformat(),
                round(duration, 2),
                json.dumps(tender_types),
                pages_visited,
                tenders_parsed,
                tenders_saved,
                failures,
                deduped_count,
                json.dumps(error_summary),
                run_id,
            ),
        )
        conn.commit()
        conn.close()
        log.info("Run metadata finalised in %s", db_path)
    except Exception as exc:
        log.error("Could not finalise run metadata: %s", exc)
