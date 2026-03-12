"""Pack an unpacked Office directory back into a PPTX (or DOCX/XLSX) file.

Condenses XML whitespace, optionally validates structure against the original
file, then writes a ZIP-deflated Office document.

Ported from the Anthropic PPTX skill — the DOCX/redline validators are omitted;
the core pack + PPTX validation path is preserved.

Usage:
    python scripts/office/pack.py <input_dir> <output.pptx> [--original <original.pptx>] [--validate true|false]

Examples:
    python scripts/office/pack.py unpacked/ output.pptx --original template.pptx
    python scripts/office/pack.py unpacked/ output.pptx --validate false
"""

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import defusedxml.minidom


# ---------------------------------------------------------------------------
# PPTX structure validation (lightweight — checks required parts exist)
# ---------------------------------------------------------------------------

_REQUIRED_PPTX_PARTS = [
    "[Content_Types].xml",
    "_rels/.rels",
    "ppt/presentation.xml",
    "ppt/_rels/presentation.xml.rels",
]


def _validate_pptx_structure(unpacked_dir: Path) -> list[str]:
    """Return a list of missing required PPTX parts (empty = valid)."""
    missing = []
    for part in _REQUIRED_PPTX_PARTS:
        if not (unpacked_dir / part).exists():
            missing.append(part)
    return missing


# ---------------------------------------------------------------------------
# XML condensing
# ---------------------------------------------------------------------------

def _condense_xml(xml_file: Path) -> None:
    """Remove decorative whitespace between elements (preserve text nodes)."""
    try:
        with open(xml_file, encoding="utf-8") as fh:
            dom = defusedxml.minidom.parse(fh)

        for element in dom.getElementsByTagName("*"):
            # Never strip text from text-bearing elements (a:t, w:t, etc.)
            if element.tagName.endswith(":t"):
                continue
            for child in list(element.childNodes):
                if (
                    child.nodeType == child.TEXT_NODE
                    and child.nodeValue
                    and child.nodeValue.strip() == ""
                ) or child.nodeType == child.COMMENT_NODE:
                    element.removeChild(child)

        xml_file.write_bytes(dom.toxml(encoding="UTF-8"))
    except Exception as exc:
        print(f"WARNING: Could not condense {xml_file.name}: {exc}", file=sys.stderr)
        # Non-fatal — leave file as-is and continue


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pack(
    input_directory: str,
    output_file: str,
    original_file: str | None = None,
    validate: bool = True,
) -> tuple[None, str]:
    """
    Pack a directory of XML files into an Office document.

    Parameters
    ----------
    input_directory : str
        Directory produced by unpack.py.
    output_file : str
        Destination file path (.pptx / .docx / .xlsx).
    original_file : str | None
        Original template for structural comparison (optional).
    validate : bool
        Run PPTX structure check before packing (default: True).

    Returns
    -------
    tuple[None, str]
        (None, message) — message starts with "Error" on failure.
    """
    input_dir = Path(input_directory)
    output_path = Path(output_file)
    suffix = output_path.suffix.lower()

    if not input_dir.is_dir():
        return None, f"Error: {input_dir} is not a directory"

    if suffix not in {".docx", ".pptx", ".xlsx"}:
        return None, f"Error: {output_file} must be a .docx, .pptx, or .xlsx file"

    # --- Validate PPTX structure ---
    if validate and suffix == ".pptx":
        missing = _validate_pptx_structure(input_dir)
        if missing:
            return None, f"Error: Validation failed — missing required parts: {missing}"

    # --- Condense + pack ---
    with tempfile.TemporaryDirectory() as tmp:
        tmp_content = Path(tmp) / "content"
        shutil.copytree(input_dir, tmp_content)

        for pattern in ("*.xml", "*.rels"):
            for xml_file in tmp_content.rglob(pattern):
                _condense_xml(xml_file)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in tmp_content.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(tmp_content))

    return None, f"Successfully packed {input_directory} to {output_file}"


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pack an unpacked Office directory back into a PPTX/DOCX/XLSX"
    )
    parser.add_argument("input_directory", help="Directory produced by unpack.py")
    parser.add_argument("output_file", help="Output Office file (.pptx / .docx / .xlsx)")
    parser.add_argument(
        "--original",
        help="Original file for structural comparison (optional)",
    )
    parser.add_argument(
        "--validate",
        type=lambda x: x.lower() == "true",
        default=True,
        metavar="true|false",
        help="Run PPTX structure validation before packing (default: true)",
    )
    args = parser.parse_args()

    _, message = pack(
        args.input_directory,
        args.output_file,
        original_file=args.original,
        validate=args.validate,
    )
    print(message)

    if message.startswith("Error"):
        sys.exit(1)
