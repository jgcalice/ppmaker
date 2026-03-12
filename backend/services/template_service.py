import json
import logging
from pathlib import Path

from models.schemas import TemplateInfo
from services.security_service import safe_template_path

logger = logging.getLogger(__name__)


def _get_template_base_path() -> Path:
    """Return the path to template_padrao/ directory."""
    backend_dir = Path(__file__).resolve().parent.parent
    project_root = backend_dir.parent
    return project_root / "template_padrao"


def get_all_templates() -> list[TemplateInfo]:
    """Scan global/ and local/ for .json template metadata files."""
    base = _get_template_base_path()
    templates = []

    for scope in ("global", "local"):
        scope_dir = base / scope
        if not scope_dir.is_dir():
            continue
        for json_file in scope_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                templates.append(TemplateInfo(**data))
            except Exception:
                logger.warning("Skipping invalid template file: %s", json_file)
                continue

    return templates


def get_known_template_ids() -> list[str]:
    """Return list of all known template IDs."""
    return [t.id for t in get_all_templates()]


def get_template_pptx_path(template_id: str) -> Path | None:
    """Return the path to the .pptx file for a given template ID, with path traversal protection."""
    base = _get_template_base_path()
    for scope in ("global", "local"):
        try:
            pptx_path = safe_template_path(template_id, scope, base)
        except Exception:
            return None
        if pptx_path.is_file():
            return pptx_path
    return None


def get_template_metadata(template_id: str) -> TemplateInfo | None:
    """Return metadata for a specific template, with path traversal protection."""
    base = _get_template_base_path()
    for scope in ("global", "local"):
        try:
            # Use safe_template_path logic but for .json
            resolved_base = base.resolve()
            json_path = (resolved_base / scope / f"{template_id}.json").resolve()
            if not str(json_path).startswith(str(resolved_base)):
                return None
        except Exception:
            continue
        if json_path.is_file():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return TemplateInfo(**data)
            except Exception:
                logger.warning("Skipping invalid template metadata: %s", json_path)
                continue
    return None
