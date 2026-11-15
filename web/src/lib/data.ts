// Loaders for web/public/data (written by pipeline/08_export_web.py; field meanings in docs/PHASE_D.md).

export type CountryCode = 'KAZ' | 'UZB' | 'TKM' | 'KGZ' | 'TJK' | 'PRT' | 'AUS' | 'BRA' | 'USA' | 'IND';

export interface Meta {
  pending_countries?: string[];
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

export const COUNTRY_NAMES: Record<string, string> = {
  KAZ: 'Kazakhstan',
  UZB: 'Uzbekistan',
  TKM: 'Turkmenistan',
  KGZ: 'Kyrgyzstan',
  TJK: 'Tajikistan',
  PRT: 'Portugal',
  AUS: 'Australia',
  BRA: 'Brazil',
  USA: 'United States',
  IND: 'India',
};
export const COUNTRY_SHORT: Record<string, string> = { KAZ: 'KZ', UZB: 'UZ', TKM: 'TM', KGZ: 'KG', TJK: 'TJ' };
/** ADM1 code prefix (KZ-, UZ-…) to country. */
export const ISO_PREFIX: Record<string, CountryCode> = { KZ: 'KAZ', UZ: 'UZB', TM: 'TKM', KG: 'KGZ', TJ: 'TJK' };

/**
 * Central Asian countries the map can show: listed in meta.json, not pending export, and with a
 * series file that actually loads. Anything missing is simply left out.
 */
export async function loadMapCountries(): Promise<CountryCode[]> {
  const meta = await loadMeta();
  const listed = new Set(meta.countries.map((c) => c.code));
  const pending = new Set(meta.pending_countries ?? []);
  const cand = REGION_COUNTRIES.filter((c) => listed.has(c) && !pending.has(c));
  const ok = await Promise.all(
    cand.map((c) =>
      fetch(hexUrl(c, 'r5', Number(meta.first_ym.slice(0, 4))), { method: 'HEAD' })
        .then((r) => r.ok && !(r.headers.get('content-type') ?? '').includes('text/html'))
        .catch(() => false),
    ),
  );
  return cand.filter((_, i) => ok[i]);
}

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
