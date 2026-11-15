// Builds public/geo/borders.json: land borders between countries (world-atlas 50m), as one
// MultiLineString, coordinates rounded to 0.01°. Run once: npm run geo
import { readFileSync, writeFileSync } from 'node:fs';
import { mesh } from 'topojson-client';

const topo = JSON.parse(readFileSync('node_modules/world-atlas/countries-50m.json', 'utf8'));
const m = mesh(topo, topo.objects.countries, (a, b) => a !== b);
const r = (x) => Math.round(x * 100) / 100;
m.coordinates = m.coordinates.map((line) => {
  const out = [];
  for (const [x, y] of line) {
    const p = [r(x), r(y)];
    const last = out[out.length - 1];
    if (!last || last[0] !== p[0] || last[1] !== p[1]) out.push(p);
  }
  return out;
}).filter((l) => l.length > 1);
writeFileSync('public/geo/borders.json', JSON.stringify({ type: 'Feature', properties: {}, geometry: m }));
console.log('lines', m.coordinates.length);
