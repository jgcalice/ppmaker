# Required data-testid Attributes

These `data-testid` attributes are required by the E2E test suite (Playwright). The frontend team must ensure these are present on the corresponding components.

## Template Gallery Page (`/` or `/templates`)

| data-testid | Component | Description |
|---|---|---|
| `template-card` | `TemplateCard` | Each template card in the gallery grid |

## Create Page (`/create`)

| data-testid | Component | Description |
|---|---|---|
| `content-input` | `<textarea>` | Main content textarea where user pastes text |
| `content-error` | Error message `<span>` | Character limit error (shown when > 5000 chars) |
| `next-step-btn` | `<button>` | "Proximo" button to advance to step 2 |
| `audience-input` | `<input>` | Audience field (optional) |
| `generate-storytelling-btn` | `<button>` | "Gerar Storytelling" button to trigger AI outline generation |

## Outline Review / Storytelling Result

| data-testid | Component | Description |
|---|---|---|
| `slide-card` | `SlideCard` | Each slide card in the generated outline |
| `generate-pptx-btn` | `<button>` | "Gerar Apresentacao" button to generate and download PPTX |

## Usage in Tests

These testids are used in:
- `e2e/tests/happy-path.spec.ts` — full flow
- `e2e/tests/error-states.spec.ts` — error and edge case scenarios

## Guidelines

- Always use `data-testid` as the attribute name (not `data-test` or `data-cy`)
- Keep testids stable — changing them breaks E2E tests
- Testids should be on the outermost interactive element (e.g., the clickable card, not an inner div)
