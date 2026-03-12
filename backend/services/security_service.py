import re
import os
from typing import Optional
from pathlib import Path

MAX_CONTENT_LENGTH = 5000
ALLOWED_TONES = {"professional", "casual", "executive"}
TEMPLATE_ID_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-_]{0,63}$')


class SecurityError(ValueError):
    """Raised when input fails security validation."""
    pass


def validate_content(content: str) -> str:
    """
    Validate and sanitize user content input.
    - Enforce max length
    - Strip null bytes
    - Remove excessive whitespace sequences (> 10 consecutive newlines)
    Returns sanitized content or raises SecurityError.
    """
    if not content or not content.strip():
        raise SecurityError("Content cannot be empty")

    # Remove null bytes
    content = content.replace('\x00', '')

    # Enforce max length
    if len(content) > MAX_CONTENT_LENGTH:
        raise SecurityError(f"Content exceeds maximum length of {MAX_CONTENT_LENGTH} characters")

    # Limit consecutive newlines (prevent whitespace bombs)
    content = re.sub(r'\n{10,}', '\n\n\n', content)

    return content.strip()


def validate_template_id(template_id: str, known_template_ids: list[str]) -> str:
    """
    Validate template_id to prevent path traversal attacks.
    - Must match alphanumeric/dash/underscore pattern
    - Must be in the list of known template IDs (loaded from filesystem)
    Returns template_id or raises SecurityError.
    """
    if not template_id:
        raise SecurityError("template_id cannot be empty")

    # Pattern check: alphanumeric, dashes, underscores only
    if not TEMPLATE_ID_PATTERN.match(template_id):
        raise SecurityError(f"Invalid template_id format: {template_id}")

    # Allowlist check: must be a known template
    if template_id not in known_template_ids:
        raise SecurityError(f"Template not found: {template_id}")

    return template_id


def validate_tone(tone: Optional[str]) -> str:
    """Validate tone is one of the allowed values."""
    if tone is None:
        return "professional"
    if tone not in ALLOWED_TONES:
        raise SecurityError(f"Invalid tone: {tone}. Must be one of: {ALLOWED_TONES}")
    return tone


def safe_template_path(template_id: str, scope: str, base_dir: Path) -> Path:
    """
    Construct a safe file path for a template, preventing path traversal.
    Raises SecurityError if the resolved path escapes base_dir.
    """
    resolved_base = base_dir.resolve()
    candidate = (resolved_base / scope / f"{template_id}.pptx").resolve()

    # Ensure the resolved path is inside base_dir
    if not str(candidate).startswith(str(resolved_base)):
        raise SecurityError(f"Path traversal detected for template_id: {template_id}")

    return candidate
