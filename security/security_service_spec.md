# Security Service Specification

**File:** `PROJECT_ROOT/backend/services/security_service.py`
**Dependencies:** stdlib only (re, os, pathlib, typing)

## Purpose

Centralized input validation and sanitization for PPMaker. Imported by backend routers to validate all user-supplied inputs before any business logic executes.

## Functions

### `validate_content(content: str) -> str`
- Rejects empty/whitespace-only content
- Strips null bytes (`\x00`)
- Enforces max length of 5000 characters
- Collapses 10+ consecutive newlines to 3 (whitespace bomb mitigation)
- Returns sanitized, stripped content

### `validate_template_id(template_id: str, known_template_ids: list[str]) -> str`
- Rejects empty template_id
- Validates format: alphanumeric, dashes, underscores only (max 64 chars)
- Checks against allowlist of known template IDs loaded from filesystem
- Prevents path traversal by design (no slashes, dots, or special chars allowed)

### `validate_tone(tone: Optional[str]) -> str`
- Returns "professional" if tone is None
- Validates against allowlist: {"professional", "casual", "executive"}

### `safe_template_path(template_id: str, scope: str, base_dir: Path) -> Path`
- Constructs resolved filesystem path for template
- Verifies resolved path stays within base_dir (path traversal guard)
- Defense-in-depth: even if validate_template_id is bypassed, this prevents filesystem escape

## Error Handling

All validation functions raise `SecurityError(ValueError)` on failure. Callers should catch `SecurityError` and return 422 to the client.

## Integration

Backend routers should call these functions at the top of each endpoint handler, before any service calls. Example:

```python
from services.security_service import validate_content, validate_template_id, SecurityError

@router.post("/storytelling")
async def create_storytelling(request: StorytellingRequest):
    try:
        content = validate_content(request.content)
        template_ids = [t.id for t in get_all_templates()]
        validate_template_id(request.template_id, template_ids)
    except SecurityError as e:
        raise HTTPException(status_code=422, detail=str(e))
    # ... proceed with business logic
```
