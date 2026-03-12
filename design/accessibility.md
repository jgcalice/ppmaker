# PPMaker Accessibility Specs

Target: WCAG 2.1 AA compliance.

---

## Contrast Ratios

All text/background combinations meet WCAG AA minimum (4.5:1 for normal text, 3:1 for large text).

| Foreground | Background | Ratio | Pass |
|---|---|---|---|
| `--color-text-primary` (#FAFAFA) | `--color-bg-primary` (#0A0A0A) | 19.3:1 | AA |
| `--color-text-primary` (#FAFAFA) | `--color-bg-secondary` (#141414) | 15.4:1 | AA |
| `--color-text-secondary` (#A1A1AA) | `--color-bg-primary` (#0A0A0A) | 7.5:1 | AA |
| `--color-text-secondary` (#A1A1AA) | `--color-bg-secondary` (#141414) | 6.0:1 | AA |
| `--color-text-muted` (#52525B) | `--color-bg-primary` (#0A0A0A) | 3.3:1 | AA Large only |
| `--color-text-muted` (#52525B) | `--color-bg-secondary` (#141414) | 2.7:1 | Decorative only |
| White (#FFFFFF) | `--color-accent` (#6366F1) | 4.6:1 | AA |
| White (#FFFFFF) | `--color-success` (#22C55E) | 3.1:1 | AA Large only |
| White (#FFFFFF) | `--color-error` (#EF4444) | 4.0:1 | AA Large only |
| `#0A0A0A` | `--color-warning` (#F59E0B) | 9.1:1 | AA |

### Design Constraints from Contrast
- `--color-text-muted` must only be used for non-essential decorative text (placeholders, hints) or large text (>= 18px / 14px bold). Never for actionable labels.
- Success/error button text uses white on colored backgrounds — buttons are large text (semibold >= 14px), meeting AA Large.
- Warning badge text uses dark text (#0A0A0A) on amber background for strong contrast.

---

## ARIA Labels

### TemplateCard
```
role="radio"
aria-label="Template [name], escopo [global/local]"
aria-checked="true/false"
```
Template grid container: `role="radiogroup"`, `aria-label="Selecione um template"`

### ContentInput
```
aria-label="Conteudo da apresentacao"
aria-describedby="content-help content-counter"
aria-invalid="true" (when > 5000 chars)
```
- `#content-help`: "Pode ser informal. A IA cuida da estrutura."
- `#content-counter`: "X/5000 caracteres" (dynamically updated)

### Context Fields (Step 2)
```
Audiencia: aria-label="Audiencia da apresentacao"
Objetivo: aria-label="Objetivo da apresentacao"
Tom: aria-label="Tom da apresentacao", role="listbox"
```

### StorytellingOutline
```
ProgressSteps container: role="list", aria-label="Progresso da geracao"
Each step: role="listitem", aria-current="step" (active one only)
```
- Live region for updates: `aria-live="polite"` on a visually hidden element that announces "Passo X concluido" as each step completes.

### SlideCard
```
role="article"
aria-label="Slide X: [title]"
```
- Edit mode inputs: `aria-label="Titulo do slide X"`, `aria-label="Ponto X do slide Y"`

### GenerateButton
```
aria-label based on state:
  Idle: "Gerar apresentacao"
  Loading: "Gerando apresentacao, aguarde"
  Success: "Baixar apresentacao gerada"
  Error: "Erro ao gerar. Clique para tentar novamente"
aria-busy="true" (Loading state)
aria-disabled="true" (Loading state)
```

### ConfirmationDialog
```
role="alertdialog"
aria-labelledby="dialog-title"
aria-describedby="dialog-body"
aria-modal="true"
```

### StepNavigation
```
role="navigation"
aria-label="Etapas da criacao"
Each step: aria-current="step" (current), aria-disabled="true" (not reached)
```

### ToastNotification
```
role="alert"
aria-live="assertive" (errors)
aria-live="polite" (success, warning)
```

---

## Focus Order

### Global
Tab order follows visual layout top-to-bottom, left-to-right:
1. StepNavigation steps (completed steps are focusable, unreached are not)
2. Main content area (varies by step)
3. CTA button

### Step 0 — Template Selection
1. Template grid (radio group) — arrow keys navigate between cards
2. Each TemplateCard is focusable within the group

### Step 1 — Conteudo
1. Template pill "x" button (dismiss)
2. ContentInput textarea
3. "Proximo" CTA button

### Step 2 — Contexto
1. Back arrow button
2. Audiencia input
3. Objetivo input
4. Tom dropdown
5. "Gerar Storytelling" CTA button

### Step 3 — Storytelling
1. Back arrow button
2. "Editar outline" toggle button
3. SlideCard list (each card is focusable; in edit mode, inputs within each card are focusable)
4. GenerateButton CTA

### Step 4 — Apresentacao
1. Download button
2. "Criar nova apresentacao" link

### Inside ConfirmationDialog
1. "Cancelar" button (receives focus on open)
2. "Confirmar" button
3. Focus trapped — Tab cycles between these two only
4. Escape closes dialog

---

## Keyboard Navigation

### Global Keys
| Key | Action |
|---|---|
| Tab | Move focus to next focusable element |
| Shift+Tab | Move focus to previous focusable element |
| Enter | Activate focused button/link |
| Escape | Close modal/dialog/dropdown |

### TemplateCard Grid
| Key | Action |
|---|---|
| Arrow Right / Arrow Down | Focus next template |
| Arrow Left / Arrow Up | Focus previous template |
| Enter / Space | Select focused template |
| Home | Focus first template |
| End | Focus last template |

### ContentInput
| Key | Action |
|---|---|
| Tab | Move focus out of textarea to CTA |
| Ctrl+Enter | Submit (same as clicking CTA) |

### Tom Dropdown (Step 2)
| Key | Action |
|---|---|
| Enter / Space | Open dropdown |
| Arrow Down / Arrow Up | Navigate options |
| Enter | Select option and close |
| Escape | Close without selecting |

### SlideCard Edit Mode
| Key | Action |
|---|---|
| Tab | Move between editable fields within card, then to next card |
| Enter (on talking point) | Add new talking point below |
| Backspace (on empty talking point) | Remove point, focus previous |
| Escape | Exit edit mode (same as clicking toggle) |

### ConfirmationDialog
| Key | Action |
|---|---|
| Escape | Close dialog (Cancel) |
| Enter | Activate focused button |
| Tab | Cycle between Cancel and Confirm only |

---

## Screen Reader Announcements

These are announced via `aria-live` regions (visually hidden):

| Event | Announcement |
|---|---|
| Template selected | "Template [name] selecionado" |
| Step changed | "Etapa X de 4: [step name]" |
| Character limit warning | "Atencao: proximo do limite de caracteres" |
| Character limit exceeded | "Limite de caracteres excedido" |
| AI step completed | "Passo [name] concluido" |
| Outline ready | "Outline gerado com X slides" |
| PPTX generating | "Gerando apresentacao" |
| PPTX ready | "Apresentacao pronta para download" |
| Error | "Erro: [message]" |

---

## Reduced Motion

When `prefers-reduced-motion: reduce` is active:
- Disable all shimmer animations (show static placeholder bars)
- Disable pulsing dots (show static filled circles)
- Disable slide card stagger animation (show all cards immediately)
- Disable scale transforms on hover (use border-color change only)
- Keep opacity transitions (these are generally safe)
- ConfirmationDialog: appears instantly (no fade)
- Toast: appears instantly (no slide)
