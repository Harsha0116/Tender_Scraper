import re
from datetime import datetime
from typing import Optional

from logger import get_logger

log = get_logger(__name__)

SCRAPER_VERSION = "1.0.0"

_DATE_FORMATS = [
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d-%m-%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
]

_TYPE_RULES = [
    (
        "Goods",
        re.compile(
            r"\b(supply|purchase|procurement|material|equipment|goods|item|"
            r"glassware|drugs?|medicine|instruments?|furnish)\b",
            re.I,
        ),
    ),
    (
        "Services",
        re.compile(
            r"\b(service|maintenance|housekeep|security|consultanc|management|"
            r"operation|O&M|hire|outsourc|facility|software|AMC|annual)\b",
            re.I,
        ),
    ),
    (
        "Works",
        re.compile(
            r"\b(construct|civil|erect|repair|renovate|road|building|pipeline|"
            r"bridge|dam|canal|laying|install|work)\b",
            re.I,
        ),
    ),
]

_BOILERPLATE = re.compile(
    r"(bid documents? (for|to)|please refer|as per (the )?requirement|"
    r"tender for|e-tender for)",
    re.I,
)


def _clean_text(value: str) -> str:
    if not value:
        return ""
    value = value.replace("\n", " ").replace("\r", " ")
    value = re.sub(r"  +", " ", value)
    return value.strip()


def _parse_date(raw: str) -> Optional[str]:
 
    raw = _clean_text(raw)
    if not raw:
        return None
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    log.debug("Could not parse date: %r", raw)
    return None


def _classify_tender_type(text: str) -> str:
    for label, pattern in _TYPE_RULES:
        if pattern.search(text):
            return label
    return "Works"  


def _clean_organisation(dept: str) -> str:
   
    dept = _clean_text(dept)
    m = re.match(r"^[A-Z0-9&\-]+\s*-\s*(.+)", dept)
    if m:
        return m.group(1).strip()
    return dept


def _clean_description(raw: str) -> str:
    desc = _clean_text(raw)
    desc = _BOILERPLATE.sub("", desc).strip()
    desc = re.sub(r"  +", " ", desc)
    return desc


def _parse_value(raw: str) -> Optional[float]:
    try:
        v = float(raw)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def _parse_doc_count(raw: str) -> int:
    m = re.search(r"(\d+)", raw or "")
    return int(m.group(1)) if m else 0



def clean_record(raw: dict) -> dict:
    
    tender_id = raw.get("tender_id", "").strip()
    if not tender_id:
        log.debug("Skipping record with no tender_id (ifb_no=%s)", raw.get("ifb_no"))
        return None

    name_of_work = _clean_text(raw.get("name_of_work", ""))
    organisation = _clean_organisation(raw.get("department", ""))
    description  = _clean_description(name_of_work)
    tender_type  = _classify_tender_type(name_of_work)
    closing_date = _parse_date(raw.get("last_submission_raw", ""))
    est_value    = _parse_value(raw.get("estimated_value_raw", ""))
    doc_count    = _parse_doc_count(raw.get("doc_count", ""))

    return {
        "tender_id":        tender_id,
        "tender_type":      tender_type,
        "title":            _clean_text(raw.get("ifb_no", "")),
        "organisation":     organisation,
        "publish_date":     None,           # not exposed by this endpoint
        "closing_date":     closing_date,
        "description":      description,
        "source_url":       raw.get("source_url", ""),
        "estimated_value":  est_value,
        "attachments":      doc_count,
        "corrigendum":      _clean_text(raw.get("corrigendum", "")),
        "raw_html_snippet": raw.get("raw_html_snippet", ""),
    }


def clean_records(raw_list: list[dict]) -> tuple[list[dict], int]:
   
    cleaned = []
    skipped = 0
    for raw in raw_list:
        record = clean_record(raw)
        if record:
            cleaned.append(record)
        else:
            skipped += 1
    return cleaned, skipped
