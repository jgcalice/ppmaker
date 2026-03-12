"""Tests for template_service — filesystem scanning, metadata parsing, error handling."""

import json
from unittest.mock import patch


def test_list_templates_returns_both_scopes(temp_template_dir):
    """Should list templates from both global/ and local/ directories."""
    with patch(
        "services.template_service._get_template_base_path",
        return_value=temp_template_dir,
    ):
        from services.template_service import get_all_templates

        templates = get_all_templates()
        scopes = {t.scope for t in templates}
        assert "global" in scopes
        assert "local" in scopes
        assert len(templates) >= 2


def test_template_metadata_has_required_fields(temp_template_dir):
    """Each template must have id, name, scope, palette, layouts."""
    with patch(
        "services.template_service._get_template_base_path",
        return_value=temp_template_dir,
    ):
        from services.template_service import get_all_templates

        templates = get_all_templates()
        for t in templates:
            assert t.id
            assert t.name
            assert t.scope in ("global", "local")
            assert t.palette
            assert len(t.layouts) > 0
            assert t.font_title
            assert t.font_body


def test_palette_has_all_color_fields(temp_template_dir):
    """Palette must have primary, secondary, accent, background, text."""
    with patch(
        "services.template_service._get_template_base_path",
        return_value=temp_template_dir,
    ):
        from services.template_service import get_all_templates

        templates = get_all_templates()
        for t in templates:
            palette = t.palette
            assert palette.primary.startswith("#")
            assert palette.secondary.startswith("#")
            assert palette.accent.startswith("#")
            assert palette.background.startswith("#")
            assert palette.text.startswith("#")


def test_empty_template_dir_returns_empty_list(tmp_path):
    """Should return empty list if template_padrao is empty."""
    (tmp_path / "global").mkdir()
    (tmp_path / "local").mkdir()

    with patch(
        "services.template_service._get_template_base_path",
        return_value=tmp_path,
    ):
        from services.template_service import get_all_templates

        templates = get_all_templates()
        assert templates == []


def test_invalid_json_is_skipped_with_warning(temp_template_dir):
    """Corrupted .json files should be skipped, not crash the service."""
    # Write a corrupt file
    (temp_template_dir / "global" / "broken.json").write_text(
        "{invalid json!!!", encoding="utf-8"
    )

    with patch(
        "services.template_service._get_template_base_path",
        return_value=temp_template_dir,
    ):
        from services.template_service import get_all_templates

        templates = get_all_templates()
        # Should still have the valid templates, broken one skipped
        ids = [t.id for t in templates]
        assert "test-template" in ids
        assert "broken" not in ids


def test_get_template_metadata_returns_correct_template(temp_template_dir):
    """get_template_metadata should return the specific template by ID."""
    with patch(
        "services.template_service._get_template_base_path",
        return_value=temp_template_dir,
    ):
        from services.template_service import get_template_metadata

        meta = get_template_metadata("test-template")
        assert meta is not None
        assert meta.id == "test-template"
        assert meta.name == "Test Template"


def test_get_template_metadata_returns_none_for_unknown(temp_template_dir):
    """get_template_metadata should return None for unknown ID."""
    with patch(
        "services.template_service._get_template_base_path",
        return_value=temp_template_dir,
    ):
        from services.template_service import get_template_metadata

        meta = get_template_metadata("nonexistent-template")
        assert meta is None


def test_missing_scope_dir_is_handled(tmp_path):
    """If only global/ exists (no local/), should not crash."""
    (tmp_path / "global").mkdir()
    # No local/ directory

    meta = {
        "id": "only-global",
        "name": "Only Global",
        "scope": "global",
        "palette": {
            "primary": "#000000",
            "secondary": "#111111",
            "accent": "#222222",
            "background": "#FFFFFF",
            "text": "#333333",
        },
        "layouts": ["title"],
        "font_title": "Arial",
        "font_body": "Arial",
    }
    (tmp_path / "global" / "only-global.json").write_text(
        json.dumps(meta), encoding="utf-8"
    )

    with patch(
        "services.template_service._get_template_base_path",
        return_value=tmp_path,
    ):
        from services.template_service import get_all_templates

        templates = get_all_templates()
        assert len(templates) == 1
        assert templates[0].id == "only-global"
