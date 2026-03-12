"""Tests for security validation — input limits, path traversal, sanitization.

Note: The backend currently uses Pydantic max_length=5000 for content validation
and relies on template_service.get_template_metadata returning None for unknown IDs.
These tests validate those security boundaries.
"""

import pytest

from models.schemas import StorytellingRequest, TemplateInfo
from pydantic import ValidationError


def test_validate_content_rejects_empty():
    """Empty content must be rejected by Pydantic validation."""
    with pytest.raises(ValidationError):
        StorytellingRequest(content="", template_id="test")


def test_validate_content_rejects_over_5000_chars():
    """Content exceeding 5000 characters must be rejected."""
    long_content = "A" * 5001
    with pytest.raises(ValidationError):
        StorytellingRequest(content=long_content, template_id="test")


def test_validate_content_accepts_exactly_5000_chars():
    """Content at exactly 5000 characters should be accepted."""
    content = "A" * 5000
    req = StorytellingRequest(content=content, template_id="test")
    assert len(req.content) == 5000


def test_validate_content_accepts_normal_input():
    """Normal-length content should be accepted."""
    req = StorytellingRequest(
        content="Apresentacao sobre resultados do Q1",
        template_id="test-template",
    )
    assert req.content == "Apresentacao sobre resultados do Q1"


def test_validate_template_id_rejects_path_traversal():
    """Path traversal attempts in template_id must not resolve to files outside template_padrao."""
    from unittest.mock import patch

    with patch(
        "services.template_service._get_template_base_path",
    ) as mock_base:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "global").mkdir()
            (base / "local").mkdir()
            mock_base.return_value = base

            from services.template_service import get_template_metadata

            # Path traversal attempt
            result = get_template_metadata("../../etc/passwd")
            assert result is None


def test_validate_template_id_rejects_unknown_id():
    """Unknown template IDs should return None, not crash."""
    from unittest.mock import patch

    with patch(
        "services.template_service._get_template_base_path",
    ) as mock_base:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "global").mkdir()
            (base / "local").mkdir()
            mock_base.return_value = base

            from services.template_service import get_template_metadata

            result = get_template_metadata("nonexistent-id-xyz")
            assert result is None


def test_validate_template_id_accepts_valid_id(temp_template_dir):
    """Valid template IDs should return metadata."""
    from unittest.mock import patch

    with patch(
        "services.template_service._get_template_base_path",
        return_value=temp_template_dir,
    ):
        from services.template_service import get_template_metadata

        result = get_template_metadata("test-template")
        assert result is not None
        assert result.id == "test-template"


def test_safe_template_path_prevents_traversal(tmp_path):
    """get_template_pptx_path must not resolve paths outside base_dir."""
    from unittest.mock import patch

    (tmp_path / "global").mkdir()
    (tmp_path / "local").mkdir()

    with patch(
        "services.template_service._get_template_base_path",
        return_value=tmp_path,
    ):
        from services.template_service import get_template_pptx_path

        # Path traversal: should not find anything
        result = get_template_pptx_path("../../../etc/passwd")
        assert result is None


def test_storytelling_request_rejects_invalid_tone():
    """Invalid tone values must be rejected."""
    with pytest.raises(ValidationError):
        StorytellingRequest(
            content="Valid content",
            template_id="test",
            tone="hacker",
        )


def test_storytelling_request_accepts_valid_tones():
    """All valid tone enum values should be accepted."""
    for tone in ("professional", "casual", "executive"):
        req = StorytellingRequest(
            content="Valid content",
            template_id="test",
            tone=tone,
        )
        assert req.tone.value == tone


def test_content_with_null_bytes():
    """Content with null bytes should be handled by Pydantic (not crash)."""
    # Pydantic v2 accepts strings with null bytes by default
    # This test documents current behavior
    req = StorytellingRequest(
        content="Hello\x00World",
        template_id="test",
    )
    assert "\x00" in req.content or "Hello" in req.content
