"""
Utility script to create PPTX template files for PPMaker.
Run once after installing dependencies: python create_template.py

TEMPLATES
---------

1. Global template (template-01.pptx)
   - Scope: global
   - Palette: blues/red (generic corporate)
     PRIMARY:    #003087  (dark blue)
     SECONDARY:  #E31837  (red)
     ACCENT:     #FFB81C  (gold)
     BACKGROUND: #FFFFFF  (white)
     TEXT:       #1A1A1A  (near black)
   - Uses python-pptx default blank presentation with standard slide layouts.
   - pptx_service.py adds slides dynamically using layouts by index (0-5).

2. Local Corporate template (local-corporate.pptx)
   - Scope: local
   - Palette extracted from 4 real example .pptx files (2 analyzed successfully):
     PRIMARY:    #0766FF  (blue — most common fill color, 120 occurrences)
     SECONDARY:  #00328D  (dark navy — dominant text/bg color, 252 text runs)
     ACCENT:     #FFA41B  (amber/orange — accent color)
     BACKGROUND: #FFFFFF  (white slide background)
     TEXT:       #00328D  (navy — most common text color)
   - Fonts found: Avantt (primary), Avannt (variant), Quire Sans, Montserrat
     Template uses Calibri as fallback (universally available on Windows/Office)
   - Slide size: 12192000 x 6858000 EMU (13.33" x 7.50" — 16:9 widescreen)
   - Structural patterns observed in examples:
     * Full-slide background shape at position (0,0) on every slide
     * Recurring brand mark at position (200,200) EMU on 21/35 slides
     * Blue header bar (#0766FF) spanning full width at top
     * Dark navy footer bar (#00328D) spanning full width at bottom
     * Orange accent line (#FFA41B) as section separator
     * Body text in navy (#00328D) on white backgrounds
     * Green status indicators (#2DA703, #00B050) for KPIs/status
   - Contains 6 slides (one per layout type):
     [0] title             — Cover: navy bg, blue top band, orange separator
     [1] content           — Blue header, white body, bullet list, navy footer
     [2] two-column        — Header + two side-by-side content columns
     [3] chart-placeholder — Header + large gray chart area placeholder
     [4] image-text        — Header + image placeholder left + text right
     [5] closing           — Full navy bg, blue band, "Obrigado!" centered
   - Template file: template_padrao/local/local-corporate.pptx
   - Metadata file: template_padrao/local/local-corporate.json
   - Creation script: ../create_local_template_v2.py

LAYOUT INDEX MAPPING (used by pptx_service.py)
-----------------------------------------------
pptx_service.LAYOUT_INDEX_MAP maps layout names to slide layout indices:
    title             -> 0
    content           -> 1
    two-column        -> 2
    chart-placeholder -> 3
    image-text        -> 4
    closing           -> 5

The local template uses python-pptx's default layouts (indices 0-10 available),
and the 6 visual slides are pre-built reference slides for visual design.
When generating a presentation, pptx_service.py:
  1. Loads the .pptx template
  2. Calls _remove_existing_slides() to clear reference slides
  3. Adds new slides using prs.slide_layouts[idx] for each outline slide
  4. Applies brand colors from the palette JSON to text/shapes
"""
import os
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN


# Global template colors (generic corporate)
PRIMARY = RGBColor(0x00, 0x30, 0x87)
SECONDARY = RGBColor(0xE3, 0x18, 0x37)
ACCENT = RGBColor(0xFF, 0xB8, 0x1C)
BACKGROUND = RGBColor(0xFF, 0xFF, 0xFF)
TEXT_COLOR = RGBColor(0x1A, 0x1A, 0x1A)

SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)


def create_template():
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    # We need to work with the slide master to define layouts
    # python-pptx has limited support for creating layouts from scratch,
    # so we'll use the default presentation which comes with standard layouts.
    # The standard layouts are:
    # 0: Title Slide
    # 1: Title and Content
    # 2: Section Header
    # 3: Two Content
    # 4: Comparison
    # 5: Title Only
    # 6: Blank
    # etc.

    # We'll create a presentation with slides using each layout we need,
    # then remove the slides (keeping just the layouts).
    # For PPMaker, we map:
    #   title -> layout 0 (Title Slide)
    #   content -> layout 1 (Title and Content)
    #   two-column -> layout 3 (Two Content)
    #   chart-placeholder -> layout 5 (Title Only) - we'll add chart area dynamically
    #   image-text -> layout 1 (Title and Content) - repurposed
    #   closing -> layout 0 (Title Slide) - repurposed for closing

    # The template just needs to exist as a valid .pptx with these layouts available.
    # Our pptx_service.py will add slides dynamically.

    # Save the template (empty, with default layouts)
    template_dir = Path(__file__).resolve().parent.parent / "template_padrao" / "global"
    template_dir.mkdir(parents=True, exist_ok=True)
    output_path = template_dir / "template-01.pptx"

    prs.save(str(output_path))
    print(f"Template created at: {output_path}")


if __name__ == "__main__":
    create_template()
