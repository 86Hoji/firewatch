// Loaders for web/public/data (written by pipeline/08_export_web.py; field meanings in docs/PHASE_D.md).

export type CountryCode = 'KAZ' | 'UZB' | 'TKM' | 'KGZ' | 'TJK' | 'PRT' | 'AUS' | 'BRA' | 'USA' | 'IND';

export interface Meta {
  countries: { code: CountryCode; name: string; bbox: [number, number, number, number]; center: [number, number] }[];
  first_ym: string;
  last_ym: string;
  model: Record<string, unknown>;
}

export interface Series {
  ym: string[];
  naive_points: number[];
  naive_celldays: number[];
  modis_only: number[];
  harmonized: number[];
  lo90: number[];
  hi90: number[];
  viirs: (number | null)[];
}

export interface Region {
  iso: string;
  name: string;
  ym: string[];
  harmonized: number[];
  lo90: number[];
  hi90: number[];
  /** Mean of the same calendar month over 2012–2019, per month index 0..11 (computed here). */
  normal: number[];
}

export interface Anomaly {
  country: CountryCode;
  region: string;
  ym: string;
  value: number;
  anomaly_pct: number;
  lat: number;
  lon: number;
  title: string;
}

/** Countries with hexagon files. */
export const HEX_COUNTRIES: CountryCode[] = ['KAZ', 'UZB'];
/** Countries with ADM1 boundaries and region series. */
export const REGION_COUNTRIES: CountryCode[] = ['KAZ', 'UZB', 'TKM', 'KGZ', 'TJK'];

const base = `${import.meta.env.BASE_URL}data`;
const cache = new Map<string, Promise<unknown>>();

function getJSON<T>(path: string): Promise<T> {
  let p = cache.get(path);
  if (!p) {
    p = fetch(`${base}/${path}`).then((r) => {
      if (!r.ok) throw new Error(`${path}: ${r.status}`);
      return r.json();
    });
    cache.set(path, p);
  }
  return p as Promise<T>;
}

export const loadMeta = () => getJSON<Meta>('meta.json');
export const loadSeries = (cc: CountryCode) => getJSON<Series>(`series/${cc}.json`);
export const loadAnomalies = () => getJSON<Anomaly[]>('anomalies.json');
export const boundariesUrl = (cc: CountryCode) => `${base}/boundaries/${cc}_adm1.geojson`;
export const hexUrl = (cc: CountryCode, res: string, year: number) => `${base}/hex/${cc}/${res}/${year}.json`;

export async function loadRegions(cc: CountryCode): Promise<Region[]> {
  const raw = await getJSON<{ regions: Omit<Region, 'normal'>[] }>(`regions/${cc}.json`);
  return raw.regions.map((r) => {
    const sum = new Array(12).fill(0);
    const n = new Array(12).fill(0);
    r.ym.forEach((ym, i) => {
      const y = Number(ym.slice(0, 4));
      if (y >= 2012 && y <= 2019) {
        const m = Number(ym.slice(5, 7)) - 1;
        sum[m] += r.harmonized[i];
        n[m] += 1;
      }
    });
    return { ...r, normal: sum.map((s, m) => (n[m] ? s / n[m] : 0)) };
  });
}

export async function loadAdm1(): Promise<GeoJSON.FeatureCollection> {
  const all = await Promise.all(
    REGION_COUNTRIES.map((cc) =>
      fetch(boundariesUrl(cc))
        .then((r) => r.json() as Promise<GeoJSON.FeatureCollection>)
        .then((fc) => fc.features.map((f) => ({ ...f, properties: { ...f.properties, country: cc } }))),
    ),
  );
  return { type: 'FeatureCollection', features: all.flat() };
}
