# PPMaker Component States

Every component state is fully specified. No state should require the user to guess what happened. Every action has immediate visual feedback (< 100ms response).

---

## TemplateCard

Displays a template option in the template selection grid.

### States

**Default**
- Background: `--color-bg-secondary` (#141414)
- Border: 1px solid `--color-border` (#2A2A2A)
- Border-radius: `--radius-md` (8px)
- Content: template name (--text-sm, semibold, --color-text-primary), scope badge ("Global" or "Local" pill, --radius-full), color palette swatches (4 small circles showing template accent colors)
- Padding: --space-4 (16px)
- Cursor: pointer
- Transition: `--transition-fast`

**Hover**
- Transform: `scale(1.02)`
- Border-color: `--color-accent` (#6366F1)
- Shadow: `--shadow-card`
- Transition: `--transition-normal` (200ms ease-out)

**Selected**
- Border: 2px solid `--color-accent` (#6366F1)
- Shadow: `--shadow-glow-accent` (indigo glow)
- Checkmark icon overlay: top-right corner, 24px circle with white checkmark on indigo background
- Transform: none (returns to scale 1)

**Loading (skeleton)**
- Minimum 3 skeleton cards displayed
- Background: `--color-bg-secondary`
- Content replaced with shimmer animation bars (one for name, one for badge, one for swatches)
- Shimmer: linear-gradient sweep from left to right, 1.5s infinite
- No cursor change (not interactive during loading)

**Empty (no templates available)**
- Full-width container replacing the grid
- Icon: folder-open (muted, 48px)
- Text: "Nenhum template disponivel" (--text-base, --color-text-secondary)
- Subtext: "Verifique a pasta template_padrao/" (--text-sm, --color-text-muted)
- Centered vertically and horizontally

---

## ContentInput

Large textarea for the user's raw content (Step 1).

### States

**Default**
- Background: `--color-bg-secondary` (#141414)
- Border: 1px solid `--color-border` (#2A2A2A)
- Border-radius: `--radius-sm` (4px)
- Min-height: 300px
- Padding: --space-4 (16px)
- Font: Inter, --text-base
- Color: `--color-text-primary`
- Placeholder: "Cole ou digite seu conteudo aqui..." in `--color-text-muted`
- Resize: vertical only

**Focus**
- Border-color: `--color-border-active` (#6366F1)
- No box-shadow (clean focus, border only)
- Outline: none

**Warning (4001-5000 characters)**
- Border-color: `--color-warning` (#F59E0B)
- Character counter visible below textarea: "X/5000 caracteres" in `--color-warning`
- Counter font: --text-sm
- Transition: border-color `--transition-fast`

**Error (>5000 characters)**
- Border-color: `--color-error` (#EF4444)
- Counter text: "X/5000 caracteres — Limite excedido" in `--color-error`
- Text beyond 5000 chars still editable (soft limit — user can fix)
- CTA "Proximo" button becomes disabled

**Disabled**
- Opacity: 0.5
- Cursor: not-allowed
- Background: `--color-bg-primary` (#0A0A0A)
- No interaction possible

---

## StorytellingOutline (AI Generation Progress)

Shows real-time progress while the backend generates the storytelling outline via SSE.

### States

**Generating (SSE streaming)**
- Each AI step shown as a row in a vertical list
- Steps in order:
  1. Planejador (Planner)
  2. Arquiteto (Architect)
  3. Construtor de Historias (Story Builder)
  4. Diretor Visual (Visual Director)
  5. Gerador (Generator)
  6. Editor (Editor)
- Active step: pulsing indigo dot (CSS animation, 1s ease-in-out infinite), label in --text-sm semibold, --color-text-primary
- Completed steps: green checkmark circle (`--color-success`), label in --text-sm, --color-text-muted
- Pending steps: gray circle (`--color-text-muted`), label in --text-sm, --color-text-muted
- Container background: `--color-bg-secondary`, padding --space-6, border-radius --radius-md

**Outline Received**
- Generation progress fades out (opacity 0, 300ms)
- Meta header appears: presentation title (--text-2xl, bold), objective (--text-sm, secondary), audience (--text-sm, secondary)
- Slide cards animate in with stagger: each card fades in + translateY(8px to 0) with 50ms delay between cards
- Total animation: --transition-slow per card

**Error (generation failed)**
- Progress indicator stops at the failed step
- Failed step: red dot + "Erro no passo X" in --color-error
- Below the list: error message card with --color-bg-tertiary background
- Retry button: "Tentar novamente" with refresh icon, --color-accent
- Keeps any previously completed steps visible (not cleared)

**Empty (no outline yet)**
- Not shown — this component only renders after user clicks "Gerar Storytelling"

---

## SlideCard

Represents one slide in the generated outline (Step 3).

### States

**Default (view mode)**
- Background: `--color-bg-secondary`
- Border: 1px solid `--color-border`
- Border-radius: `--radius-md`
- Padding: --space-4
- Content:
  - Index badge: top-left, small circle (24px) with slide number, --color-bg-tertiary, --text-xs
  - Layout badge: pill (--radius-full) with layout type name, colored by layout type (see below)
  - Title: --text-base, semibold, --color-text-primary
  - Talking points: bulleted list, --text-sm, --color-text-secondary

**Layout badge colors:**
| Layout | Background | Text |
|---|---|---|
| title | `#6366F1` (indigo) | white |
| content | `#3F3F46` (zinc) | `#FAFAFA` |
| two-column | `#7C3AED` (violet) | white |
| chart-placeholder | `#F59E0B` (amber) | `#0A0A0A` |
| image-text | `#0EA5E9` (sky) | white |
| closing | `#22C55E` (emerald) | white |

**Has Placeholder**
- Amber warning badge: top-right, pill with "Placeholder" text in --color-warning
- Dashed border section at bottom of card: 1px dashed --color-warning, padding --space-3
- Hint text inside dashed section: "Este slide precisa de dados (grafico/imagem) a preencher no PowerPoint" in --text-xs, --color-warning

**Edit Mode**
- Triggered when user activates "Editar outline" toggle
- Title becomes a text input: --color-bg-tertiary background, --color-border border, --radius-sm
- Talking points become individual editable text lines: each point is an input field
- Add point: "+" button at bottom of list (--text-sm, --color-accent)
- Remove point: "x" button at right of each point (--text-sm, --color-text-muted, hover --color-error)
- Border-color: `--color-border-active` to indicate editable state

**Loading (skeleton)**
- Same dimensions as default
- Shimmer bars replacing title, badge, and talking points
- 1.5s shimmer animation

---

## GenerateButton

Primary CTA for generating the final .pptx file.

### States

**Idle**
- Label: "Gerar Apresentacao"
- Icon: wand/sparkle icon (left of text)
- Background: `--color-accent` (#6366F1)
- Color: white
- Border-radius: `--radius-md`
- Padding: --space-3 vertical, --space-6 horizontal
- Font: --text-base, semibold
- Cursor: pointer
- Hover: background `--color-accent-hover` (#4F46E5), transition --transition-fast

**Loading**
- Label: "Gerando PPTX..."
- Icon: spinner (CSS rotate animation, 1s linear infinite)
- Background: `--color-accent` at 70% opacity
- Cursor: not-allowed
- Pointer-events: none (prevents double-click)

**Success**
- Label: "Baixar PPTX"
- Icon: checkmark (left), download arrow (right)
- Background: `--color-success` (#22C55E)
- Color: white
- Cursor: pointer
- Hover: brightness(1.1)
- Click triggers file download

**Error**
- Label: "Erro ao gerar — Tentar novamente"
- Icon: alert-triangle
- Background: transparent
- Border: 1px solid `--color-error`
- Color: `--color-error`
- Cursor: pointer
- Hover: background `--color-error` at 10% opacity

---

## ProgressSteps (AI Steps Indicator)

Horizontal or vertical step indicator showing AI pipeline progress.

### States (per step)

**Pending**
- Circle: 12px, border 2px solid `--color-text-muted` (#52525B), no fill
- Label: --text-sm, --color-text-muted
- Connector line (to next step): 1px solid `--color-border`

**Active**
- Circle: 12px, background `--color-accent` (#6366F1), pulsing animation (scale 1 to 1.3, 1s ease-in-out infinite)
- Label: --text-sm, semibold, --color-text-primary
- Connector line to previous: solid `--color-success`
- Connector line to next: dashed `--color-border`

**Completed**
- Circle: 12px, background `--color-success` (#22C55E), white checkmark icon inside
- Label: --text-sm, --color-text-muted
- Connector line: solid `--color-success`

---

## StepNavigation

Top navigation showing the 4-step flow (Conteudo, Contexto, Storytelling, Apresentacao).

### States (per step)

**Not reached**
- Number circle: border only, `--color-border`
- Label: --color-text-muted
- Not clickable

**Current**
- Number circle: filled `--color-accent`, white number
- Label: --color-text-primary, semibold
- Underline indicator: 2px `--color-accent`

**Completed (can go back)**
- Number circle: filled `--color-success`, white checkmark
- Label: --color-text-secondary
- Clickable (shows confirmation dialog if going back would lose data)

---

## ConfirmationDialog

Modal dialog for destructive navigation (e.g., going back from Step 3).

### States

**Open**
- Backdrop: rgba(0,0,0,0.7), z-index --z-modal
- Card: --color-bg-secondary, --radius-lg, --shadow-dropdown, max-width 400px, centered
- Title: --text-lg, semibold, --color-text-primary
- Body: --text-base, --color-text-secondary
- Actions: "Cancelar" (ghost button, --color-text-secondary) + "Confirmar" (filled, --color-error)
- Focus trap: Tab cycles between the two buttons only
- Escape key: closes dialog (same as Cancel)

**Closed**
- Not rendered in DOM (removed, not hidden)

---

## ToastNotification

Ephemeral feedback for non-blocking events.

### Variants

**Success**
- Background: `--color-success` at 15% opacity
- Border-left: 3px solid `--color-success`
- Icon: checkmark circle
- Auto-dismiss: 4 seconds

**Error**
- Background: `--color-error` at 15% opacity
- Border-left: 3px solid `--color-error`
- Icon: alert circle
- Persists until dismissed (click X)

**Warning**
- Background: `--color-warning` at 15% opacity
- Border-left: 3px solid `--color-warning`
- Icon: alert triangle
- Auto-dismiss: 6 seconds

### Position & Animation
- Top-right corner, --space-4 from edges
- Enter: translateX(100%) to translateX(0), --transition-slow
- Exit: opacity 1 to 0, --transition-normal
- Z-index: --z-toast
- Max-width: 360px
