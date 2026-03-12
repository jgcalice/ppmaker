# PPMaker Threat Model (MVP)

**Date:** 2026-03-06
**Methodology:** STRIDE
**Scope:** PPMaker MVP — web app that takes user text input, calls Claude API, generates .pptx from filesystem templates. No user authentication.

---

## Assets to Protect

| Asset | Location | Sensitivity |
|-------|----------|-------------|
| ANTHROPIC_API_KEY | Environment variable | **Critical** — financial exposure if leaked |
| Template files (.pptx, .json) | Filesystem (`template_padrao/`) | Low — under version control, read-only |
| Generated PPTX | In-memory (BytesIO) | Medium — contains user content |
| User input (text content) | Request body, passed to Claude API | Medium — may contain confidential business data |

---

## Attack Surface

1. **POST /api/v1/storytelling** — accepts `content`, `template_id`, `audience`, `objective`, `tone`
2. **POST /api/v1/generate-pptx** — accepts `storytelling` outline + `template_id`
3. **GET /api/v1/templates** — lists available templates (read-only, low risk)
4. **Claude API call** — user content forwarded as LLM prompt
5. **Filesystem access** — template files read by `template_service.py`

---

## STRIDE Analysis

### S — Spoofing

| Threat | Surface | Risk | Control |
|--------|---------|------|---------|
| Identity spoofing | No auth in MVP | **L** | N/A — no identity to spoof. Acceptable for MVP. |

### T — Tampering

| Threat | Surface | Risk | Control |
|--------|---------|------|---------|
| Path traversal via `template_id` | `template_service.py:get_template_pptx_path()` constructs filesystem path from user-supplied `template_id` | **H** | Allowlist validation: `validate_template_id()` checks against known template IDs + regex pattern (alphanumeric/dash/underscore only). `safe_template_path()` resolves and verifies path stays within base directory. |
| Prompt injection via `content` | `ai_service.py` passes user content directly into Claude prompt | **M** | Input sanitization via `validate_content()`. System prompt instructs Claude to respond only with structured JSON. Content is interpolated into user message, not system prompt. |
| Tampering with template files | Filesystem | **L** | Templates under version control; no upload mechanism in MVP. |

### R — Repudiation

| Threat | Surface | Risk | Control |
|--------|---------|------|---------|
| No accountability for API usage | No auth = no user identity | **L** | Out of scope for MVP. Recommend structured logging of request metadata (IP, timestamp, content length) for future audit trail. |

### I — Information Disclosure

| Threat | Surface | Risk | Control |
|--------|---------|------|---------|
| API key in error responses | Exception handlers in routers use `detail=str(e)` | **H** | Error handler must strip environment variables and internal paths. Currently `routers/pptx.py:36` and `routers/storytelling.py:29` pass raw `str(e)` which could expose internal state. Recommend generic error messages in production. |
| API key in logs | `ai_service.py` reads key from env | **M** | Key is read via `os.environ.get()` and passed directly to client. No logging of the key observed. Recommend explicit audit to ensure no future log statement captures it. |
| Path traversal reading arbitrary files | `template_id` parameter | **H** | Mitigated by allowlist validation (see Tampering). |
| Stack traces in responses | FastAPI default debug mode | **M** | Ensure `debug=False` in production. FastAPI does not expose tracebacks by default in production mode. |

### D — Denial of Service

| Threat | Surface | Risk | Control |
|--------|---------|------|---------|
| Large content causing expensive Claude API calls | `content` field up to 5000 chars | **M** | Max 5000 chars enforced via Pydantic `max_length` in `StorytellingRequest`. `validate_content()` provides defense-in-depth. |
| Many concurrent requests causing API cost explosion | All endpoints | **M** | No rate limiting in MVP. Recommend adding rate limiting (e.g., SlowAPI) before production. Document as known risk. |
| Whitespace bomb in content | `content` field | **L** | `validate_content()` collapses excessive consecutive newlines. |
| PPTX generation timeout | `generate-pptx` endpoint | **L** | 30-second timeout enforced in `routers/pptx.py:24`. Claude call has 120-second timeout. |

### E — Elevation of Privilege

| Threat | Surface | Risk | Control |
|--------|---------|------|---------|
| N/A | No auth, no roles | **L** | No privilege system to escalate. |

---

## OWASP LLM Top 10 Relevance

| OWASP LLM | Applicability | Risk | Control |
|------------|--------------|------|---------|
| LLM01 — Prompt Injection | User content is interpolated into Claude prompt via `STORYTELLING_USER_PROMPT.format(content=content, ...)` | **M** | System prompt constrains output to JSON only. User content is in user message, not system prompt. Claude output is parsed as JSON, not executed. |
| LLM02 — Insecure Output Handling | Claude response parsed as JSON → used to build PPTX | **L** | Output is parsed via `json.loads()` and validated against Pydantic `StorytellingOutline`. No code execution of LLM output. |
| LLM04 — Model Denial of Service | Large/adversarial prompts | **M** | Content length capped at 5000 chars. Claude call has 120s timeout. |
| LLM06 — Sensitive Information Disclosure | Could Claude leak the API key? | **L** | API key is not in the conversation context (not in system prompt or user message). Claude cannot access environment variables. |

---

## Top 3 Risks (Prioritized)

1. **Path traversal via template_id** (HIGH) — Without allowlist validation, a crafted `template_id` like `../../etc/passwd` could read arbitrary files. **Mitigation:** `security_service.validate_template_id()` + `safe_template_path()`.

2. **API key exposure in error responses** (HIGH) — Exception handlers pass `str(e)` to HTTP responses, which could include internal details. **Mitigation:** Generic error messages; never pass raw exception strings to clients in production.

3. **API cost explosion via unbounded requests** (MEDIUM) — No rate limiting means an attacker can send thousands of requests, each triggering a Claude API call. **Mitigation:** Recommend rate limiting before production deployment.
