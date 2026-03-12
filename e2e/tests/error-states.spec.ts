import { test, expect } from '@playwright/test';

test.describe('PPMaker Error States', () => {
  test('shows error when content is too long', async ({ page }) => {
    await page.goto('/create?template_id=template-01');

    const longContent = 'A'.repeat(5001);
    await page.fill('[data-testid="content-input"]', longContent);

    // Error message should become visible
    await expect(page.locator('[data-testid="content-error"]')).toBeVisible();
  });

  test('shows loading states during storytelling generation', async ({ page }) => {
    // Mock the storytelling API to be slow
    await page.route('**/api/v1/storytelling', async (route) => {
      // Delay response by 3 seconds to verify loading state appears
      await new Promise((resolve) => setTimeout(resolve, 3000));
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: 'data: {"type": "progress", "step": "planner", "message": "Analisando..."}\n\n',
      });
    });

    await page.goto('/create?template_id=template-01');

    await page.fill(
      '[data-testid="content-input"]',
      'Conteudo de teste para verificar loading states.'
    );
    await page.click('[data-testid="next-step-btn"]');
    await page.click('[data-testid="generate-storytelling-btn"]');

    // Some loading indicator should be visible while waiting
    // This is a soft check — the exact element depends on frontend implementation
    const isLoading =
      (await page.locator('[data-testid="loading-indicator"]').isVisible().catch(() => false)) ||
      (await page.locator('[role="progressbar"]').isVisible().catch(() => false)) ||
      (await page.locator('.animate-spin').isVisible().catch(() => false));

    // We expect some form of loading state
    expect(isLoading).toBeTruthy();
  });

  test('template gallery shows templates', async ({ page }) => {
    await page.goto('/');

    // Wait for templates to load
    await page.waitForSelector('[data-testid="template-card"]');

    // Should have at least one template
    const cards = page.locator('[data-testid="template-card"]');
    await expect(cards).toHaveCount({ minimum: 1 });
  });

  test('content input accepts valid input', async ({ page }) => {
    await page.goto('/create?template_id=template-01');

    const validContent = 'Resultados trimestrais da empresa.';
    await page.fill('[data-testid="content-input"]', validContent);

    // No error should be shown
    await expect(page.locator('[data-testid="content-error"]')).not.toBeVisible();
  });
});
