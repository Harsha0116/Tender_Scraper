import re
from bs4 import BeautifulSoup

from logger import get_logger

log = get_logger(__name__)


def parse_raw_record(item: dict) -> dict:
   
    ifb_no        = item.get("1", "")
    html_cell     = item.get("2", "")
    doc_cell      = item.get("3", "")

    soup = BeautifulSoup(html_cell, "html.parser")
    text = soup.get_text(" ", strip=True)

    tender_id = ""
    m = re.search(r"Tender Id\s*:(\d+)", text)
    if m:
        tender_id = m.group(1)

    department = ""
    red_span = soup.find("span", style=lambda s: s and "f44336" in s)
    if red_span:
        raw = red_span.get_text(" ", strip=True)
        department = re.sub(r"Tender Id\s*:\d+", "", raw).strip()

    name_of_work = ""
    m = re.search(
        r"Name Of Work\s*:(.*?)(?:Corrigendum\s*:|Estimated Contract Value|Last Date|$)",
        text, re.DOTALL,
    )
    if m:
        name_of_work = m.group(1).strip()

    estimated_value = ""
    m = re.search(r"Estimated Contract Value\s*:\s*([\d.]+)", text)
    if m:
        estimated_value = m.group(1)

    last_submission_raw = ""
    m = re.search(r"Last Date & Time For Submission\s*:\s*([\d\-:/ ]+)", text)
    if m:
        last_submission_raw = m.group(1).strip()

    corrigendum = ""
    m = re.search(r"Corrigendum\s*:\s*([^\n<]+)", text)
    if m:
        corrigendum = m.group(1).strip()

    doc_soup  = BeautifulSoup(doc_cell, "html.parser")
    doc_count = doc_soup.get_text(strip=True)

    source_url = ""
    if tender_id:
        source_url = f"https://tender.nprocure.com/view-nit-home?tenderid={tender_id}"

    if not tender_id:
        log.debug("Could not extract tender_id from record; ifb_no=%s", ifb_no)

    return {
        "tender_id":            tender_id,
        "ifb_no":               ifb_no,
        "department":           department,
        "name_of_work":         name_of_work,
        "estimated_value_raw":  estimated_value,
        "last_submission_raw":  last_submission_raw,
        "corrigendum":          corrigendum,
        "doc_count":            doc_count,
        "source_url":           source_url,
        "raw_html_snippet":     html_cell[:500],   # first 500 chars for debugging
    }


def parse_page(raw_items: list[dict]) -> list[dict]:
    parsed = []
    for item in raw_items:
        try:
            record = parse_raw_record(item)
            parsed.append(record)
        except Exception as exc:
            log.warning("Failed to parse item: %s — %s", item.get("1", "?"), exc)
    return parsed
