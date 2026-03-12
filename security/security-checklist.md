# PPMaker Security Checklist (MVP)

## Input Validation
- [ ] Content max length (5000 chars) enforced in backend
- [ ] template_id validated against allowlist (no path traversal)
- [ ] tone validated against allowed values
- [ ] Null bytes stripped from input

## API Security
- [ ] ANTHROPIC_API_KEY read from environment only (never hardcoded)
- [ ] API key not present in any log statement
- [ ] API key not returned in any error response
- [ ] CORS restricted to localhost:3000 (not wildcard *)

## File Handling
- [ ] PPTX generated in-memory (BytesIO), never written to disk
- [ ] Template files accessed via safe_template_path only
- [ ] No path traversal possible via template_id parameter

## LLM Security (OWASP LLM Top 10)
- [ ] System prompt includes guardrails bounding Claude's output to presentation content
- [ ] User content not treated as trusted instructions (LLM01: Prompt Injection)
- [ ] Claude output is used only for structured JSON parsing (not executed)

## Error Handling
- [ ] Production error responses do not expose stack traces
- [ ] Internal file paths not exposed in error messages
- [ ] 422 validation errors use FastAPI's standard format

## Operational
- [ ] .env.example exists (no real keys)
- [ ] .gitignore includes .env files
- [ ] No secrets in docker-compose.yml
