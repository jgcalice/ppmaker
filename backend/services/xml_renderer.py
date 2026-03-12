"""XML-based PPTX renderer — third (preferred) rendering path.

Generates a PPTX by:
  1. Copying the template to a TemporaryDirectory
  2. Unpacking via scripts/office/unpack.py
  3. For each slide in the outline:
       a. Selecting the best-matching model slide from the layout catalog
       b. Duplicating it with scripts/add_slide.py
       c. Editing the slide XML directly (title, bullets, placeholder_hint)
  4. Cleaning orphaned files with scripts/clean.py
  5. Repacking with scripts/office/pack.py
  6. Reading the result into io.BytesIO

XML editing rules (Anthropic PPTX editing.md):
  - Separate <a:r> for each paragraph — NEVER concatenate into a single run
  - Bold titles: rPr b="1"
  - Smart quotes as XML entities: &#x201C; / &#x201D;
  - Parse with defusedxml.minidom (NEVER xml.etree.ElementTree)
  - Use <a:buChar char="&#x2022;"/> for bullets, never unicode • in text runs

Public contract:

    def generate_pptx_xml(
        outline: StorytellingOutline,
        template_path: str,
        template_meta: TemplateInfo,
    ) -> io.BytesIO

Raises RuntimeError if scripts are missing.
Raises subprocess.CalledProcessError on script failure (allows fallback).
"""

import io
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import defusedxml.minidom

from models.schemas import StorytellingOutline, TemplateInfo, SlideOutline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Script path resolution
# ---------------------------------------------------------------------------

def _project_root() -> Path:
    """Resolve the project root (parent of backend/)."""
    return Path(__file__).resolve().parent.parent.parent


def _scripts_root() -> Path:
    return _project_root() / "scripts"


def _script(relative: str) -> str:
    """Return the absolute path to a script under scripts/."""
    return str(_scripts_root() / relative)


def _check_scripts() -> None:
    """Raise RuntimeError if any required script is missing."""
    required = [
        "office/unpack.py",
        "office/pack.py",
        "add_slide.py",
        "clean.py",
    ]
    missing = [r for r in required if not (_scripts_root() / r).exists()]
    if missing:
        raise RuntimeError(
            f"XML renderer: required scripts not found in "
            f"{_scripts_root()}: {missing}"
        )


# ---------------------------------------------------------------------------
# Layout catalog — pick best slide model for each outline slide
# ---------------------------------------------------------------------------

_LAYOUT_PREFERENCE = {
    "title":              ["title", "section", "closing"],
    "content":            ["content", "bullets", "body"],
    "two-column":         ["two-column", "content", "body"],
    "chart-placeholder":  ["chart", "data", "content"],
    "image-text":         ["image", "photo", "content"],
    "closing":            ["closing", "title", "section"],
}


def _select_model_slide(
    unpacked_dir: Path,
    outline_slide: SlideOutline,
    catalog: list[dict] | None,
) -> str:
    """
    Return the filename of the best model slide to duplicate (e.g. 'slide2.xml').

    Strategy:
    1. If catalog is available, look for a slide whose use_for list matches
       the outline layout.
    2. Fall back to slide1.xml (always present after unpack).
    """
    slides_dir = unpacked_dir / "ppt" / "slides"
    layout = outline_slide.layout.lower()

    if catalog:
        preferences = _LAYOUT_PREFERENCE.get(layout, [layout, "content"])
        for pref in preferences:
            for entry in catalog:
                use_for = [u.lower() for u in entry.get("use_for", [])]
                if pref in use_for:
                    idx = entry.get("slide_index", 0) + 1  # 1-based
                    candidate = slides_dir / f"slide{idx}.xml"
                    if candidate.exists():
                        logger.debug(
                            "Layout '%s' → model slide slide%d.xml (catalog match '%s')",
                            layout, idx, pref,
                        )
                        return f"slide{idx}.xml"

    # Default: slide1.xml (title slide)
    if (slides_dir / "slide1.xml").exists():
        return "slide1.xml"

    # Last resort: first .xml in slides dir
    existing = sorted(slides_dir.glob("slide*.xml"))
    return existing[0].name if existing else "slide1.xml"


# ---------------------------------------------------------------------------
# XML editing helpers
# ---------------------------------------------------------------------------

_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _smart_quote(text: str) -> str:
    """Replace curly quotes with XML entities."""
    return (
        text
        .replace("\u201c", "&#x201C;")
        .replace("\u201d", "&#x201D;")
        .replace("\u2018", "&#x2018;")
        .replace("\u2019", "&#x2019;")
    )


def _make_run_xml(text: str, bold: bool = False, font_name: str = "") -> str:
    """Build a minimal <a:r> XML fragment as a string."""
    rpr_attrs = ""
    if bold:
        rpr_attrs += ' b="1"'
    if font_name:
        latin = f'<a:latin typeface="{font_name}"/>'
        rpr = f"<a:rPr lang=\"pt-BR\"{rpr_attrs}>{latin}</a:rPr>"
    else:
        rpr = f'<a:rPr lang="pt-BR"{rpr_attrs}/>' if (bold or rpr_attrs) else "<a:rPr/>"
    escaped_text = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    # Apply smart-quote entity replacement after escaping
    escaped_text = (
        escaped_text
        .replace("&#x201C;", "&#x201C;")  # preserve entity literals
        .replace("&#x201D;", "&#x201D;")
    )
    return f"<a:r>{rpr}<a:t>{escaped_text}</a:t></a:r>"


def _build_paragraph_xml(
    text: str,
    bold: bool = False,
    is_bullet: bool = False,
    font_name: str = "",
) -> str:
    """Build a <a:p> XML fragment for a title or bullet line."""
    bullet_part = ""
    if is_bullet:
        bullet_part = '<a:pPr><a:buChar char="&#x2022;"/></a:pPr>'
    else:
        bullet_part = "<a:pPr><a:buNone/></a:pPr>"

    run = _make_run_xml(text, bold=bold, font_name=font_name)
    return f"<a:p>{bullet_part}{run}</a:p>"


# ---------------------------------------------------------------------------
# Slide XML content injection
# ---------------------------------------------------------------------------

def _clear_text_bodies(slide_path: Path) -> None:
    """
    Remove all <a:t> text content from a slide XML, leaving structure intact.
    This clears template placeholder text before injecting new content.
    """
    content = slide_path.read_text(encoding="utf-8")
    # Replace text in <a:t> elements with empty string, preserving tags
    content = re.sub(r"(<a:t[^>]*>)[^<]*(</a:t>)", r"\1\2", content)
    slide_path.write_text(content, encoding="utf-8")


def _inject_slide_content(
    slide_path: Path,
    outline_slide: SlideOutline,
    font_title: str,
    font_body: str,
) -> None:
    """
    Write title and talking points into the slide XML.

    Approach: parse with defusedxml.minidom, find the first significant
    text body (txBody) for title, second for body/bullets.  If the structure
    is too different, fall back to a string-injection approach.
    """
    try:
        _inject_via_dom(slide_path, outline_slide, font_title, font_body)
    except Exception as exc:
        logger.warning(
            "DOM injection failed for slide %d (%s) — trying string fallback",
            outline_slide.index, exc,
        )
        try:
            _inject_via_string(slide_path, outline_slide, font_title, font_body)
        except Exception as exc2:
            logger.warning(
                "String injection also failed for slide %d: %s — leaving content as-is",
                outline_slide.index, exc2,
            )


def _inject_via_dom(
    slide_path: Path,
    outline_slide: SlideOutline,
    font_title: str,
    font_body: str,
) -> None:
    """Inject content using minidom — preserves namespace declarations."""
    content = slide_path.read_bytes()
    doc = defusedxml.minidom.parseString(content)

    tx_bodies = doc.getElementsByTagNameNS(_NS_P, "txBody")
    if not tx_bodies:
        tx_bodies = doc.getElementsByTagNameNS(_NS_A, "txBody")

    if not tx_bodies:
        raise RuntimeError("No txBody elements found")

    def _set_txbody_text(tx_body, lines: list[str], bold: bool = False, bullets: bool = False):
        """Replace all <a:p> children of a txBody with fresh paragraphs."""
        # Remove existing paragraphs
        a_p_elements = tx_body.getElementsByTagNameNS(_NS_A, "p")
        for p in list(a_p_elements):
            if p.parentNode is tx_body:
                tx_body.removeChild(p)

        # Build new paragraph XML and parse-in via a wrapper
        paras_xml = ""
        for line in lines:
            safe = _smart_quote(line)
            paras_xml += _build_paragraph_xml(safe, bold=bold, is_bullet=bullets, font_name=font_body if not bold else font_title)

        wrapper_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<root xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            + paras_xml
            + "</root>"
        )
        wrapper_doc = defusedxml.minidom.parseString(wrapper_xml.encode("utf-8"))
        for p_node in wrapper_doc.documentElement.childNodes:
            imported = doc.importNode(p_node, deep=True)
            tx_body.appendChild(imported)

    # First txBody → title
    _set_txbody_text(tx_bodies[0], [outline_slide.title], bold=True, bullets=False)

    # Second txBody → bullets (if present)
    if len(tx_bodies) > 1:
        body_lines = list(outline_slide.talking_points)
        if outline_slide.has_placeholder and outline_slide.placeholder_hint:
            body_lines.append(f"[ {outline_slide.placeholder_hint} ]")
        _set_txbody_text(tx_bodies[1], body_lines, bold=False, bullets=True)

    slide_path.write_bytes(doc.toxml(encoding="utf-8"))


def _inject_via_string(
    slide_path: Path,
    outline_slide: SlideOutline,
    font_title: str,
    font_body: str,
) -> None:
    """
    Fallback: clear all a:t text, then insert a minimal txBody replacement
    by locating the first <p:sp> (title placeholder by convention).
    """
    _clear_text_bodies(slide_path)

    content = slide_path.read_text(encoding="utf-8")

    title_safe = _smart_quote(outline_slide.title)
    title_para = _build_paragraph_xml(title_safe, bold=True, is_bullet=False, font_name=font_title)

    body_paras = ""
    for pt in outline_slide.talking_points:
        safe = _smart_quote(pt)
        body_paras += _build_paragraph_xml(safe, bold=False, is_bullet=True, font_name=font_body)
    if outline_slide.has_placeholder and outline_slide.placeholder_hint:
        safe = _smart_quote(f"[ {outline_slide.placeholder_hint} ]")
        body_paras += _build_paragraph_xml(safe, bold=False, is_bullet=False, font_name=font_body)

    # Inject title into first empty <a:txBody>
    new_title_body = (
        "<a:txBody>"
        "<a:bodyPr/>"
        "<a:lstStyle/>"
        + title_para
        + "</a:txBody>"
    )
    content = re.sub(
        r"<a:txBody>\s*<a:bodyPr[^/]*/>\s*<a:lstStyle[^/]*/>\s*</a:txBody>",
        new_title_body,
        content,
        count=1,
    )

    # Inject body into second empty <a:txBody>
    if body_paras:
        new_body_body = (
            "<a:txBody>"
            "<a:bodyPr/>"
            "<a:lstStyle/>"
            + body_paras
            + "</a:txBody>"
        )
        content = re.sub(
            r"<a:txBody>\s*<a:bodyPr[^/]*/>\s*<a:lstStyle[^/]*/>\s*</a:txBody>",
            new_body_body,
            content,
            count=1,
        )

    slide_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# sldIdLst registration
# ---------------------------------------------------------------------------

def _register_slide_in_presentation(unpacked_dir: Path, new_slide_name: str, rid: str, slide_id: int) -> None:
    """Add <p:sldId> entry to ppt/presentation.xml sldIdLst."""
    pres_path = unpacked_dir / "ppt" / "presentation.xml"
    content = pres_path.read_text(encoding="utf-8")

    entry = f'<p:sldId id="{slide_id}" r:id="{rid}"/>'
    if rid not in content:
        content = re.sub(
            r"(</p:sldIdLst>)",
            f"  {entry}\n\\1",
            content,
        )
        pres_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# add_slide subprocess wrapper
# ---------------------------------------------------------------------------

def _run_add_slide(unpacked_dir: Path, source: str) -> tuple[str, str, int]:
    """
    Run add_slide.py and parse its stdout for the new filename, rId, and sldId.

    Returns
    -------
    tuple[str, str, int]
        (new_slide_name, rid, slide_id)
    """
    result = subprocess.run(
        [sys.executable, _script("add_slide.py"), str(unpacked_dir), source],
        capture_output=True,
        text=True,
        check=True,
    )
    output = result.stdout.strip()

    # Parse: "Created slideN.xml from ..."
    name_match = re.search(r"Created (slide\d+\.xml)", output)
    new_name = name_match.group(1) if name_match else None

    # Parse: 'Add to presentation.xml <p:sldIdLst>: <p:sldId id="NNN" r:id="rIdN"/>'
    rid_match = re.search(r'r:id="(rId\d+)"', output)
    rid = rid_match.group(1) if rid_match else None

    sid_match = re.search(r'id="(\d+)"', output)
    slide_id = int(sid_match.group(1)) if sid_match else 256

    if not new_name or not rid:
        raise RuntimeError(
            f"add_slide.py output could not be parsed: {output!r}"
        )

    return new_name, rid, slide_id


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_pptx_xml(
    outline: StorytellingOutline,
    template_path: str,
    template_meta: TemplateInfo,
) -> io.BytesIO:
    """
    Generate a PPTX via unpack → edit XML slide-by-slide → pack.

    Uses tempfile.TemporaryDirectory() as context manager so cleanup is
    guaranteed even on exception.

    Parameters
    ----------
    outline : StorytellingOutline
        Structured slide outline to render.
    template_path : str
        Path to the base template .pptx.
    template_meta : TemplateInfo
        Palette, font, and layout metadata.

    Returns
    -------
    io.BytesIO
        In-memory PPTX buffer, seeked to position 0.

    Raises
    ------
    RuntimeError
        If required scripts are absent.
    subprocess.CalledProcessError
        If a script subprocess fails (allows caller to fall back).
    """
    _check_scripts()

    font_title = template_meta.font_title or "Calibri"
    font_body = template_meta.font_body or "Calibri"

    # Load catalog if available (best-effort; None = use default model slide)
    catalog: list[dict] | None = None
    try:
        import json as _json
        template_dir = os.path.dirname(os.path.abspath(template_path))
        catalog_path = os.path.normpath(
            os.path.join(template_dir, "..", "..", "tools", "layout_catalog.json")
        )
        if not os.path.isfile(catalog_path):
            catalog_path = os.path.normpath(
                os.path.join(template_dir, "..", "..", "..", "tools", "layout_catalog.json")
            )
        if os.path.isfile(catalog_path):
            with open(catalog_path, "r", encoding="utf-8") as fh:
                catalog_data = _json.load(fh)
                catalog = catalog_data.get("catalog", [])
    except Exception as exc:
        logger.warning("Could not load layout catalog: %s", exc)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        unpacked_dir = tmp_path / "unpacked"
        output_pptx = tmp_path / "output.pptx"

        # --- 1. Copy template to temp ---
        tmp_template = tmp_path / "template.pptx"
        try:
            with open(template_path, "rb") as fh:
                tmp_template.write_bytes(fh.read())
        except OSError as exc:
            raise RuntimeError(f"Cannot read template file {template_path!r}: {exc}") from exc

        # --- 2. Unpack ---
        result = subprocess.run(
            [sys.executable, _script("office/unpack.py"), str(tmp_template), str(unpacked_dir)],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.debug("unpack.py: %s", result.stdout.strip())

        # --- 3. Remove original slides from sldIdLst (keep layouts/masters) ---
        #   We will add only the slides we need from the outline.
        #   Strategy: keep all slides as templates but remove their sldIdLst entries,
        #   then add duplicates for each outline slide.
        _clear_sldidlst(unpacked_dir)

        # --- 4. Add & populate slides ---
        for slide_data in outline.slides:
            model_slide = _select_model_slide(unpacked_dir, slide_data, catalog)
            logger.debug(
                "Slide %d ('%s') → duplicate %s",
                slide_data.index, slide_data.layout, model_slide,
            )

            new_name, rid, slide_id = _run_add_slide(unpacked_dir, model_slide)

            # Register in sldIdLst
            _register_slide_in_presentation(unpacked_dir, new_name, rid, slide_id)

            # Inject content
            new_slide_path = unpacked_dir / "ppt" / "slides" / new_name
            _inject_slide_content(new_slide_path, slide_data, font_title, font_body)

        # --- 5. Clean orphaned files ---
        result = subprocess.run(
            [sys.executable, _script("clean.py"), str(unpacked_dir)],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.debug("clean.py: %s", result.stdout.strip())

        # --- 6. Pack ---
        result = subprocess.run(
            [
                sys.executable,
                _script("office/pack.py"),
                str(unpacked_dir),
                str(output_pptx),
                "--original", str(tmp_template),
                "--validate", "true",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.debug("pack.py: %s", result.stdout.strip())

        # --- 7. Read into BytesIO ---
        pptx_bytes = output_pptx.read_bytes()

    buffer = io.BytesIO(pptx_bytes)
    buffer.seek(0)

    if buffer.getbuffer().nbytes > 50 * 1024 * 1024:
        raise ValueError("Generated PPTX exceeds 50 MB size limit")

    logger.info(
        "XML renderer produced %d-byte PPTX for outline '%s'",
        buffer.getbuffer().nbytes, outline.title,
    )
    return buffer


# ---------------------------------------------------------------------------
# sldIdLst helper
# ---------------------------------------------------------------------------

def _clear_sldidlst(unpacked_dir: Path) -> None:
    """
    Empty the <p:sldIdLst> in presentation.xml so we can rebuild it from scratch.
    Leaves the element itself (and its children attributes) intact but removes
    all <p:sldId> child entries.
    """
    pres_path = unpacked_dir / "ppt" / "presentation.xml"
    content = pres_path.read_text(encoding="utf-8")

    # Replace everything between <p:sldIdLst> and </p:sldIdLst>
    content = re.sub(
        r"(<p:sldIdLst>)(.*?)(</p:sldIdLst>)",
        r"\1\3",
        content,
        flags=re.DOTALL,
    )
    pres_path.write_text(content, encoding="utf-8")
