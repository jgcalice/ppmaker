# ADR-003: Visual Placeholder Strategy for Missing Data Slides

## Status: Accepted

## Context

When users input their content into PPMaker, they often describe what they want to present without having all the data ready. For example, a user might write "show quarterly revenue growth" without providing the actual numbers. The AI storytelling engine identifies these slides and marks them with `has_placeholder: true` and a descriptive `placeholder_hint` (e.g., "Grafico de barras: evolucao trimestral de receita").

The generated PPTX must clearly communicate to the user: **"this slide needs a chart or data here — here's what type of content to add."** The placeholder must be:
1. **Visually obvious**: Users must immediately recognize that the slide is incomplete
2. **Informative**: The hint text must guide the user on what to insert (chart type, data description)
3. **Easy to replace**: Users must be able to select and delete the placeholder, then insert their actual chart/image in PowerPoint or Google Slides
4. **Non-disruptive**: The placeholder should not break the template's visual identity or cause rendering issues

## Options Considered

| Option | User Clarity | Editability | Implementation | Visual Quality |
|--------|-------------|-------------|----------------|----------------|
| **Text-only reminder** ("INSIRA GRAFICO AQUI") | Low — easy to miss in body text | Easy | Trivial | Low — looks like an error |
| **Dashed-border rectangle + hint text (chosen)** | High — visually distinct shape | Medium — select shape, delete, insert chart | Simple — python-pptx shape + line style | Good — professional appearance |
| **Empty white space** | None — user has no guidance | N/A | Trivial | N/A — invisible |
| **Placeholder image with watermark** | Medium — recognizable but static | Hard — must delete image, resize new content | Complex — requires generating/storing images | Medium — generic appearance |

## Decision

We chose a **dashed-border rectangle with the template's accent color**, containing the AI-generated `placeholder_hint` text as a visual reminder. The rectangle uses a transparent fill so the slide background shows through, and the dashed border creates a clear "insert here" visual cue familiar to users from design tools.

## Implementation Spec

```python
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn

def add_placeholder_shape(slide, placeholder_hint: str, accent_color: str = "#6366F1"):
    """Add a dashed-border placeholder rectangle to a slide.

    Args:
        slide: python-pptx slide object
        placeholder_hint: AI-generated hint text describing what to insert
        accent_color: Hex color for the dashed border (from template palette)
    """
    # Position: centered, below title area
    left = Inches(1.0)
    top = Inches(2.5)
    width = Inches(8.0)
    height = Inches(3.5)

    # Add rectangle shape
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        left, top, width, height
    )

    # Parse accent color
    r = int(accent_color[1:3], 16)
    g = int(accent_color[3:5], 16)
    b = int(accent_color[5:7], 16)

    # Dashed border with accent color
    shape.line.color.rgb = RGBColor(r, g, b)
    shape.line.width = Pt(1.5)

    # Set dash style via XML (python-pptx doesn't expose dash style directly)
    ln = shape.line._ln
    ln.set(qn('prstDash'), 'dash')

    # Transparent fill (no fill)
    shape.fill.background()

    # Add hint text
    tf = shape.text_frame
    tf.word_wrap = True

    # Icon + hint line
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = placeholder_hint
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(r, g, b)
    run.font.bold = True

    # Instruction line
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    run2 = p2.add_run()
    run2.text = "[Substituir por grafico ou dado real]"
    run2.font.size = Pt(11)
    run2.font.color.rgb = RGBColor(0xA1, 0xA1, 0xAA)
    run2.font.italic = True
```

### Shape Behavior in PowerPoint/Google Slides
- **PowerPoint**: User clicks the rectangle, presses Delete, then inserts their chart/image in the same area. The dashed border makes it immediately obvious this is a placeholder.
- **Google Slides**: Same workflow — click, delete, insert. Google Slides renders the dashed border correctly.

## Consequences

### Good
- **Immediate recognition**: The dashed border is a universal "insert here" visual convention — users understand it without instructions
- **AI-guided hints**: The `placeholder_hint` from the storytelling engine tells users exactly what type of content to add (e.g., "Grafico de barras: comparativo de market share Q1-Q4"), reducing guesswork
- **Template-consistent**: Using the template's accent color for the border keeps the placeholder visually integrated with the presentation's color scheme
- **Easy to replace**: A single shape that can be selected and deleted in one click, then replaced with actual content
- **No external dependencies**: Implementation uses only python-pptx built-in features and minimal XML manipulation

### Bad
- **Dash style via XML**: python-pptx doesn't expose line dash style through its high-level API; we must manipulate the underlying XML (`prstDash` attribute), which is slightly fragile
- **Fixed positioning**: The placeholder rectangle uses fixed coordinates (1" left, 2.5" top, 8" wide, 3.5" tall). This works well for standard 16:9 slides but may need adjustment if templates use non-standard dimensions
- **No chart suggestion**: The placeholder is a visual hint only — it doesn't pre-configure a chart type. Users must create their charts from scratch

## Fitness Function

**Test**: For every slide in a generated PPTX where `has_placeholder=true` in the source outline, the corresponding slide must contain at least one rectangular shape with:
1. A dashed border (verify `prstDash` attribute in shape XML)
2. Visible text containing the `placeholder_hint` value
3. Border color matching the template's accent color (within RGB delta < 5)

Automated test: generate PPTX from an outline with 2+ placeholder slides, extract slide XML, assert shape presence and properties.
