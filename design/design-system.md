# PPMaker Design System

Visual identity for the PPMaker web application UI (not the generated presentations).

---

## Color Tokens

### Backgrounds
| Token | Value | Usage |
|---|---|---|
| `--color-bg-primary` | `#0A0A0A` | Main page background |
| `--color-bg-secondary` | `#141414` | Card/surface backgrounds |
| `--color-bg-tertiary` | `#1F1F1F` | Hover states, input backgrounds |

### Borders
| Token | Value | Usage |
|---|---|---|
| `--color-border` | `#2A2A2A` | Subtle borders (cards, dividers) |
| `--color-border-active` | `#6366F1` | Active/focused element borders |

### Text
| Token | Value | Usage |
|---|---|---|
| `--color-text-primary` | `#FAFAFA` | Headings, primary labels |
| `--color-text-secondary` | `#A1A1AA` | Body copy, descriptions |
| `--color-text-muted` | `#52525B` | Placeholders, hints, captions |

### Accent & Semantic
| Token | Value | Usage |
|---|---|---|
| `--color-accent` | `#6366F1` | Primary actions (buttons, links, active states) — Indigo |
| `--color-accent-hover` | `#4F46E5` | Accent hover state |
| `--color-success` | `#22C55E` | Success states, completed steps |
| `--color-warning` | `#F59E0B` | Placeholder warnings, amber alerts |
| `--color-error` | `#EF4444` | Error states, destructive actions |

---

## Typography

### Font Stack
- **Display / Headings:** Geist (loaded via `next/font/google` or Google Fonts CDN)
- **Body / UI text:** Inter (loaded via `next/font/google` or Google Fonts CDN)
- **Monospace (code snippets, if needed):** Geist Mono

### Type Scale
| Token | Size / Line-height | Usage |
|---|---|---|
| `--text-xs` | 0.75rem / 1rem (12px/16px) | Captions, badges |
| `--text-sm` | 0.875rem / 1.25rem (14px/20px) | Secondary labels, counters |
| `--text-base` | 1rem / 1.5rem (16px/24px) | Body text, inputs |
| `--text-lg` | 1.125rem / 1.75rem (18px/28px) | Subheadings |
| `--text-xl` | 1.25rem / 1.75rem (20px/28px) | Section titles |
| `--text-2xl` | 1.5rem / 2rem (24px/32px) | Page subtitles |
| `--text-3xl` | 1.875rem / 2.25rem (30px/36px) | Page titles |
| `--text-4xl` | 2.25rem / 2.5rem (36px/40px) | Hero text |

### Font Weights
| Weight | Usage |
|---|---|
| 400 (Regular) | Body text, descriptions |
| 500 (Medium) | Labels, active steps |
| 600 (Semibold) | Subheadings, buttons |
| 700 (Bold) | Page headings, hero text |

---

## Spacing Scale

Based on a 4px grid:

| Token | Value |
|---|---|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-6` | 24px |
| `--space-8` | 32px |
| `--space-12` | 48px |
| `--space-16` | 64px |

---

## Border Radius

| Token | Value | Usage |
|---|---|---|
| `--radius-sm` | 4px | Inputs, small elements |
| `--radius-md` | 8px | Cards, buttons |
| `--radius-lg` | 12px | Modals, dialogs |
| `--radius-full` | 999px | Badges, pills, chips |

---

## Shadows

| Token | Value | Usage |
|---|---|---|
| `--shadow-card` | `0 0 0 1px rgba(255,255,255,0.05), 0 4px 16px rgba(0,0,0,0.4)` | Card elevation |
| `--shadow-glow-accent` | `0 0 0 2px #6366F1, 0 0 12px rgba(99,102,241,0.25)` | Selected/active glow (TemplateCard selected, focus rings) |
| `--shadow-dropdown` | `0 4px 24px rgba(0,0,0,0.6)` | Dropdowns, popovers |

---

## Transitions

| Token | Value | Usage |
|---|---|---|
| `--transition-fast` | `150ms ease-out` | Hovers, color changes |
| `--transition-normal` | `200ms ease-out` | Scale transforms, opacity |
| `--transition-slow` | `300ms ease-out` | Layout shifts, slide-in |

---

## Breakpoints

| Name | Value | Behavior |
|---|---|---|
| Mobile | < 640px | Single column, full-width cards |
| Tablet | 640px–1024px | 2-column template grid |
| Desktop | > 1024px | 3-column template grid, max-width 1200px container |

---

## Z-Index Scale

| Token | Value | Usage |
|---|---|---|
| `--z-base` | 0 | Default content |
| `--z-dropdown` | 10 | Dropdowns, popovers |
| `--z-modal` | 50 | Modal dialogs, confirmation dialogs |
| `--z-toast` | 100 | Toast notifications |

---

## CSS Variable Implementation

All tokens should be declared on `:root` in `globals.css` or a dedicated `tokens.css` file. Components reference tokens via `var(--token-name)` — never use raw hex values in component styles.

```css
:root {
  /* Backgrounds */
  --color-bg-primary: #0A0A0A;
  --color-bg-secondary: #141414;
  --color-bg-tertiary: #1F1F1F;

  /* Borders */
  --color-border: #2A2A2A;
  --color-border-active: #6366F1;

  /* Text */
  --color-text-primary: #FAFAFA;
  --color-text-secondary: #A1A1AA;
  --color-text-muted: #52525B;

  /* Accent & Semantic */
  --color-accent: #6366F1;
  --color-accent-hover: #4F46E5;
  --color-success: #22C55E;
  --color-warning: #F59E0B;
  --color-error: #EF4444;

  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;
  --space-16: 64px;

  /* Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 999px;

  /* Shadows */
  --shadow-card: 0 0 0 1px rgba(255,255,255,0.05), 0 4px 16px rgba(0,0,0,0.4);
  --shadow-glow-accent: 0 0 0 2px #6366F1, 0 0 12px rgba(99,102,241,0.25);
  --shadow-dropdown: 0 4px 24px rgba(0,0,0,0.6);

  /* Transitions */
  --transition-fast: 150ms ease-out;
  --transition-normal: 200ms ease-out;
  --transition-slow: 300ms ease-out;
}
```
