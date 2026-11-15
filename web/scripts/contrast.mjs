// WCAG check of text over the live map: for every text element, compare its colour with the
// 99.5th-percentile brightest backdrop pixel behind it (text hidden). Usage: node scripts/contrast.mjs [url-path]
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import { mkdirSync } from 'node:fs';
const base = 'http://localhost:5173';
const path = process.argv[2] || '/explore?ym=2003-10';
const browser = await chromium.launch({ channel: 'msedge', args: ['--enable-gpu', '--use-angle=d3d11', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(base + path, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(11000);
await page.mouse.move(740, 300);
await page.waitForTimeout(200);
await page.mouse.move(745, 305);
await page.waitForTimeout(1200);
const items = await page.evaluate(() => {
  const out = [];
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walk.nextNode()) {
    const t = walk.currentNode;
    if (!t.textContent.trim()) continue;
    const el = t.parentElement;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || +cs.opacity === 0) continue;
    const range = document.createRange();
    range.selectNodeContents(t);
    const r = range.getBoundingClientRect();
    if (r.width < 2 || r.bottom < 0 || r.top > innerHeight) continue;
    out.push({ text: t.textContent.trim().slice(0, 28), color: cs.color, size: parseFloat(cs.fontSize), weight: +cs.fontWeight, r: [r.x, r.y, r.width, r.height].map(Math.round) });
  }
  return out;
});
await page.addStyleTag({ content: '* { color: transparent !important; text-shadow: none !important; }' });
await page.waitForTimeout(150);
const shot = await page.screenshot();
await browser.close();
const { PNG } = await import('pngjs').catch(() => ({ PNG: null }));
if (!PNG) { console.log('install pngjs'); process.exit(1); }
const img = PNG.sync.read(shot);
const lin = (c) => ((c /= 255) <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const L = (r, g, b) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
let fails = 0;
for (const it of items) {
  const [x, y, w, h] = it.r;
  const lums = [];
  for (let j = Math.max(0, y); j < Math.min(img.height, y + h); j++)
    for (let i = Math.max(0, x); i < Math.min(img.width, x + w); i++) {
      const o = (j * img.width + i) * 4;
      lums.push(L(img.data[o], img.data[o + 1], img.data[o + 2]));
    }
  lums.sort((a, b) => a - b);
  const bg = lums[Math.floor(lums.length * 0.995)] ?? 0;
  const m = it.color.match(/[\d.]+/g).map(Number);
  const lt = L(m[0], m[1], m[2]);
  const c = (Math.max(lt, bg) + 0.05) / (Math.min(lt, bg) + 0.05);
  const large = it.size >= 24 || (it.size >= 18.66 && it.weight >= 700);
  const ok = c >= (large ? 3 : 4.5);
  if (!ok) fails++;
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${c.toFixed(2).padStart(5)}:1  ${String(it.size).padStart(3)}px  ${it.text}`);
}
console.log(fails ? `${fails} below AA` : 'all text passes AA');
