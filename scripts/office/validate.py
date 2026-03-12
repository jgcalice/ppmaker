"""Validate an unpacked PPTX directory or packed PPTX file.

Checks required structural parts exist and XML files are well-formed.

Usage:
    python scripts/office/validate.py <path> [--original <original.pptx>]

The path can be either:
  - An unpacked directory containing the PPTX XML files
  - A packed .pptx file (unpacked to a temp directory for validation)
"""

import argparse
import sys
import tempfile
import zipfile
from pathlib import Path

import defusedxml.minidom


# ---------------------------------------------------------------------------
# Required PPTX structural parts
# ---------------------------------------------------------------------------

_REQUIRED_PPTX_PARTS = [
    "[Content_Types].xml",
    "_rels/.rels",
    "ppt/presentation.xml",
    "ppt/_rels/presentation.xml.rels",
]


def validate_pptx_structure(unpacked_dir: Path, verbose: bool = False) -> bool:
    """Check that all required PPTX parts are present."""
    missing = [p for p in _REQUIRED_PPTX_PARTS if not (unpacked_dir / p).exists()]
    if missing:
        print(f"FAILED - Missing required parts: {missing}")
        return False
    if verbose:
        print("PASSED - All required structural parts present")
    return True


def validate_xml_wellformed(unpacked_dir: Path, verbose: bool = False) -> bool:
    """Check that all XML/.rels files are well-formed."""
    errors = []
    for xml_file in list(unpacked_dir.rglob("*.xml")) + list(unpacked_dir.rglob("*.rels")):
        try:
            defusedxml.minidom.parseString(xml_file.read_bytes())
        except Exception as exc:
            errors.append(f"  {xml_file.relative_to(unpacked_dir)}: {exc}")

    if errors:
        print(f"FAILED - {len(errors)} malformed XML file(s):")
        for e in errors:
            print(e)
        return False
    if verbose:
        print(f"PASSED - All XML files are well-formed")
    return True


def validate(path: Path, original_file: Path | None = None, verbose: bool = False) -> bool:
    """Run all PPTX validations. Returns True if all pass."""
    if path.is_file() and path.suffix.lower() in {".pptx", ".docx", ".xlsx"}:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(tmp_dir)
            return validate(tmp_dir, original_file=original_file, verbose=verbose)

    if not path.is_dir():
        print(f"Error: {path} is not a directory or Office file")
        return False

    all_valid = True
    if not validate_pptx_structure(path, verbose=verbose):
        all_valid = False
    if not validate_xml_wellformed(path, verbose=verbose):
        all_valid = False

    if all_valid:
        print("All validations PASSED!")
    return all_valid


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a PPTX directory or file")
    parser.add_argument(
        "path",
        help="Path to unpacked directory or packed Office file (.pptx)",
    )
    parser.add_argument(
        "--original",
        default=None,
        help="Path to original file for comparison (optional)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"Error: {path} does not exist", file=sys.stderr)
        sys.exit(1)

    original = Path(args.original) if args.original else None
    success = validate(path, original_file=original, verbose=args.verbose)
    sys.exit(0 if success else 1)
