import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cleaner import (
    _clean_text,
    _parse_date,
    _classify_tender_type,
    _clean_organisation,
    _clean_description,
    _parse_value,
    _parse_doc_count,
    clean_record,
    clean_records,
)



class TestCleanText:
    def test_strips_leading_trailing_whitespace(self):
        assert _clean_text("  hello  ") == "hello"

    def test_collapses_multiple_spaces(self):
        assert _clean_text("hello   world") == "hello world"

    def test_replaces_newlines_with_space(self):
        assert _clean_text("hello\nworld") == "hello world"

    def test_replaces_carriage_returns(self):
        assert _clean_text("hello\r\nworld") == "hello world"

    def test_empty_string_returns_empty(self):
        assert _clean_text("") == ""

    def test_none_returns_empty(self):
        assert _clean_text(None) == ""

    def test_only_whitespace_returns_empty(self):
        assert _clean_text("   \n\t  ") == ""

    def test_normal_text_unchanged(self):
        assert _clean_text("Construction of road") == "Construction of road"



class TestParseDate:
    def test_dd_mm_yyyy_hhmmss(self):
        assert _parse_date("05-03-2026 18:05:00") == "2026-03-05"

    def test_dd_mm_yyyy_hhmm(self):
        assert _parse_date("03-03-2026 15:00") == "2026-03-03"

    def test_dd_mm_yyyy_only(self):
        assert _parse_date("25-03-2026") == "2026-03-25"

    def test_dd_slash_mm_slash_yyyy(self):
        assert _parse_date("25/03/2026") == "2026-03-25"

    def test_dd_slash_mm_slash_yyyy_with_time(self):
        assert _parse_date("25/03/2026 18:00:00") == "2026-03-25"

    def test_empty_string_returns_none(self):
        assert _parse_date("") is None

    def test_none_returns_none(self):
        assert _parse_date(None) is None

    def test_invalid_date_returns_none(self):
        assert _parse_date("not-a-date") is None

    def test_whitespace_around_date_handled(self):
        assert _parse_date("  10-03-2026 18:00:00  ") == "2026-03-10"

    def test_output_always_iso_format(self):
        result = _parse_date("01-01-2026")
        assert result == "2026-01-01"



class TestClassifyTenderType:
    def test_works_keyword_construction(self):
        assert _classify_tender_type("Construction of road bridge") == "Works"

    def test_works_keyword_repair(self):
        assert _classify_tender_type("Renovation and Repairing work at I.T.I.") == "Works"

    def test_works_keyword_pipeline(self):
        assert _classify_tender_type("Laying of pipeline and civil work") == "Works"

    def test_goods_keyword_supply(self):
        assert _classify_tender_type("Supply of medicines and equipment") == "Goods"

    def test_goods_keyword_purchase(self):
        assert _classify_tender_type("Purchase of glassware items") == "Goods"

    def test_goods_keyword_drug(self):
        assert _classify_tender_type("Providing drugs and instruments for veterinary") == "Goods"

    def test_services_keyword_security(self):
        assert _classify_tender_type("Security services and housekeeping") == "Services"

    def test_services_keyword_maintenance(self):
        assert _classify_tender_type("Annual maintenance of college premises") == "Services"

    def test_services_keyword_consultancy(self):
        assert _classify_tender_type("Consultancy for project management") == "Services"

    def test_goods_takes_priority_over_services(self):
        # "supply" (Goods) appears before "service" in text — Goods should win
        assert _classify_tender_type("Supply and maintenance service") == "Goods"

    def test_default_fallback_is_works(self):
        assert _classify_tender_type("Some completely unrelated text xyz") == "Works"

    def test_case_insensitive(self):
        assert _classify_tender_type("CONSTRUCTION OF BUILDING") == "Works"
        assert _classify_tender_type("SUPPLY OF GOODS") == "Goods"



class TestCleanOrganisation:
    def test_strips_code_prefix(self):
        assert _clean_organisation("R&B-R&B Division, Mahisagar") == "R&B Division, Mahisagar"

    def test_strips_amc_prefix(self):
        assert _clean_organisation("AMC-Cattle Nuisance Control Department - Ahmedabad") == \
               "Cattle Nuisance Control Department - Ahmedabad"

    def test_strips_gwssb_prefix(self):
        assert _clean_organisation("GWSSB-Public Health Circle - Junagadh") == \
               "Public Health Circle - Junagadh"

    def test_no_prefix_returned_as_is(self):
        assert _clean_organisation("Some Department Name") == "Some Department Name"

    def test_empty_returns_empty(self):
        assert _clean_organisation("") == ""

    def test_whitespace_trimmed(self):
        assert _clean_organisation("  AMC-Dept Name  ") == "Dept Name"



class TestCleanDescription:
    def test_strips_bid_documents_for(self):
        result = _clean_description("Bid Documents for construction of road")
        assert "Bid Documents for" not in result
        assert "construction of road" in result

    def test_strips_bid_document_to(self):
        result = _clean_description("Bid Document to provide services")
        assert "Bid Document to" not in result

    def test_strips_tender_for(self):
        result = _clean_description("Tender for supply of materials")
        assert "Tender for" not in result

    def test_strips_e_tender_for(self):
        result = _clean_description("E-Tender for civil works")
        assert "E-Tender for" not in result

    def test_normal_description_unchanged(self):
        result = _clean_description("Construction of road from A to B")
        assert result == "Construction of road from A to B"

    def test_collapses_whitespace(self):
        result = _clean_description("construction   of   road")
        assert "  " not in result



class TestParseValue:
    def test_valid_float_string(self):
        assert _parse_value("5998400.40") == 5998400.40

    def test_integer_string(self):
        assert _parse_value("3000000") == 3000000.0

    def test_zero_returns_none(self):
        assert _parse_value("0.00") is None

    def test_zero_int_returns_none(self):
        assert _parse_value("0") is None

    def test_empty_string_returns_none(self):
        assert _parse_value("") is None

    def test_none_returns_none(self):
        assert _parse_value(None) is None

    def test_non_numeric_returns_none(self):
        assert _parse_value("N/A") is None

    def test_large_value(self):
        assert _parse_value("1201021732.00") == 1201021732.0



class TestParseDocCount:
    def test_total_no_format(self):
        assert _parse_doc_count("Total No:8") == 8

    def test_total_no_with_space(self):
        assert _parse_doc_count("Total No: 12") == 12

    def test_just_number(self):
        assert _parse_doc_count("4") == 4

    def test_empty_string_returns_zero(self):
        assert _parse_doc_count("") == 0

    def test_none_returns_zero(self):
        assert _parse_doc_count(None) == 0

    def test_no_number_returns_zero(self):
        assert _parse_doc_count("No documents") == 0



class TestCleanRecord:
    def test_full_works_record(self, parsed_works_record):
        result = clean_record(parsed_works_record)
        assert result is not None
        assert result["tender_id"] == "280210"
        assert result["tender_type"] == "Works"
        assert result["closing_date"] == "2026-03-05"
        assert result["estimated_value"] == 5998400.40
        assert result["attachments"] == 8
        assert result["organisation"] == "R&B Division, Mahisagar"

    def test_goods_record(self, parsed_goods_record):
        result = clean_record(parsed_goods_record)
        assert result["tender_type"] == "Goods"
        assert result["estimated_value"] == 3000000.0
        assert result["closing_date"] == "2026-03-03"

    def test_missing_tender_id_returns_none(self, parsed_missing_id_record):
        assert clean_record(parsed_missing_id_record) is None

    def test_output_has_all_required_fields(self, parsed_works_record):
        result = clean_record(parsed_works_record)
        required = ["tender_id", "tender_type", "title", "organisation",
                    "publish_date", "closing_date", "description",
                    "source_url", "estimated_value", "attachments"]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_publish_date_always_none(self, parsed_works_record):
        # This endpoint does not expose publish_date
        result = clean_record(parsed_works_record)
        assert result["publish_date"] is None

    def test_source_url_preserved(self, parsed_works_record):
        result = clean_record(parsed_works_record)
        assert result["source_url"] == \
               "https://tender.nprocure.com/view-nit-home?tenderid=280210"

    def test_description_has_no_newlines(self, parsed_works_record):
        parsed_works_record["name_of_work"] = "Work\nwith\nnewlines"
        result = clean_record(parsed_works_record)
        assert "\n" not in result["description"]



class TestCleanRecords:
    def test_returns_cleaned_and_skipped_count(self, parsed_works_record, parsed_missing_id_record):
        raw_list = [parsed_works_record, parsed_missing_id_record]
        cleaned, skipped = clean_records(raw_list)
        assert len(cleaned) == 1
        assert skipped == 1

    def test_empty_list(self):
        cleaned, skipped = clean_records([])
        assert cleaned == []
        assert skipped == 0

    def test_all_valid_records(self, parsed_works_record, parsed_goods_record):
        cleaned, skipped = clean_records([parsed_works_record, parsed_goods_record])
        assert len(cleaned) == 2
        assert skipped == 0
