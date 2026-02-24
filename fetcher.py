import base64
import json
import re
import secrets
import time
from typing import Iterator

import requests
import urllib3
from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA1
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import pad

from logger import get_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = get_logger(__name__)

BASE_URL    = "https://tender.nprocure.com"
API_URL     = f"{BASE_URL}/beforeLoginTenderTableList"
HOMEPAGE    = f"{BASE_URL}/"

_PASSPHRASE = base64.b64decode("ejdNcmw=").decode()
_KEY_B64    = "ejdNcmw="
_PBKDF2_ITER = 1000
_KEY_BYTES   = 16
_BLOCK_SIZE  = 16



def _aes_encrypt(plaintext: str, salt_hex: str, iv_hex: str) -> str:
    
    salt = bytes.fromhex(salt_hex)
    iv   = bytes.fromhex(iv_hex)
    key  = PBKDF2(
        _PASSPHRASE.encode(), salt,
        dkLen=_KEY_BYTES,
        count=_PBKDF2_ITER,
        prf=lambda p, s: HMAC.new(p, s, SHA1).digest(),
    )
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct = cipher.encrypt(pad(plaintext.encode("utf-8"), _BLOCK_SIZE))
    return base64.b64encode(ct).decode()


def _build_envelope(plain_dict: dict) -> dict:
    plaintext = json.dumps(plain_dict, separators=(",", ":"))
    iv_hex    = secrets.token_hex(_BLOCK_SIZE)
    salt_hex  = secrets.token_hex(_BLOCK_SIZE)
    return {
        "jsonData": _aes_encrypt(plaintext, salt_hex, iv_hex),
        "iv":       iv_hex,
        "salt":     salt_hex,
        "key":      _KEY_B64,
    }


def _build_req_data(display_start: int, display_length: int) -> dict:
  
    return {
        "reqData": [
            {"name": "sEcho",          "value": 1},
            {"name": "iColumns",       "value": 3},
            {"name": "sColumns",       "value": ",,"},
            {"name": "iDisplayStart",  "value": display_start},
            {"name": "iDisplayLength", "value": display_length},
            {"name": "mDataProp_0",    "value": "1"},
            {"name": "bSortable_0",    "value": True},
            {"name": "mDataProp_1",    "value": "2"},
            {"name": "bSortable_1",    "value": True},
            {"name": "mDataProp_2",    "value": "3"},
            {"name": "bSortable_2",    "value": False},
            {"name": "iSortCol_0",     "value": 0},
            {"name": "sSortDir_0",     "value": "asc"},
            {"name": "iSortingCols",   "value": 1},
        ],
        "_csrf":  "",
        "idList": "0",
        "id":     "Tenders In Progress",
    }



def make_session(user_agent: str, timeout: int) -> requests.Session:
  
    s = requests.Session()
    s.verify = False

    s.headers.update({
        "User-Agent":        user_agent,
        "Accept":            "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language":   "en-US,en;q=0.9",
        "Connection":        "keep-alive",
    })

    session_id = ""
    for url in [HOMEPAGE, f"{BASE_URL}/tenderSearchResult"]:
        try:
            resp = s.get(url, timeout=timeout)
            log.info("GET %s → HTTP %d", url, resp.status_code)

            session_id = s.cookies.get("TSESSIONID", "")

            if not session_id:
                raw = resp.headers.get("Set-Cookie", "")
                m = re.search(r"TSESSIONID=([A-F0-9a-f]+)", raw, re.I)
                if m:
                    session_id = m.group(1)

            if session_id:
                log.info("TSESSIONID acquired: %s…", session_id[:8])
                break
            log.debug("No TSESSIONID in %s, trying next URL", url)

        except requests.RequestException as exc:
            log.warning("Could not reach %s: %s", url, exc)

    if not session_id:
        log.warning(
            "TSESSIONID not found — API calls will likely return HTTP 500. "
            "Set TSESSIONID env var or ensure the site is reachable."
        )
        session_id = ""

    s.headers.update({
        "Accept":            "application/json, text/javascript, */*; q=0.01",
        "Content-Type":      "application/json",
        "X-Requested-With":  "XMLHttpRequest",
        "Origin":            BASE_URL,
        "Referer":           HOMEPAGE,
        "Cookie":            f"TSESSIONID={session_id}; {session_id}",
    })

    return s



def fetch_page(
    session: requests.Session,
    start: int,
    length: int,
    timeout: int,
    retries: int,
) -> dict:
   
    plain   = _build_req_data(start, length)
    payload = _build_envelope(plain)

    last_exc = None
    for attempt in range(1, retries + 2):        
        try:
            resp = session.post(API_URL, json=payload, timeout=timeout)

            if resp.status_code == 200:
                data = resp.json()
                log.debug(
                    "Page start=%d length=%d → %d records in response",
                    start, length, len(data.get("data", [])),
                )
                return data

            if resp.status_code in (500, 502, 503, 504):
                log.warning(
                    "HTTP %d at start=%d (attempt %d/%d) — retrying",
                    resp.status_code, start, attempt, retries + 1,
                )
                last_exc = requests.HTTPError(f"HTTP {resp.status_code}")
            else:
                resp.raise_for_status()

        except (requests.Timeout, requests.ConnectionError) as exc:
            log.warning(
                "Network error at start=%d (attempt %d/%d): %s",
                start, attempt, retries + 1, exc,
            )
            last_exc = exc

        if attempt <= retries:
            wait = 2 ** attempt
            log.info("Backing off %ds before retry…", wait)
            time.sleep(wait)

    raise RuntimeError(
        f"All {retries + 1} attempts failed for start={start}"
    ) from last_exc



def iter_raw_pages(
    session: requests.Session,
    config: dict,
) -> Iterator[tuple[list[dict], int]]:
   
    limit     = config["limit"]
    page_size = config["page_size"]
    rate_limit = config["rate_limit"]
    timeout   = config["timeout"]
    retries   = config["retries"]

    log.info("Fetching page 1 (start=0, length=%d)…", page_size)
    data  = fetch_page(session, 0, page_size, timeout, retries)
    total = data.get("iTotalRecords", 0)
    log.info("Server reports %d total tenders", total)

    if limit:
        total = min(total, limit)
        log.info("--limit applied: will fetch at most %d tenders", total)

    yield data.get("data", []), total

    start = page_size
    while start < total:
        time.sleep(rate_limit)
        batch_end = min(start + page_size, total)
        log.info("Fetching records %d–%d / %d…", start, batch_end, total)
        data = fetch_page(session, start, page_size, timeout, retries)
        yield data.get("data", []), total
        start += page_size
