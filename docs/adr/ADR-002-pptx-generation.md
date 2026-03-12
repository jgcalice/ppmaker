# ADR-002: PPTX Generation Library

## Status: Accepted

## Context

PPMaker needs to generate `.pptx` files programmatically from pre-existing corporate templates. The generated files must preserve the visual identity of the template: brand colors, fonts, slide layouts, and background elements. Users will open these files in Microsoft PowerPoint and Google Slides.

Key requirements:
- **Template fidelity**: Read an existing `.pptx` template and add content while preserving its visual design (colors, fonts, layouts, backgrounds)
- **Text content insertion**: Add titles, bullet points, and formatted text to slides based on the AI-generated storytelling outline
- **Placeholder shapes**: Add visual placeholder shapes (dashed rectangles with hint text) for slides that need charts or data the user hasn't provided yet
- **Python-native**: The backend is FastAPI (Python); the library must integrate natively without subprocess calls or external service dependencies
- **No server-side Office**: We cannot install Microsoft Office or LibreOffice on the server
- **In-memory generation**: Generate the PPTX in a `BytesIO` buffer and stream it directly to the client without writing to disk

## Decision

We chose **python-pptx v0.6.x** (MIT license) as the PPTX generation library.

## Alternatives Considered

| Option | License | Template Fidelity | Complexity | Cost | Python-native |
|--------|---------|------------------|-----------|------|---------------|
| **python-pptx (chosen)** | MIT | Medium | Low | Free | Yes |
| **Aspose.Slides for Python** | Commercial | High | Medium | ~$1,000/yr | Yes (via .NET bridge) |
| **LibreOffice API (via subprocess)** | LGPL | High | High | Free | No (subprocess) |
| **HTML/CSS to PPTX (Reveal.js export)** | Various | Low | Medium | Free | No (JS toolchain) |
| **Google Slides API** | Proprietary | Medium | High | Free (quota-limited) | Yes (REST) |

### Why not Aspose?
Aspose.Slides offers superior template fidelity (SmartArt, animations, complex gradients) but costs ~$1,000/year and runs via a .NET bridge layer. For an MVP with simple templates designed within python-pptx's capabilities, the cost and complexity are not justified. If template fidelity becomes a critical issue post-MVP, Aspose is the natural upgrade path.

### Why not LibreOffice?
LibreOffice's API provides excellent fidelity but requires installing LibreOffice on the server, managing a headless process, and handling subprocess communication. This adds operational complexity, increases Docker image size significantly (~500MB+), and introduces a single point of failure. Not appropriate for MVP.

### Why not Google Slides API?
Requires Google Cloud credentials, API quota management, and network calls for every slide operation. Adds external dependency and latency. Generated files would need export from Google's format. Over-engineered for MVP.

## Known Limitations of python-pptx (Critical for Team)

The following limitations **directly affect how templates must be designed** and what the PPTX engine can produce:

| Limitation | Impact | Workaround |
|------------|--------|------------|
| **SmartArt graphics** | Cannot be programmatically created or modified; read-only in existing slides | Do not use SmartArt in templates; use simple shapes and text boxes instead |
| **Animations and transitions** | Not supported; existing animations in templates are preserved but new ones cannot be added | Templates should not rely on animations for information hierarchy |
| **Complex gradient fills** | Multi-stop gradients and path gradients may be simplified or lost when modifying shapes | Use solid fills or simple two-stop linear gradients in templates |
| **Advanced chart types** | Only basic chart types (bar, line, pie, scatter) are supported; no waterfall, sunburst, treemap | Use basic chart types in templates; complex charts are out of scope for MVP |
| **EMF/WMF images** | Limited support for Windows metafile formats | Use PNG/JPEG for all embedded images |
| **Theme color inheritance** | Modifying theme colors programmatically is fragile; direct RGB is safer | Use explicit RGB colors from the template's JSON metadata palette, not theme color references |
| **Table styling** | Limited control over table borders and cell formatting | Keep tables simple; avoid complex merged cells or custom border patterns |
| **Slide master modification** | Modifying slide masters at runtime is unreliable | Templates must have all needed slide masters/layouts pre-configured |

## Template Design Constraint (Derived from this Decision)

Templates **must** be created with python-pptx limitations in mind. This is a hard constraint for the designer agent:

- Use **solid fills** (not complex gradients) for shape backgrounds
- Use **standard placeholder types** in slide layouts (title, body, picture) — no SmartArt
- Keep **slide masters simple**: background image/color + standard placeholders
- Avoid **animated transitions** between slides
- Use **PNG/JPEG** for any embedded images, not vector formats (EMF/WMF)
- Name slide layouts explicitly (e.g., "title", "content", "two-column", "chart-placeholder") so python-pptx can access them by name via `prs.slide_layouts.get_by_name()`
- Define the color palette in the companion `.json` metadata file — the PPTX engine reads colors from JSON, not from the PPTX theme

## Consequences

### Good
- **Zero cost**: MIT license, no per-seat or annual fees
- **Python-native**: Direct import, no subprocess, no external service calls
- **In-memory generation**: Works with `BytesIO` — no temp files, no disk I/O
- **Mature and stable**: Active since 2013, well-documented, widely used in enterprise Python
- **Simple API**: Creating slides and adding shapes is straightforward; onboarding time is low
- **Template preservation**: Existing slide masters, backgrounds, and layouts are preserved when adding new slides

### Bad
- **Template complexity ceiling**: Cannot reproduce all PowerPoint effects — templates must be designed within python-pptx's capability envelope
- **No SmartArt or animations**: Users who expect SmartArt conversion or animated decks will be disappointed
- **Theme color fragility**: Relying on theme colors for programmatic content is unreliable; we must use explicit RGB values, adding a layer of indirection (JSON palette)
- **Maintenance risk**: python-pptx has slow release cycles; critical bugs may take months to be patched upstream

## Migration Path

If template fidelity requirements exceed python-pptx's capabilities post-MVP:
1. **Short-term**: Upgrade to Aspose.Slides for Python (~$1,000/yr) — same API surface, higher fidelity
2. **Long-term**: Consider a microservice architecture with LibreOffice headless for complex template rendering, keeping python-pptx for simple templates

## Fitness Function

**Test**: Generated PPTX opens in Microsoft PowerPoint (Windows) and Google Slides without warnings or repair prompts. Colors in generated content match the template palette within delta < 5 in each RGB channel. Fonts in generated text match the template's `font_title` and `font_body` specification. Automated test: generate PPTX, extract XML, assert color values and font names match template JSON metadata.
