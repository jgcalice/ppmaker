import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Ensure backend package is importable
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


SAMPLE_OUTLINE = {
    "title": "Test Presentation",
    "objective": "Test objective",
    "audience": "Test audience",
    "total_slides": 3,
    "slides": [
        {
            "index": 0,
            "layout": "title",
            "title": "Introduction",
            "talking_points": ["Point 1", "Point 2"],
            "has_placeholder": False,
            "placeholder_hint": "",
        },
        {
            "index": 1,
            "layout": "content",
            "title": "Main Content",
            "talking_points": ["Detail A", "Detail B"],
            "has_placeholder": False,
            "placeholder_hint": "",
        },
        {
            "index": 2,
            "layout": "chart-placeholder",
            "title": "Results",
            "talking_points": ["Result X"],
            "has_placeholder": True,
            "placeholder_hint": "Bar chart: quarterly growth",
        },
    ],
}

SAMPLE_TEMPLATE_META = {
    "id": "test-template",
    "name": "Test Template",
    "scope": "global",
    "palette": {
        "primary": "#003087",
        "secondary": "#E31837",
        "accent": "#FFB81C",
        "background": "#FFFFFF",
        "text": "#1A1A1A",
    },
    "layouts": ["title", "content", "chart-placeholder"],
    "font_title": "Calibri",
    "font_body": "Calibri",
}


@pytest.fixture
def sample_outline():
    return SAMPLE_OUTLINE.copy()


@pytest.fixture
def sample_outline_model():
    from models.schemas import StorytellingOutline

    return StorytellingOutline(**SAMPLE_OUTLINE)


@pytest.fixture
def sample_template_meta():
    from models.schemas import TemplateInfo

    return TemplateInfo(**SAMPLE_TEMPLATE_META)


@pytest.fixture
def temp_template_dir(tmp_path):
    """Creates a temp directory with a valid template structure."""
    global_dir = tmp_path / "global"
    local_dir = tmp_path / "local"
    global_dir.mkdir()
    local_dir.mkdir()

    # Create template JSON
    (global_dir / "test-template.json").write_text(
        json.dumps(SAMPLE_TEMPLATE_META), encoding="utf-8"
    )

    # Create a local template too
    local_meta = SAMPLE_TEMPLATE_META.copy()
    local_meta["id"] = "local-template"
    local_meta["name"] = "Local Template"
    local_meta["scope"] = "local"
    (local_dir / "local-template.json").write_text(
        json.dumps(local_meta), encoding="utf-8"
    )

    return tmp_path


@pytest.fixture
def client():
    """FastAPI TestClient with mocked AI service."""
    from fastapi.testclient import TestClient

    with patch("routers.storytelling.generate_storytelling") as mock_ai, \
         patch("routers.storytelling.get_known_template_ids", return_value=["test-template"]):
        # Mock the SSE generator
        async def fake_sse(*args, **kwargs):
            outline_event = {"type": "outline", "data": SAMPLE_OUTLINE}
            yield f"data: {json.dumps(outline_event)}\n\n"
            yield f'data: {json.dumps({"type": "done"})}\n\n'

        mock_ai.side_effect = fake_sse

        from main import app

        with TestClient(app) as c:
            yield c
