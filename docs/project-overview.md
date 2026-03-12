# PPMaker — Project Overview

**Transforming raw text into brand-perfect PowerPoint presentations in under 2 minutes.**

---

## The Idea

### Problem

Creating professional presentations is slow, error-prone, and inconsistent. A typical knowledge worker spends 2–4 hours per presentation — structuring the narrative, formatting slides, applying brand colors, sizing text, and searching for the right visual layout. The result is still often inconsistent with brand standards.

### Vision

PPMaker removes that friction entirely. The user describes *what they want to communicate* — in plain text or (future) audio — and the system handles:

1. **Structuring the narrative** (via an AI storytelling engine)
2. **Selecting the right visual layout** per slide (via a visual director)
3. **Rendering a brand-perfect PPTX** (via a stencil-based renderer)

The output is a `.pptx` file you can open immediately in PowerPoint, already formatted with the right fonts, colors, brand photos, and visual hierarchy — ready to present or fine-tune.

### Key Principles

| Principle | Meaning |
|---|---|
| **Content first** | User writes what they know; the AI writes the presentation |
| **Brand fidelity** | Slides are cloned from real branded templates, not programmatically generated from scratch |
| **Transparency** | AI-generated outline is shown and editable before rendering |
| **Placeholder-aware** | Slides that need data the user hasn't provided yet are rendered with placeholder blocks |

---

## The Process

### End-to-End User Journey

```
Step 1: SELECT TEMPLATE
  User opens PPMaker → sees template gallery
  Chooses between "local" (e.g. AB InBev Ambev corporate) or "global" templates
  Each template shows: name, color palette preview, available layouts

Step 2: INPUT CONTENT
  User pastes text (up to 5000 characters) describing what they want to present
  Optionally specifies: audience, objective, tone (professional / casual / executive)

Step 3: AI STORYTELLING (streaming)
  System calls Claude with a 6-phase internal process:
    1. Planner    — defines structure, slide count (5–15), main message
    2. Architect  — builds slide skeleton: title, purpose, layout for each
    3. Story      — shapes narrative arc: hook → problem → insight → solution → conclusion
    4. Director   — selects visual layout per slide; flags placeholders
    5. Generator  — writes concise titles + up to 5 talking points per slide
    6. Editor     — prunes to essentials; ensures 1 idea per slide
  Progress streamed to UI in real time (Server-Sent Events)
  Final outline (JSON) delivered and displayed as editable slide list

Step 4: REVIEW & EDIT OUTLINE
  User sees each slide: layout badge, title, talking points, placeholder warnings
  Can edit any slide directly in the UI before generating
  Clicking "Generate" triggers PPTX rendering

Step 5: PPTX GENERATION (server-side)
  StencilRenderer clones slides from the brand template PPTX
  VisualDirector selects the best matching stencil slide per layout hint
  All text zones filled with AI-generated content (title, bullets, captions, KPIs)
  Brand photos (HERO_RECT zones) preserved in place
  Decorative elements (shapes, accents, gradients) unchanged
  Binary .pptx returned and downloaded by browser
```

### What the User Gets

A `.pptx` file that:
- Opens directly in PowerPoint / Google Slides
- Uses the brand's actual fonts, colors, and accent shapes
- Has real brand photography in content slides (not placeholders)
- Has properly distributed text across all visual zones
- Has chart/data placeholder blocks where the user indicated missing data
- Is structured as a coherent narrative, not just a bullet dump

---

## Technical Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    BROWSER (Next.js)                     │
│  Template Gallery → Content Input → Outline Editor       │
│  → Generate & Download                                   │
└────────────────────┬────────────────────────────────────┘
                     │  HTTP / SSE
┌────────────────────▼────────────────────────────────────┐
│              BACKEND (FastAPI / Python)                   │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ /templates  │  │/storytelling │  │/generate-pptx  │  │
│  │  GET        │  │  POST (SSE)  │  │  POST          │  │
│  └──────┬──────┘  └──────┬───────┘  └────────┬───────┘  │
│         │                │                    │           │
│  template_service    ai_service          pptx_service     │
│  (FS scan)          (Claude API)        (render engine)   │
│                                                           │
│                    ┌────────────────┐                     │
│                    │ visual_director │                     │
│                    │ (layout select)│                     │
│                    └────────────────┘                     │
│                    ┌──────────────────────┐               │
│                    │ render_from_template  │               │
│                    │ (stencil renderer)    │               │
│                    └──────────────────────┘               │
└─────────────────────────────────────────────────────────-┘
                     │ Reads
┌────────────────────▼────────────────────────────────────┐
│               TEMPLATE STORAGE (Filesystem)              │
│  template_padrao/                                        │
│    local/   local-corporate.pptx + .json                 │
│    global/  template-01.pptx + .json                     │
│  tools/     layout_catalog.json + brand_tokens.json      │
└─────────────────────────────────────────────────────────-┘
                     │ Calls
┌────────────────────▼────────────────────────────────────┐
│                  ANTHROPIC API                           │
│                  Claude Sonnet 4.6                       │
└─────────────────────────────────────────────────────────-┘
```

### Stack

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | Next.js 16, React 19, TailwindCSS 4, shadcn/ui | App Router SSR, real-time SSE handling, dark-mode design system |
| Backend | Python FastAPI + uvicorn | Async SSE, python-pptx ecosystem, Anthropic SDK |
| AI | Claude Sonnet 4.6 (`claude-sonnet-4-6`) | Best-in-class structured output, JSON fidelity |
| PPTX rendering | python-pptx 0.6+ | Programmatic PPTX manipulation |
| Streaming | Server-Sent Events (SSE) | One-way progress stream, no WebSocket overhead |
| Template storage | Filesystem (`template_padrao/`) | No DB needed for MVP; templates are static files |
| Deploy | Docker Compose | Single-command local or cloud deploy |

---

## Core Technical Components

### 1. Storytelling Engine (`ai_service.py` + `prompts/storytelling.py`)

The AI is instructed to act as a 6-role presentation consultant:

```
Role 1 — Planner:   defines goal, audience, message, slide count
Role 2 — Architect: structures slides in logical sequence
Role 3 — Story:     applies narrative arc (hook→problem→insight→solution→close)
Role 4 — Director:  assigns layout type per slide; marks placeholder slides
Role 5 — Generator: writes final titles + up to 5 talking points per slide
Role 6 — Editor:    prunes redundancy; ensures 1 idea per slide
```

Output is always a validated JSON `StorytellingOutline` object. Streaming is via SSE — each Claude chunk is forwarded to the browser as `data: {type: "progress", step: "...", message: "..."}` events, with the final JSON delivered as `data: {type: "outline", data: {...}}`.

---

### 2. Template System (`template_service.py`)

Templates are pairs of files:
```
template_padrao/
  local/
    local-corporate.pptx   ← the stencil (brand photos, shapes, layouts)
    local-corporate.json   ← metadata (id, name, palette, layouts, fonts)
  global/
    template-01.pptx
    template-01.json
```

The JSON metadata defines:
```json
{
  "id": "local-corporate",
  "name": "Corporativo Local (AB InBev)",
  "scope": "local",
  "palette": { "primary": "#0766FF", "secondary": "#00328D", "accent": "#FFA41B", ... },
  "layouts": ["title", "content", "two-column", "chart-placeholder", "image-text", "closing"],
  "font_title": "Avantt",
  "font_body": "Avantt"
}
```

---

### 3. Layout Catalog (`tools/inspect_template.py` → `tools/layout_catalog.json`)

Before rendering, the PPTX template is analyzed by `inspect_template.py` to produce `layout_catalog.json` — a structured index of all 47 slides in the stencil, each with:

```json
{
  "layout_id": "SLIDE06",
  "slide_index": 5,
  "use_for": ["content", "two-column"],
  "features": {
    "text_density": 11,
    "hero_images_circle": 0,
    "cards_roundrect": 0,
    "has_chart": false
  },
  "text_zones": [
    { "zone_id": "ZONE_0", "role": "TITLE", "area": 12345, "top": 800000 },
    { "zone_id": "ZONE_1", "role": "CAPTION", "area": 5000, "top": 2000000 },
    ...
  ],
  "image_zones": [
    { "zone_id": "IMG_0", "role": "HERO_RECT", "area": 900000 },
    ...
  ]
}
```

**Zone classification** (two-pass algorithm in `render_from_template.py`):
- **Pass 1**: Shapes with explicit font sizes → classified by size thresholds:
  - ≥ 24pt → `TITLE`
  - ≥ 14pt → `SUBTITLE`
  - 9–14pt → `BODY`
  - < 9pt → `CAPTION`
- **Pass 2**: Shapes with theme-inherited fonts (0pt returned by python-pptx for Ambev template) → classified by position + area:
  - Top-most large shape → `TITLE`
  - Largest remaining shape → `BODY`
  - Small shapes top-half → `LABEL`
  - Small shapes bottom-half → `CAPTION`
- **Image zones**: `HERO_RECT` (large brand photos — beer, people, bottles) vs `DECO` (small decorative shapes, geometric accents)

---

### 4. Visual Director (`visual_director.py`)

Selects the best stencil slide from the catalog for each layout hint from the AI outline.

**Scoring algorithm:**
```
+3   has_chart AND slide has placeholder flag
+2   hero_images_circle > 0 AND hint is "hero" or "title"
+2   cards_roundrect >= 4 AND 4–6 bullets (card layout match)
+1   text_density 2–6 AND 1–5 bullets (good text density match)
-1   text_density > 8 AND few bullets (overkill layout)
+2*N (capped at +8)   HERO_RECT image zones × 2 (brand photos are strongly preferred)
+1 (max +2)           DECO zones / 3 (decorative accents, minor bonus)
-2   text_density > 10 AND no HERO_RECT zones (penalise text-dense slides with no photos)
```

**Candidate pool expansion:**
- `two-column` hint → merges with `content` candidates to avoid over-constraining
- `image-text` / `hero` hints → expands to all slides with ≥ 2 image zones (even if not tagged)

**Optional AI path:** If `ANTHROPIC_API_KEY` is set, the visual director can call Claude to generate a full `SlideSpec` contract (headline, highlight word, takeaway, zone mapping, icon suggestions, quality checks). Without an API key, a deterministic fallback produces the spec.

---

### 5. Stencil Renderer (`render_from_template.py`)

The renderer takes the catalog-selected slide and applies the AI-generated content:

```python
for slide in outline.slides:
    stencil_idx = visual_director.get_stencil_index(selected_layout_id)
    new_slide = clone_slide(template_pptx.slides[stencil_idx], output_pptx)
    zones = classify_zones(new_slide)  # TITLE, BODY, CAPTION, HIGHLIGHT, LABEL

    for zone in zones:
        if zone.role == "TITLE":       → slide.title (truncated to 8 words)
        if zone.role == "BODY":        → "\n".join(slide.talking_points)
        if zone.role == "CAPTION":     → sequential talking points (distributed)
        if zone.role == "HIGHLIGHT":   → extracted numeric KPI (e.g. "+12%")
        if zone.role == "LABEL":       → short sequential talking point snippets
        # Image zones are untouched → brand photos remain in place
```

**`replace_text_preserving_format()`** replaces text while keeping all run-level formatting (bold, size, color, font) from the original stencil — ensuring brand typography is never lost.

**Placeholder handling**: When `slide.has_placeholder = True`, a dashed-border rectangle is inserted with the `placeholder_hint` text (e.g. "Insert: monthly revenue chart Q1–Q4").

---

### 6. Security Layer (`security_service.py`)

All user inputs are validated before any AI or file operation:

| Input | Validation |
|---|---|
| `content` | Max 5000 chars; null byte removal; whitespace bomb prevention |
| `template_id` | Regex `^[a-zA-Z0-9][a-zA-Z0-9\-_]{0,63}$`; whitelist check against known IDs |
| `tone` | Must be one of: `professional`, `casual`, `executive` |
| Template file paths | `safe_template_path()` ensures resolved path stays inside `template_padrao/` |

---

## API Reference

### `GET /api/v1/templates`

Returns all available templates.

**Response:**
```json
{
  "templates": [
    {
      "id": "local-corporate",
      "name": "Corporativo Local (AB InBev)",
      "scope": "local",
      "palette": { "primary": "#0766FF", "secondary": "#00328D", ... },
      "layouts": ["title", "content", "two-column", ...],
      "font_title": "Avantt",
      "font_body": "Avantt"
    }
  ]
}
```

---

### `POST /api/v1/storytelling`

Generates a slide outline from raw content. Response is an SSE stream.

**Request:**
```json
{
  "content": "Quero apresentar os resultados do Q1 2025...",
  "template_id": "local-corporate",
  "audience": "Diretoria executiva",
  "objective": "Informar performance trimestral",
  "tone": "professional"
}
```

**SSE stream:**
```
data: {"type": "progress", "step": "planner",   "message": "Analisando conteúdo..."}
data: {"type": "progress", "step": "architect",  "message": "Estruturando slides..."}
data: {"type": "progress", "step": "story",      "message": "Construindo narrativa..."}
data: {"type": "progress", "step": "director",   "message": "Selecionando layouts..."}
data: {"type": "progress", "step": "generator",  "message": "Gerando conteúdo..."}
data: {"type": "progress", "step": "editor",     "message": "Refinando apresentação..."}
data: {"type": "outline",  "data": { ...StorytellingOutline JSON... }}
data: {"type": "done"}
```

---

### `POST /api/v1/generate-pptx`

Generates and returns a `.pptx` binary file.

**Request:**
```json
{
  "storytelling": {
    "title": "Resultados Q1 2025",
    "objective": "Apresentar resultados",
    "audience": "Liderança",
    "total_slides": 4,
    "slides": [
      { "index": 0, "layout": "title",   "title": "Resultados Q1 2025", "talking_points": ["..."] },
      { "index": 1, "layout": "content", "title": "Destaques", "talking_points": ["Volume +12%", "NPS 78", ...] },
      { "index": 2, "layout": "image-text", "title": "Nossa Marca", "talking_points": ["..."] },
      { "index": 3, "layout": "closing", "title": "Próximos Passos", "talking_points": ["..."] }
    ]
  },
  "template_id": "local-corporate"
}
```

**Response:** Binary `.pptx` file
`Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation`
`Content-Disposition: attachment; filename="presentation.pptx"`

---

## Data Models

```
StorytellingRequest
  content        str (max 5000)
  template_id    str
  audience       str | None
  objective      str | None
  tone           "professional" | "casual" | "executive"

StorytellingOutline
  title          str
  objective      str
  audience       str
  total_slides   int (5–15)
  slides         list[SlideOutline]

SlideOutline
  index          int
  layout         "title" | "content" | "two-column" | "chart-placeholder" | "image-text" | "closing"
  title          str
  talking_points list[str] (max 5)
  has_placeholder bool
  placeholder_hint str

GeneratePptxRequest
  storytelling   StorytellingOutline
  template_id    str
```

---

## File Structure

```
ppmaker/
├── backend/
│   ├── main.py                    FastAPI app (CORS, router mounting)
│   ├── requirements.txt
│   ├── models/schemas.py          Pydantic data models
│   ├── routers/
│   │   ├── templates.py           GET /api/v1/templates
│   │   ├── storytelling.py        POST /api/v1/storytelling (SSE)
│   │   └── pptx.py                POST /api/v1/generate-pptx
│   ├── services/
│   │   ├── template_service.py    Filesystem template scanner
│   │   ├── ai_service.py          Claude API + SSE streaming
│   │   ├── pptx_service.py        Orchestrates rendering pipeline
│   │   ├── render_from_template.py Stencil renderer (zone classification + content placement)
│   │   ├── visual_director.py     Layout selection + SlideSpec generation
│   │   └── security_service.py    Input validation + path traversal protection
│   ├── prompts/storytelling.py    Claude system + user prompts (6 archetypes)
│   └── tests/                     pytest test suite
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx               Template selection
│   │   ├── create/page.tsx        4-step creation flow
│   │   └── templates/page.tsx     Template gallery
│   ├── components/
│   │   ├── TemplateCard.tsx
│   │   ├── ContentInput.tsx
│   │   ├── StorytellingOutline.tsx
│   │   ├── SlideCard.tsx
│   │   ├── GenerateButton.tsx
│   │   └── ProgressSteps.tsx
│   └── lib/
│       ├── api.ts                 API client (fetch + SSE)
│       └── types.ts               TypeScript type definitions
│
├── template_padrao/
│   ├── local/local-corporate.pptx + .json
│   └── global/template-01.pptx + .json
│
├── tools/
│   ├── inspect_template.py        Extracts layout catalog from PPTX stencil
│   ├── layout_catalog.json        47-slide catalog with zone metadata
│   └── brand_tokens.json          Color + typography design tokens
│
├── docs/
│   ├── project-overview.md        ← this file
│   ├── adr/                       Architecture Decision Records
│   ├── template-guide.md          How to create/add templates
│   └── test-strategy.md
│
├── design/
│   ├── design-system.md
│   ├── ux-flow.md
│   └── component-states.md
│
├── security/
│   ├── threat-model.md
│   └── security-checklist.md
│
├── e2e/tests/                     Playwright end-to-end tests
├── docker-compose.yml
└── .env.example
```

---

## Running Locally

```bash
# 1. Clone and configure
cp .env.example .env
echo "ANTHROPIC_API_KEY=your_key_here" >> .env

# 2. Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev        # → http://localhost:3000

# 4. Or with Docker
docker compose up  # → http://localhost:3000
```

**Re-generate layout catalog** (after changing the template PPTX):
```bash
cd tools
python inspect_template.py ../template_padrao/local/local-corporate.pptx > layout_catalog.json
```

---

## Adding a New Template

1. Place `your-template.pptx` and `your-template.json` in `template_padrao/local/` (or `global/`)
2. Fill in `your-template.json`:
   ```json
   {
     "id": "your-template",
     "name": "Your Template Name",
     "scope": "local",
     "palette": { "primary": "#...", "secondary": "#...", "accent": "#...", "background": "#...", "text": "#..." },
     "layouts": ["title", "content", "two-column", "chart-placeholder", "image-text", "closing"],
     "font_title": "YourFont",
     "font_body": "YourFont"
   }
   ```
3. Run `inspect_template.py` to update `layout_catalog.json`
4. Restart the backend

---

## Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Streaming | SSE (not WebSocket) | One-way push; simpler; works over HTTP/1.1; no reconnect complexity |
| PPTX rendering | Stencil (clone slides) over programmatic | Preserves brand formatting, fonts, brand photos, gradients — impossible to replicate programmatically |
| AI model | Claude Sonnet 4.6 | Best structured JSON output; reliable 6-role instruction following |
| Template storage | Filesystem over database | No DB dependency; templates are static files; easy to add without migrations |
| Layout selection | Scoring algorithm + optional LLM | Deterministic scoring works offline; LLM path upgrades visual decisions when API key present |
| Zone classification | Two-pass (explicit font → positional) | Ambev template uses theme-inherited fonts (0pt returned); positional heuristics are reliable fallback |

---

## Known Constraints

| Constraint | Detail |
|---|---|
| Max input | 5000 characters per content submission |
| Slide count | 5–15 slides per presentation |
| Talking points | Max 5 per slide |
| Template fonts | Must be installed on the machine opening the PPTX (brand fonts like "Avantt" may require installation) |
| Placeholder data | Charts/graphs must be inserted manually; system marks where they go |
| Audio input | Not yet implemented (text only in MVP) |
| Collaboration | Single-user generation; no sharing or versioning in MVP |
