import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logger as _logger_mod

_logger_mod.setup_logger("test-run")



SAMPLE_HTML_WORKS = """
<html><body>
<span style=color:#f44336; >R&B-R&B Division, Mahisagar
<form action='/view-nit-home' method='POST' target='_blank'>
<input type='hidden' name='tenderid' value='280210'/>
<a href='#' id='tenderInProgress'>Tender Id :280210</a>
</form></span>
<span style=color:#FF9933; >
<form action='/view-nit-home' method='POST'>
<input type='hidden' name='tenderid' value='280210'/>
<a href='#'><strong style='color: maroon;'>Name Of Work :</strong>
Renovation and Repairing work of Emergency Exit at I.T.I. Khanpur</a>
</form></span>
<p style=color:#FF9933;> Estimated Contract Value : 5998400.40
<p style=color:#000000;> Last Date &amp; Time For Submission : 05-03-2026 18:05:00
</body></html>
"""

SAMPLE_HTML_GOODS = """
<html><body>
<span style=color:#f44336; >AMC-Cattle Nuisance Control Department - Ahmedabad
<form action='/view-nit-home'>
<input type='hidden' name='tenderid' value='280056'/>
<a href='#' id='tenderInProgress'>Tender Id :280056</a>
</form></span>
<span style=color:#FF9933;>
<form action='/view-nit-home'>
<input type='hidden' name='tenderid' value='280056'/>
<a href='#'><strong style='color: maroon;'>Name Of Work :</strong>
Supply of drugs, medicine and instruments for veterinary staff</a>
</form></span>
<p style=color:#FF9933;> Estimated Contract Value : 3000000.00
<p style=color:#000000;> Last Date &amp; Time For Submission : 03-03-2026 15:00:00
</body></html>
"""

SAMPLE_HTML_SERVICES = """
<html><body>
<span style=color:#f44336; >EDUCATION-L. M. College of Pharmacy - Ahmedabad
<form action='/view-nit-home'>
<input type='hidden' name='tenderid' value='279385'/>
<a href='#' id='tenderInProgress'>Tender Id :279385</a>
</form></span>
<span style=color:#FF9933;>
<form action='/view-nit-home'>
<input type='hidden' name='tenderid' value='279385'/>
<a href='#'><strong style='color: maroon;'>Name Of Work :</strong>
Provide service for College Security Services and housekeeping services</a>
</form></span>
<p style=color:#FF9933; style='display:none'> Estimated Contract Value :
<p style=color:#000000;> Last Date &amp; Time For Submission : 10-03-2026 18:00:00
</body></html>
"""

SAMPLE_HTML_NO_TENDER_ID = """
<html><body>
<span style=color:#f44336;>SOME-Dept Name</span>
<p> Estimated Contract Value : 100000
<p> Last Date &amp; Time For Submission : 01-04-2026 12:00:00
</body></html>
"""

SAMPLE_DOC_CELL = """
<form action='/view-nit-document' method='POST'>
<input type='hidden' name='tenderid' value='280210'/>
<a href='#'>Total No:8</a>
</form>
"""


@pytest.fixture
def raw_works_item():
    return {"1": "15 of 2025-26", "2": SAMPLE_HTML_WORKS, "3": SAMPLE_DOC_CELL}


@pytest.fixture
def raw_goods_item():
    return {"1": "44 of 2025-2026", "2": SAMPLE_HTML_GOODS, "3": "<a>Total No:1</a>"}


@pytest.fixture
def raw_services_item():
    return {"1": "2026-HK AND SSA", "2": SAMPLE_HTML_SERVICES, "3": "<a>Total No:4</a>"}


@pytest.fixture
def raw_no_id_item():
    return {"1": "BAD-001", "2": SAMPLE_HTML_NO_TENDER_ID, "3": ""}


@pytest.fixture
def parsed_works_record():
    """A pre-parsed raw dict ready for cleaner.py input."""
    return {
        "tender_id":           "280210",
        "ifb_no":              "15 of 2025-26",
        "department":          "R&B-R&B Division, Mahisagar",
        "name_of_work":        "Renovation and Repairing work of Emergency Exit at I.T.I. Khanpur",
        "estimated_value_raw": "5998400.40",
        "last_submission_raw": "05-03-2026 18:05:00",
        "corrigendum":         "",
        "doc_count":           "Total No:8",
        "source_url":          "https://tender.nprocure.com/view-nit-home?tenderid=280210",
        "raw_html_snippet":    "<html>...",
    }


@pytest.fixture
def parsed_goods_record():
    return {
        "tender_id":           "280056",
        "ifb_no":              "44 of 2025-2026",
        "department":          "AMC-Cattle Nuisance Control Department - Ahmedabad",
        "name_of_work":        "Supply of drugs, medicine and instruments for veterinary staff",
        "estimated_value_raw": "3000000.00",
        "last_submission_raw": "03-03-2026 15:00:00",
        "corrigendum":         "",
        "doc_count":           "Total No:1",
        "source_url":          "https://tender.nprocure.com/view-nit-home?tenderid=280056",
        "raw_html_snippet":    "<html>...",
    }


@pytest.fixture
def parsed_missing_id_record():
    return {
        "tender_id":           "",
        "ifb_no":              "BAD-001",
        "department":          "SOME-Dept Name",
        "name_of_work":        "Some work description",
        "estimated_value_raw": "100000",
        "last_submission_raw": "01-04-2026",
        "corrigendum":         "",
        "doc_count":           "",
        "source_url":          "",
        "raw_html_snippet":    "",
    }
