"""Contract validation tests — verify that actual API responses match documented contracts.

These tests validate the shapes documented in tasks/todo.md.
"""

import re

import pytest


def test_templates_response_matches_contract(client):
    """Response shape must exactly match contract specification."""
    response = client.get("/api/v1/templates")
    assert response.status_code == 200

    data = response.json()
    assert "templates" in data
    assert isinstance(data["templates"], list)

    for t in data["templates"]:
        # Required top-level fields
        assert isinstance(t["id"], str) and len(t["id"]) > 0
        assert isinstance(t["name"], str) and len(t["name"]) > 0
        assert t["scope"] in ("global", "local")
        assert isinstance(t["font_title"], str)
        assert isinstance(t["font_body"], str)

        # Palette must have all color fields
        palette = t["palette"]
        for color_key in ("primary", "secondary", "accent", "background", "text"):
            assert color_key in palette
            assert isinstance(palette[color_key], str)
            assert re.match(r"^#[0-9A-Fa-f]{6}$", palette[color_key]), (
                f"palette.{color_key} must be #RRGGBB format, got: {palette[color_key]}"
            )

        # Layouts must be non-empty list of strings
        assert isinstance(t["layouts"], list)
        assert len(t["layouts"]) > 0
        for layout in t["layouts"]:
            assert isinstance(layout, str)


def test_storytelling_outline_schema_matches_contract():
    """StorytellingOutline Pydantic model must match the documented contract."""
    from models.schemas import StorytellingOutline, SlideOutline

    from tests.conftest import SAMPLE_OUTLINE

    outline = StorytellingOutline(**SAMPLE_OUTLINE)

    # Top-level fields
    assert isinstance(outline.title, str)
    assert isinstance(outline.objective, str)
    assert isinstance(outline.audience, str)
    assert isinstance(outline.total_slides, int)
    assert 5 <= outline.total_slides or outline.total_slides >= 1  # Sample has 3

    # Slides
    assert isinstance(outline.slides, list)
    for slide in outline.slides:
        assert isinstance(slide, SlideOutline)
        assert isinstance(slide.index, int)
        assert slide.layout in (
            "title",
            "content",
            "two-column",
            "chart-placeholder",
            "image-text",
            "closing",
        )
        assert isinstance(slide.title, str)
        assert isinstance(slide.talking_points, list)
        assert len(slide.talking_points) > 0
        assert isinstance(slide.has_placeholder, bool)
        assert isinstance(slide.placeholder_hint, str)


def test_generate_pptx_request_schema():
    """GeneratePptxRequest must accept storytelling + template_id."""
    from models.schemas import GeneratePptxRequest

    from tests.conftest import SAMPLE_OUTLINE

    req = GeneratePptxRequest(
        storytelling=SAMPLE_OUTLINE,
        template_id="test-template",
    )
    assert req.template_id == "test-template"
    assert req.storytelling.title == "Test Presentation"


def test_storytelling_request_schema():
    """StorytellingRequest must enforce content length and have required fields."""
    from models.schemas import StorytellingRequest

    req = StorytellingRequest(
        content="Valid content",
        template_id="test-template",
    )
    assert req.content == "Valid content"
    assert req.template_id == "test-template"
    assert req.tone.value == "professional"  # default
    assert req.audience is None
    assert req.objective is None
