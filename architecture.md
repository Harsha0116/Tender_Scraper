# Architecture & Approach

## Approach: Direct API (XHR)

The scraper calls the site's internal JSON endpoint directly:

```
POST https://tender.nprocure.com/beforeLoginTenderTableList
```

### Why not a headless browser?

The tender table is populated via an AJAX call from `app.js` after page load.
A headless browser (Selenium/Playwright) would work but costs 5–10× more memory
and time, introduces non-determinism, and is harder to deploy reliably.
For a scheduled data pipeline, the API approach is faster, lighter, and more
predictable.

---

## Encryption — How It Was Cracked

The endpoint encrypts every request payload with AES-128-CBC + PBKDF2-SHA1.
This was reverse-engineered through the following steps:

### 1. Identify the encryption stack
Inspected the page's JS bundle. Found:
- `AesUtil.js` — key derivation + encrypt/decrypt wrapper
- `aes.js` — AES implementation (CryptoJS)
- `pbkdf2.js` — PBKDF2 key derivation

Parameters from `AesUtil.js`:
- Algorithm: AES-128-CBC
- Key derivation: PBKDF2-SHA1, 1000 iterations, 16-byte key
- Passphrase: base64-decoded from the `key` field sent in the request body

### 2. Capture a live request
Used Chrome DevTools → Network → Copy as cURL on the tender table XHR.
The request body contained:
```json
{
  "jsonData": "<base64 ciphertext>",
  "iv":       "<32-char hex>",
  "salt":     "<32-char hex>",
  "key":      "ejdNcmw="
}
```

### 3. Decrypt the captured payload (the key breakthrough)
Since all parameters needed to decrypt are present in the request itself,
we decrypted the captured `jsonData` using `iv`, `salt`, and the passphrase
decoded from `key`. This revealed the exact plaintext structure:

```json
{
  "reqData": [
    {"name": "sEcho",          "value": 1},
    {"name": "iColumns",       "value": 3},
    {"name": "sColumns",       "value": ",,"},
    {"name": "iDisplayStart",  "value": 0},
    {"name": "iDisplayLength", "value": 50},
    {"name": "mDataProp_0",    "value": "1"},
    {"name": "bSortable_0",    "value": true},
    {"name": "mDataProp_1",    "value": "2"},
    {"name": "bSortable_1",    "value": true},
    {"name": "mDataProp_2",    "value": "3"},
    {"name": "bSortable_2",    "value": false},
    {"name": "iSortCol_0",     "value": 0},
    {"name": "sSortDir_0",     "value": "asc"},
    {"name": "iSortingCols",   "value": 1}
  ],
  "_csrf":  "",
  "idList": "0",
  "id":     "Tenders In Progress"
}
```

This is **DataTables v1.9 legacy format** — completely different from the
modern DataTables format. All prior 500 errors were caused by guessing the
wrong plaintext structure. Decrypting the real browser request solved it instantly.

### 4. Session handling quirk
NIC's server sets a cookie literally named `null` alongside `TSESSIONID`.
Python's `cookielib` rejects the malformed `null` cookie and can silently
drop `TSESSIONID` too. Fix: manually regex-parse the `Set-Cookie` header.
The cookie must also be sent as `TSESSIONID=VALUE; VALUE` (bare value repeated)
to match the exact format the server validates.

---

## Separation of Concerns

```
scrape.py         Orchestration only. No business logic.
  │
  ├── config.py       Read CLI args + env vars → plain config dict
  ├── logger.py       One logger, run_id injected into every line
  ├── fetcher.py      Network I/O only
  │                     - Session + cookie management
  │                     - AES payload encryption
  │                     - Paginated iteration
  │                     - Retry with exponential backoff
  │                   Returns: raw API dicts
  ├── parser.py       HTML extraction only
  │                     - BeautifulSoup parsing of 3 HTML fields per record
  │                     - No normalisation or type inference
  │                   Returns: raw string dicts
  ├── cleaner.py      Normalisation only
  │                     - Date parsing → ISO 8601
  │                     - Tender type classification (keyword rules)
  │                     - Whitespace + boilerplate stripping
  │                   Returns: clean record dicts
  └── persistence.py  Storage only
                        - JSON / NDJSON file writes
                        - Within-run + cross-run deduplication
                        - SQLite run metadata
```

Each module is independently testable with fixture data.

---

## Reliability Features

| Feature | Where |
|---------|-------|
| Retry + exponential backoff | `fetcher.fetch_page` — waits 2^attempt seconds |
| Configurable rate limit | `fetcher.iter_raw_pages` — `time.sleep(rate_limit)` |
| Idempotent writes | `persistence.save_records` — cross-run dedup by tender_id |
| Partial run recovery | Metadata row written at start, updated at end |
| All knobs configurable | `config.py` — CLI flags and env vars |
| run_id correlation | `logger.RunIdFilter` — every log line carries run_id |

---

## Production Hardening Notes

- **Scheduler**: Wrap `scrape.py` in cron or Airflow. Incremental dedup
  makes repeated daily runs safe with no extra logic.
- **Partitioned output**: Use `tenders_YYYY-MM.ndjson` naming for time-partitioned
  exports that stay manageable in size.
- **Alerting**: Query `runs_metadata` for `failures > 0` or `end_time IS NULL`
  as a simple health check after each run.
- **Concurrency**: `--concurrency` is wired into config. Replace the
  synchronous `fetcher.py` with `asyncio` + `aiohttp` for true parallelism.
