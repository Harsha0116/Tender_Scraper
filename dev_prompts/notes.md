# LLM Usage During Development

An LLM (Claude) was used as a development aid during this project.
**No LLM is called at runtime.** The scraper is entirely self-contained.

---

## What the LLM helped with

### 1. Initial recon
Prompted to inspect the site's JS bundle for AJAX endpoints.
Result: identified `AesUtil.js`, `aes.js`, `pbkdf2.js` — confirmed encryption.

### 2. Decrypting the captured payload
Key breakthrough: provided the live-captured cURL request from Chrome DevTools.
The LLM wrote a Python snippet to decrypt the payload using the iv/salt/key
fields present in the request body, revealing the exact plaintext structure:
  {"reqData":[{"name":"sEcho","value":1}, ...], "_csrf":"", "idList":"0", "id":"Tenders In Progress"}
This was the root cause of all earlier 500 errors — we were sending the
wrong plaintext structure.

### 3. Architecture design
Prompted to design a clean separation of concerns:
fetcher / parser / cleaner / persistence.

### 4. Schema design
Prompted to think through what metadata fields would be most useful for
debugging and observability.

---

## What was NOT used

- No LLM agents, LangChain, AutoGPT, or search-driven LLMs.
- No LLM API calls anywhere in the runnable code.
- All business logic (encryption, parsing, cleaning, persistence) was written
  and verified by the developer.
