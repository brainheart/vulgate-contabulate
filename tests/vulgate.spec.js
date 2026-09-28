const { test, expect } = require('@playwright/test');
const instance = require('../docs/instance.json');

async function ready(page, url = '/') {
  await page.goto(url);
  await page.waitForFunction(() => window.__contabulateReady === true);
  await expect(page.locator('#results tbody tr').first()).toBeVisible();
}

function localPath(sampleUrl) {
  const url = new URL(sampleUrl);
  return url.pathname + url.search;
}

test('sample queries load, answer their question, and survive a copied link', async ({ page, context }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  expect(instance.sample_queries).toHaveLength(3);
  const [caritas, regit, miserere] = instance.sample_queries;

  await ready(page, localPath(caritas.url));
  await expect(page.locator('#gran')).toHaveValue('play');
  await expect(page.locator('#matchMode')).toHaveValue('regex');
  await expect(page.locator('th[data-key="t0_count"]')).toHaveClass(/sorted-desc/);
  await expect(page.locator('th[data-key="t1_count"]')).toBeVisible();
  await expect(page.locator('#results tbody tr').first()).toContainText('Joannis I');
  const counts = (await page.locator('td[data-key="t0_count"]').allTextContents()).map(Number);
  expect(counts).toEqual([...counts].sort((a, b) => b - a));
  const copied = await context.newPage();
  await ready(copied, page.url());
  expect((await copied.locator('td[data-key="t0_count"]').allTextContents()).map(Number)).toEqual(counts);
  await copied.close();

  await ready(page, localPath(regit.url));
  await expect(page.locator('#gran')).toHaveValue('line');
  await expect(page.locator('#results tbody tr')).toHaveCount(1);
  await expect(page.locator('#results tbody tr')).toContainText('21.Ps.022.001');
  await expect(page.locator('#results tbody .hit')).toHaveText('Dominus regit me');

  await ready(page, localPath(miserere.url));
  const locations = await page.locator('td[data-key="location"]').allTextContents();
  expect(locations).toEqual(['21.Ps.050.003', '21.Ps.055.002', '21.Ps.056.002']);
  expect(errors).toEqual([]);
});

test('Psalm 22:1 is Dominus regit me under Vulgate numbering', async ({ page }) => {
  await ready(page, '/?gran=line&s_ft_location=' + encodeURIComponent('^21\\.Ps\\.022\\.') + '&sk=location&sd=asc');
  const first = page.locator('#results tbody tr').first();
  await expect(first).toContainText('21.Ps.022.001');
  await expect(first).toContainText('Psalmus David. Dominus regit me, et nihil mihi deerit');
  await expect(page.locator('#segmentsTotalInfo')).toContainText('(6 total rows)');
});

test('Latin regex search finds every inflected form', async ({ page }) => {
  await ready(page, '/');
  await page.selectOption('#gran', 'word');
  await page.selectOption('#matchMode', 'regex');
  await page.fill('#q', '^caritat|^caritas$');
  await page.click('#addColumnBtn');
  const words = await page.locator('td[data-key="ngram"]').allTextContents();
  expect(new Set(words)).toEqual(new Set(['caritas', 'caritatem', 'caritatis', 'caritate', 'caritati']));
  await page.selectOption('#gran', 'play');
  await page.fill('#q', 'c(ae|æ)l(um|i|o)$');
  await page.click('#addColumnBtn');
  await expect(page.locator('#results tbody tr').first()).toBeVisible();
  const hits = await page.locator('td[data-key="t0_count"]').allTextContents();
  expect(hits.map(Number).reduce((a, b) => a + b, 0)).toBeGreaterThan(300);
});

test('prologue rows keep their label and sort before verse 1', async ({ page }) => {
  await ready(page, '/?gran=line&s_ft_location=' + encodeURIComponent('^26\\.Sir\\.001\\.') + '&sk=location&sd=asc');
  const first = page.locator('#results tbody tr').first();
  await expect(first.locator('td[data-key="scene"]')).toHaveText('prol.');
  await expect(first).toContainText('Multorum nobis et magnorum');
  await expect(page.locator('#results tbody tr').nth(1)).toContainText('Omnis sapientia a Domino Deo est');
});

test('desktop and mobile layouts keep the table usable', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await ready(page);
  await expect(page.locator('h1')).toContainText('🦁 Latin Vulgate Tabular Explorer');
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator('#addColumnsMobile')).toBeVisible();
  const bounds = await page.evaluate(() => ({ page: document.documentElement.scrollWidth, viewport: innerWidth,
    table: document.querySelector('#results').scrollWidth, tableWidth: document.querySelector('#results').clientWidth }));
  expect(bounds.page).toBeLessThanOrEqual(bounds.viewport + 1);
  expect(bounds.table).toBeGreaterThan(bounds.tableWidth);
  const mobileButton = await page.locator('#addColumnsMobile').boundingBox();
  const input = await page.locator('#q').boundingBox();
  expect(mobileButton.y).toBeGreaterThan(input.y + input.height);
  expect(mobileButton.height).toBeLessThan(75);
  await page.click('#addColumnsMobile');
  await expect(page.locator('.add-column-popover')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('.add-column-popover')).toBeHidden();
  await page.goto('/sources.html');
  await expect(page.locator('h1')).toHaveText('Edition and sources');
});
