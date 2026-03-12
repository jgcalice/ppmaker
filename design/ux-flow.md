# PPMaker UX Flow

4-step creation flow: Conteudo > Contexto > Storytelling > Apresentacao.

Navigation bar at the top shows all 4 steps with the StepNavigation component. Users can go forward via CTAs and back via the back arrow (with confirmation when data would be lost).

---

## Step 0 — Template Selection (Home)

**URL:** `/`

**Layout:**
- Page title: "PPMaker" (--text-3xl, bold) + subtitle "Transforme texto em apresentacoes profissionais" (--text-lg, --color-text-secondary)
- Template grid: responsive (1 col mobile, 2 tablet, 3 desktop)
- Each template rendered as a TemplateCard component
- Section grouping: "Templates Globais" and "Templates Locais" separated by subtle label (--text-xs, uppercase, --color-text-muted, with divider line)

**Behavior:**
- On page load: show skeleton loading (3 cards min) while templates fetch from `/api/templates`
- On template click: card enters Selected state, user auto-advances to Step 1 after 300ms delay (gives visual confirmation of selection)
- If API returns empty: show TemplateCard Empty state
- If API errors: show error toast + "Nao foi possivel carregar templates. Tente recarregar a pagina."

---

## Step 1 — Conteudo

**URL:** `/create?step=1`

**Layout:**
- Selected template shown as a small pill at top: `[Template Name] x` (click x returns to Step 0)
- Hero textarea: ContentInput component (min-height 300px, full-width of content column, max-width 720px)
- Supporting text below textarea: "Pode ser informal. A IA cuida da estrutura." (--text-sm, --color-text-muted)
- Counters below supporting text: word count + character count (--text-xs, --color-text-muted). Format: "X palavras | X/5000 caracteres"
- CTA at bottom-right: "Proximo ->" button

**Behavior:**
- Textarea is auto-focused on step entry
- Word counter updates on every input (debounced 100ms for performance)
- Character counter: neutral color < 4001, --color-warning 4001-5000, --color-error > 5000
- CTA "Proximo" disabled (opacity 0.5, cursor not-allowed) if textarea is empty or > 5000 characters
- Clicking template pill "x" navigates back to Step 0 (no confirmation needed — no data loss, content persists in state)
- Content persists in client state if user navigates back from Step 2

---

## Step 2 — Contexto

**URL:** `/create?step=2`

**Layout:**
- Back arrow (top-left of content area): navigates to Step 1
- Section title: "Contexto" (--text-2xl, bold)
- Subtitle: "Opcional: quanto mais contexto, melhor o resultado" (--text-sm, --color-text-muted)
- 3 form fields stacked vertically (max-width 720px):

| Field | Type | Placeholder | Help text |
|---|---|---|---|
| Audiencia | text input | "Ex: Diretoria executiva, time de vendas..." | "Quem vai ver esta apresentacao?" |
| Objetivo | text input | "Ex: Aprovar orcamento Q2, motivar equipe..." | "O que a audiencia deve sentir ou fazer apos a apresentacao?" |
| Tom | dropdown select | — | "Estilo da linguagem" |

- Tom dropdown options: Profissional (default), Casual, Executivo
- CTA: "Gerar Storytelling ->" (always enabled — all fields optional)

**Behavior:**
- No field validation (all optional)
- Back arrow to Step 1: no confirmation needed (context fields persist in state)
- Dropdown: custom styled to match dark theme, opens downward, --shadow-dropdown
- Pressing Enter in any field advances to next field; Enter on last field triggers CTA
- Context values persist in client state

---

## Step 3 — Storytelling

**URL:** `/create?step=3`

**Layout (during generation):**
- Back arrow (top-left): shows ConfirmationDialog "Perdera o outline gerado. Confirmar?"
- StorytellingOutline component in Generating state
- ProgressSteps shows the 6 AI steps

**Layout (after generation):**
- Meta header:
  - Presentation title (--text-2xl, bold, --color-text-primary)
  - Objective (--text-sm, --color-text-secondary, prefixed with "Objetivo:")
  - Audience (--text-sm, --color-text-secondary, prefixed with "Audiencia:")
- Toggle button (top-right of slide list): "Editar outline" / "Concluir edicao" (ghost button, --color-accent)
- Slide list: vertical stack of SlideCard components, --space-3 gap
- Placeholder warning (if applicable): amber banner at bottom of slide list. Text: "X slides precisam de dados. Voce pode preenche-los depois no PowerPoint." Icon: alert-triangle. Background: --color-warning at 10% opacity.
- CTA: GenerateButton component (idle state)

**Behavior:**
- On step entry: immediately starts SSE connection to `/api/storytelling`
- SSE events update ProgressSteps in real-time
- On "outline" event: slides animate in (stagger 50ms per card)
- "Editar outline" toggle:
  - ON: all SlideCards enter Edit Mode simultaneously
  - OFF: changes are captured in state, cards return to view mode
- Back arrow always shows confirmation dialog (outline would be lost)
- If confirmed: clears outline state, returns to Step 2
- CTA "Gerar Apresentacao" triggers POST to `/api/generate`
- On click: GenerateButton enters Loading state
- On success: GenerateButton enters Success state, auto-advances to Step 4 after 500ms
- On error: GenerateButton enters Error state, user can click to retry

---

## Step 4 — Apresentacao

**URL:** `/create?step=4`

**Layout:**
- Clean centered layout (max-width 480px, vertically centered in viewport)
- Success icon: large checkmark circle (64px), --color-success, subtle entrance animation (scale 0 to 1, 300ms)
- Title: "Apresentacao pronta!" (--text-2xl, bold)
- Download button: large, full-width. Label: "Baixar Apresentacao.pptx" with download icon. Background: --color-accent. Padding: --space-4 vertical. Border-radius: --radius-md.
- Supporting info (below button): "X slides | Template: [name] | Gerado agora" (--text-sm, --color-text-muted)
- Placeholder reminder (if applicable): subtle card with amber left border. "X slides tem espacos para graficos/dados a preencher" (--text-sm, --color-warning)
- Secondary action: "Criar nova apresentacao" text link (--color-accent, --text-sm). Resets all state and navigates to Step 0.

**Behavior:**
- Download button triggers browser file download (blob URL from API response)
- No back arrow (flow is complete)
- Browser back button: shows Step 3 in read-only (outline still in state, but not re-editable)
- "Criar nova apresentacao" clears all state and returns to home

---

## Cross-cutting Behaviors

### State Persistence
- All form state (content, context, outline) lives in client-side state (React state or URL params)
- Refreshing the page at any step loses state and returns to Step 0 (MVP — no draft saving)
- A warning before unload: `beforeunload` event if user is on Step 2 or 3 with data entered

### Error Recovery
- Network errors during SSE: auto-retry once after 2s. If retry fails, show error state with manual retry button.
- API errors on template load: toast notification + empty state
- API errors on PPTX generation: GenerateButton enters Error state (user retries manually)

### Loading Strategy
- Templates: fetched on mount, cached for session
- Storytelling: streamed via SSE (no polling)
- PPTX generation: single POST, response is binary blob

### Responsive Behavior
- All steps use a single centered column (max-width 720px) except Step 0 (template grid)
- On mobile (< 640px): CTAs become full-width, padding reduces to --space-3
- StepNavigation collapses to numbers only (no labels) on mobile
