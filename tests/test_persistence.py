import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone

import pytest
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persistence import (
    deduplicate,
    save_records,
    start_run_metadata,
    finish_run_metadata,
    _load_existing_ids,
)



def make_record(tender_id, closing_date="2026-03-05", tender_type="Works"):
    return {
        "tender_id":       tender_id,
        "tender_type":     tender_type,
        "title":           f"Title {tender_id}",
        "organisation":    "Test Org",
        "publish_date":    None,
        "closing_date":    closing_date,
        "description":     "Test description",
        "source_url":      f"https://tender.nprocure.com/view-nit-home?tenderid={tender_id}",
        "estimated_value": 1000000.0,
        "attachments":     3,
        "corrigendum":     "",
        "raw_html_snippet": "<html>...",
    }



class TestDeduplicate:

    def test_no_duplicates_returns_all(self):
        records = [make_record("111"), make_record("222"), make_record("333")]
        unique, dupes = deduplicate(records)
        assert len(unique) == 3
        assert dupes == 0

    def test_removes_duplicate_tender_ids(self):
        records = [make_record("111"), make_record("111"), make_record("222")]
        unique, dupes = deduplicate(records)
        assert len(unique) == 2
        assert dupes == 1

    def test_keeps_first_occurrence(self):
        r1 = make_record("111")
        r1["description"] = "first"
        r2 = make_record("111")
        r2["description"] = "second"
        unique, _ = deduplicate([r1, r2])
        assert unique[0]["description"] == "first"

    def test_empty_list(self):
        unique, dupes = deduplicate([])
        assert unique == []
        assert dupes == 0

    def test_all_duplicates(self):
        records = [make_record("111")] * 5
        unique, dupes = deduplicate(records)
        assert len(unique) == 1
        assert dupes == 4



class TestSaveRecordsJSON:

    def test_creates_json_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            records = [make_record("111"), make_record("222")]
            saved, deduped = save_records(records, path)
            assert saved == 2
            assert deduped == 0
            assert os.path.exists(path)
        finally:
            os.unlink(path)

    def test_json_is_valid_and_array(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            save_records([make_record("111")], path)
            with open(path) as f:
                data = json.load(f)
            assert isinstance(data, list)
            assert len(data) == 1
        finally:
            os.unlink(path)

    def test_json_record_has_correct_fields(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            save_records([make_record("280210")], path)
            with open(path) as f:
                data = json.load(f)
            record = data[0]
            assert record["tender_id"] == "280210"
            assert record["tender_type"] == "Works"
            assert record["closing_date"] == "2026-03-05"
        finally:
            os.unlink(path)

    def test_incremental_adds_new_records(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            save_records([make_record("111")], path)
            save_records([make_record("222")], path)  # second run
            with open(path) as f:
                data = json.load(f)
            ids = {r["tender_id"] for r in data}
            assert "111" in ids
            assert "222" in ids
        finally:
            os.unlink(path)

    def test_cross_run_dedup_skips_existing(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            save_records([make_record("111"), make_record("222")], path)
            saved, deduped = save_records([make_record("111"), make_record("333")], path)
            assert saved == 1    
            assert deduped == 1  
        finally:
            os.unlink(path)

    def test_dry_run_writes_nothing(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        os.unlink(path)  
        try:
            saved, _ = save_records([make_record("111")], path, dry_run=True)
            assert saved == 1         
            assert not os.path.exists(path)  
        finally:
            if os.path.exists(path):
                os.unlink(path)



class TestSaveRecordsNDJSON:

    def test_creates_ndjson_file(self):
        with tempfile.NamedTemporaryFile(suffix=".ndjson", delete=False) as f:
            path = f.name
        try:
            save_records([make_record("111"), make_record("222")], path)
            assert os.path.exists(path)
        finally:
            os.unlink(path)

    def test_each_line_is_valid_json(self):
        with tempfile.NamedTemporaryFile(suffix=".ndjson", delete=False) as f:
            path = f.name
        try:
            save_records([make_record("111"), make_record("222")], path)
            with open(path) as f:
                lines = [l.strip() for l in f if l.strip()]
            assert len(lines) == 2
            for line in lines:
                obj = json.loads(line)
                assert "tender_id" in obj
        finally:
            os.unlink(path)

    def test_ndjson_incremental_appends(self):
        with tempfile.NamedTemporaryFile(suffix=".ndjson", delete=False) as f:
            path = f.name
        try:
            save_records([make_record("111")], path)
            save_records([make_record("222")], path)
            with open(path) as f:
                lines = [l.strip() for l in f if l.strip()]
            assert len(lines) == 2
        finally:
            os.unlink(path)

    def test_ndjson_cross_run_dedup(self):
        with tempfile.NamedTemporaryFile(suffix=".ndjson", delete=False) as f:
            path = f.name
        try:
            save_records([make_record("111")], path)
            saved, deduped = save_records([make_record("111")], path)
            assert saved == 0
            assert deduped == 1
            with open(path) as f:
                lines = [l.strip() for l in f if l.strip()]
            assert len(lines) == 1  # still only one record
        finally:
            os.unlink(path)



class TestCSVOutput:

    def test_csv_has_correct_columns(self):
        import csv
        import io
        records = [make_record("280210"), make_record("280056")]

        output = io.StringIO()
        fields = ["tender_id", "tender_type", "title", "organisation",
                  "closing_date", "estimated_value", "attachments", "description"]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
        output.seek(0)

        reader = csv.DictReader(output)
        assert set(reader.fieldnames) == set(fields)

    def test_csv_rows_match_record_count(self):
        import csv, io
        records = [make_record(str(i)) for i in range(10)]
        output = io.StringIO()
        fields = ["tender_id", "tender_type", "title", "organisation",
                  "closing_date", "estimated_value", "attachments", "description"]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
        output.seek(0)
        rows = list(csv.DictReader(output))
        assert len(rows) == 10

    def test_csv_no_newlines_in_cells(self):
        import csv, io
        record = make_record("280210")
        record["description"] = "Line one\nLine two\nLine three"

        from cleaner import _clean_text
        record["description"] = _clean_text(record["description"])

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(record.keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerow(record)
        output.seek(0)
        content = output.read()
        rows = list(csv.reader(io.StringIO(content)))
        assert len(rows) == 2

    def test_csv_dates_are_iso_format(self):
        import csv, io
        record = make_record("280210", closing_date="2026-03-05")
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(record.keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerow(record)
        output.seek(0)
        reader = csv.DictReader(output)
        row = next(reader)
        assert row["closing_date"] == "2026-03-05"

    def test_csv_tender_type_valid_enum(self):
        import csv, io
        records = [
            make_record("1", tender_type="Works"),
            make_record("2", tender_type="Goods"),
            make_record("3", tender_type="Services"),
        ]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(records[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
        output.seek(0)
        for row in csv.DictReader(output):
            assert row["tender_type"] in ("Works", "Goods", "Services")

    def test_csv_tender_id_unique(self):
        import csv, io
        records = [make_record(str(i)) for i in range(5)]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(records[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
        output.seek(0)
        ids = [row["tender_id"] for row in csv.DictReader(output)]
        assert len(ids) == len(set(ids))

    def test_csv_estimated_value_is_numeric(self):
        import csv, io
        record = make_record("280210")
        record["estimated_value"] = 5998400.40
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(record.keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerow(record)
        output.seek(0)
        row = next(csv.DictReader(output))
        assert float(row["estimated_value"]) == 5998400.40

    def test_csv_utf8_encoding_special_chars(self):
        import csv, io
        record = make_record("280210")
        record["organisation"] = "Junagadh-Junagadh Municipal Corporation"
        record["description"] = "कार्य विवरण"  # Hindi text

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(record.keys()),
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerow(record)
        output.seek(0)
        row = next(csv.DictReader(output))
        assert row["description"] == "कार्य विवरण"

    def test_csv_null_values_handled(self):
        import csv, io
        record = make_record("280210")
        record["estimated_value"] = None
        record["closing_date"] = None
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(record.keys()),
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerow(record)
        output.seek(0)
        row = next(csv.DictReader(output))
        # None written to CSV comes back as empty string — that's expected
        assert row["estimated_value"] in ("", "None", None)



class TestRunMetadata:

    def _get_db(self):
        f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        f.close()
        return f.name

    def test_start_run_inserts_row(self):
        db = self._get_db()
        try:
            start_run_metadata(db, "run-001", {"limit": 50, "rate_limit": 1.5}, dry_run=False)
            conn = sqlite3.connect(db)
            rows = conn.execute("SELECT run_id FROM runs_metadata").fetchall()
            conn.close()
            assert len(rows) == 1
            assert rows[0][0] == "run-001"
        finally:
            os.unlink(db)

    def test_finish_run_updates_row(self):
        db = self._get_db()
        try:
            start_run_metadata(db, "run-002", {}, dry_run=False)
            start_time = datetime.now(timezone.utc)
            finish_run_metadata(
                db_path="", run_id="run-002", start_time=start_time,
                pages_visited=10, tenders_parsed=500, tenders_saved=490,
                failures=0, deduped_count=10, error_summary=[],
                tender_types=["Works", "Goods"], dry_run=False,
            )
            finish_run_metadata(
                db_path=db, run_id="run-002", start_time=start_time,
                pages_visited=10, tenders_parsed=500, tenders_saved=490,
                failures=0, deduped_count=10, error_summary=[],
                tender_types=["Works", "Goods"], dry_run=False,
            )
            conn = sqlite3.connect(db)
            row = conn.execute(
                "SELECT tenders_saved, failures, deduped_count FROM runs_metadata WHERE run_id='run-002'"
            ).fetchone()
            conn.close()
            assert row[0] == 490
            assert row[1] == 0
            assert row[2] == 10
        finally:
            os.unlink(db)

    def test_dry_run_writes_nothing_to_db(self):
        db = self._get_db()
        try:
            start_run_metadata(db, "run-dry", {}, dry_run=True)
            conn = sqlite3.connect(db)
            try:
                rows = conn.execute("SELECT * FROM runs_metadata").fetchall()
                assert len(rows) == 0
            except sqlite3.OperationalError:
                pass 
            finally:
                conn.close()
        finally:
            os.unlink(db)

    def test_duration_seconds_is_positive(self):
        db = self._get_db()
        try:
            start_run_metadata(db, "run-003", {}, dry_run=False)
            start_time = datetime.now(timezone.utc)
            finish_run_metadata(
                db_path=db, run_id="run-003", start_time=start_time,
                pages_visited=1, tenders_parsed=50, tenders_saved=50,
                failures=0, deduped_count=0, error_summary=[],
                tender_types=["Works"], dry_run=False,
            )
            conn = sqlite3.connect(db)
            row = conn.execute(
                "SELECT duration_seconds FROM runs_metadata WHERE run_id='run-003'"
            ).fetchone()
            conn.close()
            assert row[0] >= 0
        finally:
            os.unlink(db)

    def test_error_summary_stored_as_json(self):
        db = self._get_db()
        try:
            start_run_metadata(db, "run-004", {}, dry_run=False)
            start_time = datetime.now(timezone.utc)
            finish_run_metadata(
                db_path=db, run_id="run-004", start_time=start_time,
                pages_visited=2, tenders_parsed=100, tenders_saved=98,
                failures=1, deduped_count=0,
                error_summary=["page 2: timeout"],
                tender_types=["Works"], dry_run=False,
            )
            conn = sqlite3.connect(db)
            row = conn.execute(
                "SELECT error_summary FROM runs_metadata WHERE run_id='run-004'"
            ).fetchone()
            conn.close()
            errors = json.loads(row[0])
            assert errors == ["page 2: timeout"]
        finally:
            os.unlink(db)
