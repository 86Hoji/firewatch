/// <reference lib="webworker" />
// Parses one hex year file off the main thread: centroids, ADM1 region per cell, values as a flat
// Float32Array (12 months per cell, NaN for months after last_ym).
import { cellToLatLng } from 'h3-js';

export interface HexRequest {
  id: number;
  url: string;
  boundariesUrl: string;
}
export interface HexYear {
  id: number;
  ids: string[];
  lng: Float32Array;
  lat: Float32Array;
  /** shapeISO per cell ('' when the centroid falls outside every region). */
  region: string[];
  values: Float32Array;
}

type Ring = number[][];
interface Poly {
  iso: string;
  bbox: [number, number, number, number];
  rings: Ring[][]; // polygons → rings
}

const boundaryCache = new Map<string, Promise<Poly[]>>();

function loadBoundaries(url: string): Promise<Poly[]> {
  let p = boundaryCache.get(url);
  if (!p) {
    p = fetch(url)
      .then((r) => r.json())
      .then((fc: GeoJSON.FeatureCollection) =>
        fc.features.map((f) => {
          const g = f.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon;
          const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
          let x0 = 180, y0 = 90, x1 = -180, y1 = -90;
          for (const poly of polys)
            for (const [x, y] of poly[0]) {
              if (x < x0) x0 = x;
              if (x > x1) x1 = x;
              if (y < y0) y0 = y;
              if (y > y1) y1 = y;
            }
          return { iso: String(f.properties?.shapeISO ?? ''), bbox: [x0, y0, x1, y1], rings: polys } as Poly;
        }),
      );
    boundaryCache.set(url, p);
  }
  return p;
}

function inRing(x: number, y: number, ring: Ring): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function regionOf(x: number, y: number, polys: Poly[]): string {
  for (const p of polys) {
    const b = p.bbox;
    if (x < b[0] || x > b[2] || y < b[1] || y > b[3]) continue;
    for (const poly of p.rings) {
      if (!inRing(x, y, poly[0])) continue;
      let hole = false;
      for (let h = 1; h < poly.length; h++) if (inRing(x, y, poly[h])) hole = true;
      if (!hole) return p.iso;
    }
  }
  return '';
}

self.onmessage = async (e: MessageEvent<HexRequest>) => {
  const { id, url, boundariesUrl } = e.data;
  try {
    const [json, polys] = await Promise.all([
      fetch(url).then((r) => {
        if (!r.ok) throw new Error(`${url}: ${r.status}`);
        return r.json() as Promise<{ months: string[]; cells: Record<string, (number | null)[]> }>;
      }),
      loadBoundaries(boundariesUrl),
    ]);
    const ids = Object.keys(json.cells);
    const n = ids.length;
    const lng = new Float32Array(n);
    const lat = new Float32Array(n);
    const region: string[] = new Array(n);
    const values = new Float32Array(n * 12);
    for (let i = 0; i < n; i++) {
      const [la, lo] = cellToLatLng(ids[i]);
      lat[i] = la;
      lng[i] = lo;
      region[i] = regionOf(lo, la, polys);
      const row = json.cells[ids[i]];
      for (let m = 0; m < 12; m++) {
        const v = row[m];
        values[i * 12 + m] = v == null ? NaN : v;
      }
    }
    const out: HexYear = { id, ids, lng, lat, region, values };
    (self as unknown as Worker).postMessage(out, [lng.buffer, lat.buffer, values.buffer]);
  } catch (err) {
    (self as unknown as Worker).postMessage({ id, error: String(err) });
  }
};
