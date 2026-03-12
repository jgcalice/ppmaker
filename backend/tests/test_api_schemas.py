"""Tests for FastAPI API endpoints — response codes, validation, content types.

These tests require the FastAPI app to be importable (TestClient).
AI service is mocked to avoid external API calls.
"""

import json

import pytest


def test_templates_endpoint_returns_200_with_templates(client):
    """GET /api/v1/templates should return 200 with a templates list."""
    response = client.get("/api/v1/templates")
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    assert isinstance(data["templates"], list)


def test_storytelling_endpoint_validates_required_fields(client):
    """Missing 'content' must return 422."""
    response = client.post(
        "/api/v1/storytelling",
        json={"template_id": "test-template"},
    )
    assert response.status_code == 422


def test_storytelling_endpoint_validates_content_length(client):
    """Content > 5000 chars must return 422."""
    response = client.post(
        "/api/v1/storytelling",
        json={
            "content": "A" * 5001,
            "template_id": "test-template",
        },
    )
    assert response.status_code == 422


def test_storytelling_endpoint_accepts_valid_request(client):
    """Valid request should return 200 with SSE stream."""
    response = client.post(
        "/api/v1/storytelling",
        json={
            "content": "Resultados do Q1: crescemos 30% em receita.",
            "template_id": "test-template",
        },
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


def test_generate_pptx_with_unknown_template_returns_404(client):
    """POST /api/v1/generate-pptx with unknown template should return 404."""
    from tests.conftest import SAMPLE_OUTLINE

    response = client.post(
        "/api/v1/generate-pptx",
        json={
            "storytelling": SAMPLE_OUTLINE,
            "template_id": "nonexistent-template-xyz",
        },
    )
    assert response.status_code == 404


def test_generate_pptx_validates_required_fields(client):
    """Missing storytelling body must return 422."""
    response = client.post(
        "/api/v1/generate-pptx",
        json={"template_id": "test-template"},
    )
    assert response.status_code == 422


def test_storytelling_endpoint_missing_template_id(client):
    """Missing template_id must return 422."""
    response = client.post(
        "/api/v1/storytelling",
        json={"content": "Some valid content here."},
    )
    assert response.status_code == 422


def test_storytelling_endpoint_optional_fields(client):
    """audience, objective, tone should be optional."""
    response = client.post(
        "/api/v1/storytelling",
        json={
            "content": "Valid content about Q1 results.",
            "template_id": "test-template",
            "audience": "Diretoria executiva",
            "objective": "Informar resultados",
            "tone": "executive",
        },
    )
    assert response.status_code == 200
