import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser import parse_raw_record, parse_page


class TestParseRawRecord:

    def test_extracts_tender_id(self, raw_works_item):
        result = parse_raw_record(raw_works_item)
        assert result["tender_id"] == "280210"

    def test_extracts_ifb_no(self, raw_works_item):
        result = parse_raw_record(raw_works_item)
        assert result["ifb_no"] == "15 of 2025-26"

    def test_extracts_department(self, raw_works_item):
        result = parse_raw_record(raw_works_item)
        assert "R&B" in result["department"]
        assert "Mahisagar" in result["department"]

    def test_extracts_name_of_work(self, raw_works_item):
        result = parse_raw_record(raw_works_item)
        assert "Renovation" in result["name_of_work"]
        assert "I.T.I. Khanpur" in result["name_of_work"]

    def test_extracts_estimated_value(self, raw_works_item):
        result = parse_raw_record(raw_works_item)
        assert result["estimated_value_raw"] == "5998400.40"

    def test_extracts_last_submission_date(self, raw_works_item):
        result = parse_raw_record(raw_works_item)
        assert "05-03-2026" in result["last_submission_raw"]

    def test_extracts_doc_count(self, raw_works_item):
        result = parse_raw_record(raw_works_item)
        assert "8" in result["doc_count"]

    def test_builds_source_url(self, raw_works_item):
        result = parse_raw_record(raw_works_item)
        assert result["source_url"] == \
               "https://tender.nprocure.com/view-nit-home?tenderid=280210"

    def test_empty_source_url_when_no_tender_id(self, raw_no_id_item):
        result = parse_raw_record(raw_no_id_item)
        assert result["source_url"] == ""

    def test_empty_tender_id_when_missing(self, raw_no_id_item):
        result = parse_raw_record(raw_no_id_item)
        assert result["tender_id"] == ""

    def test_raw_html_snippet_max_500_chars(self, raw_works_item):
        result = parse_raw_record(raw_works_item)
        assert len(result["raw_html_snippet"]) <= 500

    def test_goods_item_tender_id(self, raw_goods_item):
        result = parse_raw_record(raw_goods_item)
        assert result["tender_id"] == "280056"

    def test_goods_item_name_of_work(self, raw_goods_item):
        result = parse_raw_record(raw_goods_item)
        assert "drugs" in result["name_of_work"].lower() or \
               "medicine" in result["name_of_work"].lower()

    def test_services_item_tender_id(self, raw_services_item):
        result = parse_raw_record(raw_services_item)
        assert result["tender_id"] == "279385"

    def test_all_expected_keys_present(self, raw_works_item):
        result = parse_raw_record(raw_works_item)
        expected_keys = [
            "tender_id", "ifb_no", "department", "name_of_work",
            "estimated_value_raw", "last_submission_raw", "corrigendum",
            "doc_count", "source_url", "raw_html_snippet"
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_empty_item_does_not_crash(self):
        result = parse_raw_record({"1": "", "2": "", "3": ""})
        assert result["tender_id"] == ""
        assert result["name_of_work"] == ""


class TestParsePage:

    def test_parses_multiple_items(self, raw_works_item, raw_goods_item):
        results = parse_page([raw_works_item, raw_goods_item])
        assert len(results) == 2

    def test_empty_list_returns_empty(self):
        assert parse_page([]) == []

    def test_bad_item_does_not_crash_whole_page(self):
        bad_item = {"1": "X", "2": None, "3": None}
        good_item = {"1": "15 of 2025", "2": "<html><body><span style=color:#f44336;>R&B-Div<form><input name='tenderid' value='111'/><a>Tender Id :111</a></form></span><p>Last Date &amp; Time For Submission : 01-04-2026</body></html>", "3": ""}
        results = parse_page([bad_item, good_item])
        tender_ids = [r["tender_id"] for r in results]
        assert "111" in tender_ids

    def test_returns_list_of_dicts(self, raw_works_item):
        results = parse_page([raw_works_item])
        assert isinstance(results, list)
        assert isinstance(results[0], dict)
