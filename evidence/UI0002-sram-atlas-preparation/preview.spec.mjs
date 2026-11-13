import { test, expect } from '../../web/node_modules/@playwright/test/index.mjs';
import { readFileSync, mkdirSync } from 'node:fs';
const data = JSON.parse(readFileSync(new URL('./candidate-data.json', import.meta.url)));
test('actual SRAM source is visible without borrowing old qualification', async ({ page, browser }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => { if (['error', 'warning'].includes(message.type())) errors.push(message.text()); });
  await page.route('**/src/data/atlas.json*', (route) => route.fulfill({
    contentType: 'text/javascript', body: `export default ${JSON.stringify(data)};`,
  }));
  await page.goto('/#view=architecture&module=program');
  await expect(page).toHaveTitle('Protocol atlas');
  await expect(page.locator('vite-error-overlay')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Chip architecture' })).toBeVisible();
  await expect(page.locator('.metric')).toContainText('353');
  await expect(page.locator('.region-heading')).toContainText('128 program words, 8192 SRAM bits');
  await expect(page.getByText('Source qualification unavailable')).toBeVisible();
  await expect(page.locator('.inspector')).toContainText('8192 bits');
  await expect(page.locator('[data-module="program"]')).toContainText('128 × 32-bit writable words');
  const rows = await page.locator('[data-module="engine"] .module-field, [data-module="engine"] .module-subtitle').evaluateAll((nodes) =>
    nodes.map((node) => { const b = node.getBBox(); return { y: b.y, h: b.height }; }).sort((a,b) => a.y-b.y));
  for (let i=1; i<rows.length; i++) expect(rows[i].y).toBeGreaterThan(rows[i-1].y + rows[i-1].h);
  await page.locator('.outline [data-relation="engine-program"]').click();
  await expect(page.locator('.inspector')).toContainText('prefetch_pc');
  await page.getByRole('button', { name: 'Clear trace' }).click();
  mkdirSync('H:/CodexArtifacts/g2-sram-atlas', { recursive: true });
  await page.screenshot({ path: 'H:/CodexArtifacts/g2-sram-atlas/candidate-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  for (const detail of await page.locator('details').all()) {
    if (!(await detail.evaluate((node) => node.open))) await detail.locator('summary').click();
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page.locator('.inspector')).toContainText('8192 bits');
  await page.screenshot({ path: 'H:/CodexArtifacts/g2-sram-atlas/candidate-mobile.png', fullPage: true });
  expect(errors).toEqual([]);
  console.log('BROWSER_VERSION', browser.version());
});
