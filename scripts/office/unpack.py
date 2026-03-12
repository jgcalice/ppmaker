"""Unpack Office files (PPTX, DOCX, XLSX) for editing.

Extracts the ZIP archive, pretty-prints XML files with 2-space indentation,
and converts smart quotes to XML entities for safe editing.

Ported from the Anthropic PPTX skill — DOCX-specific helpers (merge_runs,
simplify_redlines) are omitted; the core PPTX extraction path is preserved.

Usage:
    python scripts/office/unpack.py <input.pptx> <output_dir>

Examples:
    python scripts/office/unpack.py template.pptx unpacked/
    python scripts/office/unpack.py presentation.pptx /tmp/work_dir/
"""

import argparse
import sys
import zipfile
from pathlib import Path

import defusedxml.minidom

SMART_QUOTE_REPLACEMENTS = {
    "\u201c": "&#x201C;",  # left double quotation mark
    "\u201d": "&#x201D;",  # right double quotation mark
    "\u2018": "&#x2018;",  # left single quotation mark
    "\u2019": "&#x2019;",  # right single quotation mark
}


def unpack(input_file: str, output_directory: str) -> tuple[None, str]:
    """
    Extract a PPTX (or DOCX/XLSX) to a directory with pretty-printed XML.

    Parameters
    ----------
    input_file : str
        Path to the Office file (.pptx / .docx / .xlsx).
    output_directory : str
        Destination directory (created if it does not exist).

    Returns
    -------
    tuple[None, str]
        (None, message) — message starts with "Error" on failure.
    """
    input_path = Path(input_file)
    output_path = Path(output_directory)
    suffix = input_path.suffix.lower()

    if not input_path.exists():
        return None, f"Error: {input_file} does not exist"

    if suffix not in {".docx", ".pptx", ".xlsx"}:
        return None, f"Error: {input_file} must be a .docx, .pptx, or .xlsx file"

    try:
        output_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(input_path, "r") as zf:
            zf.extractall(output_path)

        xml_files = list(output_path.rglob("*.xml")) + list(output_path.rglob("*.rels"))
        for xml_file in xml_files:
            _pretty_print_xml(xml_file)

        for xml_file in xml_files:
            _escape_smart_quotes(xml_file)

        message = f"Unpacked {input_file} ({len(xml_files)} XML files) to {output_directory}"
        return None, message

    except zipfile.BadZipFile:
        return None, f"Error: {input_file} is not a valid Office file (bad ZIP)"
    except Exception as exc:
        return None, f"Error unpacking {input_file}: {exc}"


def _pretty_print_xml(xml_file: Path) -> None:
    """Re-serialize XML with 2-space indentation for human-readable editing."""
    try:
        content = xml_file.read_bytes()
        dom = defusedxml.minidom.parseString(content)
        xml_file.write_bytes(dom.toprettyxml(indent="  ", encoding="utf-8"))
    except Exception:
        pass  # Leave unparseable files (e.g., binary rels) as-is


def _escape_smart_quotes(xml_file: Path) -> None:
    """Replace smart-quote characters with XML entities."""
    try:
        content = xml_file.read_text(encoding="utf-8")
        for char, entity in SMART_QUOTE_REPLACEMENTS.items():
            content = content.replace(char, entity)
        xml_file.write_text(content, encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Unpack a PPTX (or DOCX/XLSX) for XML editing"
    )
    parser.add_argument("input_file", help="Office file to unpack (.pptx / .docx / .xlsx)")
    parser.add_argument("output_directory", help="Destination directory for extracted XML")
    args = parser.parse_args()

    _, message = unpack(args.input_file, args.output_directory)
    print(message)

    if message.startswith("Error"):
        sys.exit(1)
