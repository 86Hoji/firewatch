// Screenshots at 1440×900 and 390×844 for design review.
// Usage: node scripts/shots.mjs [baseUrl] [tag]   (dev server must be running)
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const base = process.argv[2] || 'http://localhost:5173';
const tag = process.argv[3] || 'f1';
const out = new URL(`../shots/${tag}/`, import.meta.url);
mkdirSync(fileURLToPath(out), { recursive: true });

const browser = await chromium.launch({
  // Edge with the real GPU: SwiftShader is too slow for the globe flight.
  channel: 'msedge',
  args: ['--enable-gpu', '--use-angle=d3d11', '--ignore-gpu-blocklist'],
});

async function shoot(name, viewport, path, { wait = 11000, actions, reducedMotion } = {}) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 1, hasTouch: viewport.width < 768, reducedMotion });
  const page = await ctx.newPage();
  const logs = [];
  page.on('console', (m) => (m.type() === 'error' || m.type() === 'warning') && logs.push(`${m.type()}: ${m.text()}`));
  page.on('pageerror', (e) => logs.push(`pageerror: ${e.message}`));
  await page.goto(base + path, { waitUntil: 'domcontentloaded' });
  if (Array.isArray(wait)) {
    for (const [ms, label] of wait) {
      await page.waitForTimeout(ms);
      await page.screenshot({ path: fileURLToPath(new URL(`${name}-${label}.png`, out)) });
    }
  } else {
    await page.waitForTimeout(wait);
  }
  if (actions) await actions(page);
  await page.screenshot({ path: fileURLToPath(new URL(`${name}.png`, out)) });
  if (logs.length) console.log(name, '\n  ' + logs.slice(0, 12).join('\n  '));
  await ctx.close();
}

const desktop = { width: 1440, height: 900 };
const mobile = { width: 390, height: 844 };
const which = process.argv[4] || 'all';

if (which === 'all' || which === 'intro')
  await shoot('desktop-intro', desktop, '/explore', { wait: [[600, 't0.6'], [1400, 't2.0'], [2000, 't4.0'], [2000, 't6.0']] });
if (which === 'all' || which === 'final') {
  await shoot('desktop', desktop, '/explore');
  await shoot('mobile', mobile, '/explore');
}
if (which === 'all' || which === 'hover')
  await shoot('desktop-hover', desktop, '/explore', {
    actions: async (p) => {
      await p.mouse.move(820, 520);
      await p.waitForTimeout(250);
      await p.mouse.move(840, 530);
      await p.waitForTimeout(900);
    },
  });
if (which === 'all' || which === 'select')
  await shoot('desktop-select', desktop, '/explore', {
    actions: async (p) => {
      await p.mouse.click(820, 520);
      await p.waitForTimeout(2500);
    },
  });
if (which === 'all' || which === 'zoom')
  await shoot('desktop-r7', desktop, '/explore?ym=2023-06', {
    actions: async (p) => {
      await p.mouse.move(720, 450);
      for (let i = 0; i < 8; i++) {
        await p.mouse.wheel(0, -300);
        await p.waitForTimeout(150);
      }
      await p.waitForTimeout(4000);
    },
  });

if (which === 'all' || which === 'play')
  await shoot('desktop-play', desktop, '/explore?ym=2002-03', {
    actions: async (p) => {
      await p.getByRole('button', { name: 'Play through the months' }).click();
      const fps = await p.evaluate(
        () =>
          new Promise((res) => {
            let n = 0;
            const t0 = performance.now();
            const f = (t) => {
              n++;
              if (t - t0 < 4000) requestAnimationFrame(f);
              else res(Math.round((n * 1000) / (t - t0)));
            };
            requestAnimationFrame(f);
          }),
      );
      console.log('fps while playing:', fps);
    },
  });
if (which === 'all' || which === 'reduced') await shoot('desktop-reduced-1s', desktop, '/explore', { wait: 2500, reducedMotion: 'reduce' });
if (which === 'all' || which === 'modelled') await shoot('desktop-2003', desktop, '/explore?ym=2003-10');

if (which === 'all' || which === 'f2') {
  await shoot('desktop-chart-hover', desktop, '/explore', {
    actions: async (p) => {
      const box = await p.locator('[aria-label^="Naive and harmonized"]').boundingBox();
      if (box) {
        await p.mouse.move(box.x + box.width * 0.3, box.y + box.height * 0.5);
        await p.waitForTimeout(150);
        await p.mouse.move(box.x + box.width * 0.32, box.y + box.height * 0.5);
        await p.waitForTimeout(400);
      }
    },
  });
  await shoot('desktop-uz', desktop, '/explore', {
    actions: async (p) => {
      await p.getByRole('radio', { name: /UZ/ }).click();
      await p.waitForTimeout(2200);
    },
  });
  await shoot('mobile-sheet', mobile, '/explore', {
    actions: async (p) => {
      await p.locator('section[aria-label="Details"] > button').click();
      await p.waitForTimeout(900);
    },
  });
}
if (which === 'landing') {
  await shoot('landing-desktop', desktop, '/');
  await shoot('landing-mobile', mobile, '/');
}
if (which === 'verify') {
  await shoot('landing-desktop', desktop, '/', { wait: [[3500, 't3.5'], [3000, 't6.5'], [5000, 't11']] });
  await shoot('landing-how', desktop, '/', { actions: async (p) => { await p.getByRole('button', { name: 'How it works' }).click(); await p.waitForTimeout(1200); } });
  await shoot('explore-desktop', desktop, '/explore');
  await shoot('validation-desktop', desktop, '/validation', { wait: 3000 });
}
if (which === 'five') {
  await shoot('explore-desktop', desktop, '/explore');
  await shoot('explore-mobile', mobile, '/explore');
  for (const cc of ['TM', 'KG', 'TJ']) {
    await shoot(`explore-${cc}`, desktop, '/explore', {
      actions: async (p) => {
        await p.getByRole('radio', { name: { TM: 'Turkmenistan', KG: 'Kyrgyzstan', TJ: 'Tajikistan' }[cc] }).click();
        await p.waitForTimeout(2200);
      },
    });
  }
}
if (which === 'validation') await shoot('validation-desktop', desktop, '/validation', { wait: 3000 });
await browser.close();
console.log('saved to', fileURLToPath(out));
