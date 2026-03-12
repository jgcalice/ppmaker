import { test, expect } from '@playwright/test';

test.describe('PPMaker Happy Path', () => {
  test('complete flow: select template → input content → generate outline → download pptx', async ({ page }) => {
    // 1. Go to home / template gallery
    await page.goto('/');

    // 2. Wait for templates to load
    await page.waitForSelector('[data-testid="template-card"]');

    // 3. Click first template
    await page.click('[data-testid="template-card"]:first-child');

    // 4. Should navigate to /create
    await expect(page).toHaveURL(/\/create/);

    // 5. Fill content
    await page.fill(
      '[data-testid="content-input"]',
      'Apresentação sobre resultados do Q1: crescemos 30% em receita e conquistamos 50 novos clientes.'
    );

    // 6. Click next step
    await page.click('[data-testid="next-step-btn"]');

    // 7. Fill audience (optional)
    await page.fill('[data-testid="audience-input"]', 'Diretoria executiva');

    // 8. Generate storytelling
    await page.click('[data-testid="generate-storytelling-btn"]');

    // 9. Wait for outline to appear (up to 60 seconds for AI processing)
    await page.waitForSelector('[data-testid="slide-card"]', { timeout: 60_000 });

    // 10. Verify slides rendered (at least 3)
    const slides = page.locator('[data-testid="slide-card"]');
    await expect(slides).toHaveCount({ minimum: 3 });

    // 11. Generate PPTX and wait for download
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('[data-testid="generate-pptx-btn"]'),
    ]);

    // 12. Verify download filename
    expect(download.suggestedFilename()).toContain('.pptx');
  });
});
