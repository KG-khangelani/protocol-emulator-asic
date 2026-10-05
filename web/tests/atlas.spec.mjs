// SPDX-License-Identifier: Apache-2.0
import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';

test('architecture is real source-backed UI; search, layers, zoom and source links work', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Chip architecture' })).toBeVisible();
  await expect(page.getByText('5/5 source hashes match E0018')).toBeVisible();
  await page.getByRole('searchbox').fill('synchronizer');
  await expect(page.locator('.outline [aria-pressed]')).toHaveCount(1);
  await page.locator('.outline').getByRole('button', { name: 'Input synchronizer 16 declared state bits', exact: true }).click();
  await expect(page.locator('.inspector').getByRole('heading', { name: 'Input synchronizer', exact: true })).toBeVisible();
  await expect(page.locator('.inspector a').first()).toHaveAttribute('href', /181cfa19.*m1_input_sync.v/);
  await page.getByRole('searchbox').fill('');
  await page.getByRole('checkbox', { name: 'Signal labels' }).uncheck();
  await expect(page.locator('.signal-label')).toHaveCount(0);
  await page.getByRole('checkbox', { name: 'Signal labels' }).check();
  await expect(page.locator('.signal-label')).toHaveCount(7);
  await page.getByRole('button', { name: 'Zoom in', exact: true }).click();
  await expect(page.getByLabel('Zoom', { exact: true })).toHaveText('110%');
  await page.getByRole('button', { name: 'Fit', exact: true }).click();
  await expect(page.getByLabel('Zoom', { exact: true })).toHaveText('100%');
  expect(errors).toEqual([]);
});

test('dwell, keyboard, pin, exit and Escape tracing preserve labels and actual direction', async ({ page }) => {
  await page.goto('/');
  const relation = page.locator('.outline [data-relation="sync-engine"]');
  await relation.hover();
  await expect(page.locator('[data-edge="sync-engine"]')).toHaveClass(/traced/);
  await expect(page.locator('.wire.deemphasized')).toHaveCount(6);
  await expect(page.locator('.trace-summary')).toContainText('Input synchronizer → Sequencer');
  expect(await page.locator('[data-edge="raw-sync"] .signal-label').evaluate((item) => getComputedStyle(item).opacity)).toBe('1');
  await expect.poll(() => page.locator('.wire.deemphasized').first().evaluate((item) => getComputedStyle(item).opacity)).toBe('0.6');
  await page.getByRole('heading', { name: 'Chip architecture' }).hover();
  await expect(page.locator('.traced')).toHaveCount(0);
  await relation.focus();
  await expect(page.locator('.traced')).toHaveCount(1);
  await relation.press('Enter');
  await expect(page.locator('.trace-summary')).toContainText('Pinned relationship');
  await page.locator('.outline [data-relation="engine-data"]').hover();
  await expect(page.locator('[data-edge="sync-engine"]')).toHaveClass(/traced/);
  await relation.press('Escape');
  await expect(page.locator('.traced')).toHaveCount(0);
  await expect(relation).toBeFocused();
  await expect(relation).toHaveAttribute('aria-pressed', 'false');
  await relation.evaluate((item) => item.blur());
  await relation.focus();
  await expect(page.locator('[data-edge="sync-engine"]')).toHaveClass(/traced/);
  await page.getByRole('searchbox').focus();
  await expect(page.locator('.traced')).toHaveCount(0);
});

test('theme follows system, persists choice and keeps neutral surfaces and accessible contrast', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.getByLabel('Theme', { exact: true }).selectOption('light');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  for (const theme of ['light', 'dark']) {
    await page.getByLabel('Theme', { exact: true }).selectOption(theme);
    await page.locator('.outline [data-relation="sync-engine"]').focus();
    const contrast = await page.evaluate(() => {
      const css = getComputedStyle(document.documentElement);
      const rgb = (name) => {
        const hex = css.getPropertyValue(name).trim().slice(1);
        return [0, 2, 4].map((offset) => parseInt(hex.slice(offset, offset + 2), 16));
      };
      const luminance = (channels) => channels.map((n) => n / 255).map((n) => n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4).reduce((sum, value, i) => sum + value * [.2126, .7152, .0722][i], 0);
      const ratio = (a, b) => { const values = [luminance(rgb(a)), luminance(rgb(b))].sort((a, b) => b - a); return (values[0] + .05) / (values[1] + .05); };
      return {
        surfaces: ['--page', '--surface', '--region', '--incident'].map(rgb),
        text: ['--page', '--surface', '--region', '--incident'].flatMap((surface) => ['--ink', '--muted'].map((text) => ratio(text, surface))),
        nonText: ['--page', '--surface', '--region'].flatMap((surface) => ['--focus', '--selection', '--line'].map((line) => ratio(line, surface))),
        focusStyle: getComputedStyle(document.activeElement).outlineStyle,
      };
    });
    expect(contrast.surfaces.every((channels) => channels[0] === channels[1] && channels[1] === channels[2])).toBe(true);
    expect(Math.min(...contrast.text)).toBeGreaterThanOrEqual(4.5);
    expect(Math.min(...contrast.nonText)).toBeGreaterThanOrEqual(3);
    expect(contrast.focusStyle).toBe('solid');
  }
  await page.getByLabel('Theme', { exact: true }).selectOption('system');
  await page.emulateMedia({ colorScheme: 'light' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.emulateMedia({ colorScheme: 'dark' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
});

test('storage unavailable fails safely; reduced motion retains static tracing', async ({ page }) => {
  await page.addInitScript(() => { Storage.prototype.getItem = () => { throw new Error('retained storage-denial fixture'); }; Storage.prototype.setItem = () => { throw new Error('retained storage-denial fixture'); }; });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await page.getByLabel('Theme', { exact: true }).selectOption('dark');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.locator('.outline [data-relation="sync-engine"]').focus();
  await expect(page.locator('[data-edge="sync-engine"]')).toHaveClass(/traced/);
  await expect(page.locator('.travel-cue')).toBeHidden();
  expect(await page.locator('.wire').first().evaluate((item) => getComputedStyle(item).transitionDuration)).toBe('0s');
});

test('view URLs survive refresh and back; copy uses the current stable selection', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/');
  await page.locator('.outline [data-relation="sync-engine"]').click();
  const selected = page.url();
  await page.getByRole('button', { name: 'Copy view link' }).click();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(selected);
  await page.getByRole('button', { name: 'Evidence', exact: true }).click();
  await page.goBack();
  await expect(page.locator('.trace-summary')).toContainText('Pinned relationship');
  await page.reload();
  await expect(page.locator('[data-edge="sync-engine"]')).toHaveClass(/traced/);
  await page.goto('/#view=bogus&module=missing&relation=evil&zoom=NaN');
  await expect(page.getByRole('heading', { name: 'Chip architecture' })).toBeVisible();
  await expect(page.getByLabel('Zoom', { exact: true })).toHaveText('100%');
});

test('reference specimen, disabled edge, reset priority and malformed program remain model-only', async ({ page }) => {
  await page.goto('/#view=cycles');
  await expect(page.getByText('DERIVED · independent model, not RTL or hardware capture')).toBeVisible();
  const step = page.getByRole('button', { name: 'Step clock edge' });
  for (let i = 0; i < 4; i++) await step.click();
  const rows = await page.locator('.cycle-table tbody tr').allTextContents();
  expect(rows.map((row) => row.replaceAll(/\s+/g, ' ').trim())).toEqual([
    'Edge 00RESET MODEL0RUN00000', 'Edge 11ACCEPTED1RUN00101', 'Edge 22ACCEPTED1WAIT10101', 'Edge 33ACCEPTED2RUN00101', 'Edge 44ACCEPTED2HALT00101',
  ]);
  await page.getByRole('button', { name: 'Restart model' }).click();
  await step.click(); await step.click();
  await page.getByRole('checkbox', { name: 'ena', exact: true }).uncheck();
  await step.click();
  await expect(page.locator('.cycle-table tbody tr').last()).toContainText('DISABLED');
  await expect(page.locator('.inspector')).toContainText('WAIT');
  await page.getByRole('checkbox', { name: 'Assert reset' }).check();
  await step.click();
  await expect(page.locator('.inspector')).toContainText('RESET');
  await expect(page.locator('.inspector')).toContainText('0x00');
  await page.getByRole('checkbox', { name: 'ena', exact: true }).check();
  await page.getByRole('checkbox', { name: 'Assert reset' }).uncheck();
  await page.getByLabel('Scenario', { exact: true }).selectOption('invalid');
  await step.click();
  await expect(page.locator('.inspector')).toContainText('FAULT');
});

test('evidence and progress do not promote physical, fluency or deferred branch results', async ({ page }) => {
  await page.goto('/#view=evidence&evidence=E0018');
  await expect(page.getByText('5/5 chip source hashes match E0018')).toBeVisible();
  await expect(page.locator('.evidence-facts')).toContainText('No FIFO/continuous receive');
  await page.locator('.outline').getByRole('button', { name: 'E0010 Archived M0 GPIO baseline' }).click();
  await expect(page.locator('.evidence-facts')).toContainText('Historical GPIO source, not current M1');
  await page.getByRole('button', { name: 'Progress', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'M0 owner fluency: PENDING' })).toBeVisible();
  await expect(page.getByRole('table')).toContainText('PR8 DRAFT / NOT MERGED');
  await expect(page.getByRole('heading', { name: 'Hypotheses remain UNPROVEN' })).toBeVisible();
  await expect(page.getByRole('table')).toContainText('NOT EVALUATED');
});

test('mobile focus/tap alternatives and both themes fit portrait and landscape', async ({ page }) => {
  await mkdir('../build/atlas-qa/screenshots', { recursive: true });
  for (const [name, viewport] of [['portrait', { width: 390, height: 844 }], ['landscape', { width: 740, height: 390 }]]) {
    await page.setViewportSize(viewport);
    await page.goto('/');
    await expect(page.locator('.graph-scroll')).toBeHidden();
    const relation = page.locator('.mobile-module [data-relation="sync-engine"]');
    await relation.click();
    await expect(page.locator('.trace-summary')).toContainText('Pinned relationship');
    expect(await relation.evaluate((item) => item.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);
    for (const theme of ['light', 'dark']) {
      await page.getByLabel('Theme', { exact: true }).selectOption(theme);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.screenshot({ path: `../build/atlas-qa/screenshots/mobile-${name}-${theme}.png`, fullPage: true });
    }
  }
});

test('desktop review captures: soft neutral regions in both themes, cycles and progress', async ({ page }) => {
  await mkdir('../build/atlas-qa/screenshots', { recursive: true });
  await page.goto('/');
  for (const theme of ['light', 'dark']) {
    await page.getByLabel('Theme', { exact: true }).selectOption(theme);
    await page.locator('.outline [data-relation="sync-engine"]').click();
    await page.screenshot({ path: `../build/atlas-qa/screenshots/desktop-architecture-${theme}.png`, fullPage: true });
  }
  await page.getByRole('button', { name: 'Cycles', exact: true }).click();
  for (let i = 0; i < 4; i++) await page.getByRole('button', { name: 'Step clock edge' }).click();
  await page.screenshot({ path: '../build/atlas-qa/screenshots/desktop-cycles-dark.png', fullPage: true });
  await page.getByRole('button', { name: 'Progress', exact: true }).click();
  await page.screenshot({ path: '../build/atlas-qa/screenshots/desktop-progress-dark.png', fullPage: true });
});
