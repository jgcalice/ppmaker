# PPMaker Template Creation Guide

How to create templates compatible with PPMaker. Each template is a `.pptx` file paired with a `.json` metadata file.

---

## File Structure

Templates live in `template_padrao/`:

```
template_padrao/
  global/          # Shared templates (ship with PPMaker)
    corporate.pptx
    corporate.json
  local/           # User-created templates
    my-team.pptx
    my-team.json
```

**Naming rule:** The `.pptx` and `.json` filenames must match exactly (this is the template `id`).

---

## JSON Metadata Schema

Each template needs a `.json` file with the following structure:

```json
{
  "id": "corporate",
  "name": "Corporate Standard",
  "scope": "global",
  "description": "Clean corporate template for executive presentations",
  "palette": ["#1E3A5F", "#FFFFFF", "#F59E0B", "#6366F1"],
  "layouts": {
    "title": "Title Slide",
    "content": "Content",
    "two-column": "Two Column",
    "chart-placeholder": "Chart Placeholder",
    "image-text": "Image and Text",
    "closing": "Closing Slide"
  },
  "defaults": {
    "font_title": "Calibri",
    "font_body": "Calibri",
    "font_size_title": 32,
    "font_size_body": 18
  }
}
```

### Field Reference

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique identifier, matches filename |
| `name` | string | yes | Display name shown in template picker UI |
| `scope` | `"global"` or `"local"` | yes | Determines which section it appears in |
| `description` | string | no | Short description shown on hover |
| `palette` | string[] | yes | 4 hex color values shown as swatches in the template card |
| `layouts` | object | yes | Maps layout keys to slide layout names in the .pptx file |
| `defaults` | object | no | Default font and size overrides |

### Layout Keys

Every template must provide all 6 layout mappings:

| Key | Purpose | When the AI uses it |
|---|---|---|
| `title` | Opening slide | First slide — presentation title, subtitle, date |
| `content` | Standard content | Most slides — title + bullet points |
| `two-column` | Side-by-side | Comparisons, pros/cons, before/after |
| `chart-placeholder` | Chart/data placeholder | When the AI detects data that needs a chart (marked as placeholder) |
| `image-text` | Image + text side by side | Visual storytelling slides |
| `closing` | Final slide | Thank you, Q&A, contact info |

The **value** for each key must match the **exact name** of a slide layout in the .pptx Slide Master.

---

## Creating the .pptx Template

### Step 1: Set Up Slide Master

Open PowerPoint and go to View > Slide Master. Create (or rename) 6 layouts with names that match your JSON `layouts` values.

### Step 2: Define Placeholders

Each layout must use standard PowerPoint placeholders (Title, Body, etc.) — not freeform text boxes. PPMaker uses `python-pptx` to populate these placeholders.

**Placeholder types used by PPMaker:**

| Placeholder | python-pptx index | Used in |
|---|---|---|
| Title | 0 | All layouts |
| Body / Content | 1 | content, two-column, closing |
| Subtitle | 1 | title layout |
| Picture | 13 | image-text |
| Chart | 12 | chart-placeholder (reserved, not auto-filled) |

### Step 3: Style the Layouts

Apply your visual identity:
- Background colors/images
- Logo placement
- Header/footer styles
- Color scheme for text and shapes

### Tips for python-pptx Compatibility

1. **Use named layouts in Slide Master.** PPMaker looks up layouts by name. If the name does not match the JSON, the slide will not render correctly.

2. **Keep text placeholders simple.** Do not nest SmartArt, tables, or grouped shapes inside placeholders. `python-pptx` writes to placeholders as plain text with formatting — complex objects inside placeholders will be overwritten.

3. **Use solid fills for shapes.** Solid color fills are fully preserved. Gradients are partially preserved (start/end colors) but effects like glow, reflection, and 3D are not reliably rendered by `python-pptx`.

4. **Avoid overlapping placeholders.** If two placeholders overlap, python-pptx may write content that visually collides. Keep clear spacing.

5. **Test with python-pptx.** After creating your template, run a quick test:
   ```python
   from pptx import Presentation
   prs = Presentation('my-template.pptx')
   for layout in prs.slide_layouts:
       print(f"Layout: {layout.name}")
       for ph in layout.placeholders:
           print(f"  Placeholder {ph.placeholder_format.idx}: {ph.name}")
   ```
   Verify that all 6 layouts appear with the expected placeholder indices.

6. **Fonts:** Use fonts that are commonly available (Calibri, Arial, etc.) or embed them. If a font is not available on the server, python-pptx will not substitute — the .pptx file will reference the missing font and PowerPoint will substitute at render time.

---

## Example: Adding a New Template

1. Design your template in PowerPoint with 6 named layouts in Slide Master.

2. Save as `my-template.pptx` in `template_padrao/local/`.

3. Create `template_padrao/local/my-template.json`:
   ```json
   {
     "id": "my-template",
     "name": "My Team Template",
     "scope": "local",
     "palette": ["#1A1A2E", "#E94560", "#0F3460", "#16213E"],
     "layouts": {
       "title": "Title Slide",
       "content": "Content Slide",
       "two-column": "Two Column Layout",
       "chart-placeholder": "Chart Slide",
       "image-text": "Image and Text",
       "closing": "Thank You"
     },
     "defaults": {
       "font_title": "Calibri",
       "font_body": "Calibri",
       "font_size_title": 36,
       "font_size_body": 16
     }
   }
   ```

4. Restart PPMaker (or refresh the page). Your template appears under "Templates Locais".

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Template not showing in UI | JSON missing or `id` mismatch | Ensure .json and .pptx filenames match |
| "Layout not found" error | Layout name in JSON does not match Slide Master | Open .pptx, check exact layout names in Slide Master |
| Text appears outside placeholder | Overlapping or misaligned placeholders | Reposition placeholders with clear margins |
| Formatting lost | Complex objects in placeholders | Simplify — use plain text placeholders only |
| Wrong placeholder filled | Placeholder index mismatch | Run the python-pptx test script to verify indices |
