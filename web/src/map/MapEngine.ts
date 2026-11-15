// The map, imperatively: MapLibre globe + deck.gl interleaved overlay. React talks to it through a
// handful of methods; per-frame work (tweens, intro) never touches React.
import maplibregl, { type StyleSpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { MapboxOverlay } from '@deck.gl/mapbox';
import { AmbientLight, DirectionalLight, LightingEffect } from '@deck.gl/core';
import { H3HexagonLayer } from '@deck.gl/geo-layers';
import { GlowLayer } from './GlowLayer';
import { HEX_COUNTRIES, type Anomaly, type CountryCode } from '../lib/data';
import { HEX_TOP, logNorm, rampRGB, type Res } from '../lib/scale';
import { easeFlight, easeOut } from '../lib/ease';
import { loadHexYear } from './hexData';

const GIBS_BLACK_MARBLE =
  'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_Black_Marble/default/2016-01-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png';
const TERRARIUM = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png';

/** Column height (m) at the top of the log scale (r7 is drawn flat). */
const MAX_H = 140_000;
/** Glow diameter (m) at the top of the scale. */
const GLOW_SIZE: Record<Res, number> = { r5: 170_000, r7: 46_000 };
const R7_ZOOM = 6;
/** Past this the Black Marble raster (native z8) starts to blur. */
const MAX_ZOOM = 8;

export interface CameraSpec {
  center: [number, number];
  zoom: number;
  pitch: number;
  bearing: number;
}

export interface HoverEvent {
  iso: string;
  name: string;
  country: CountryCode;
  x: number;
  y: number;
}

export interface EngineCallbacks {
  onHover: (h: HoverEvent | null) => void;
  onSelect: (iso: string | null) => void;
  onIntroDone: () => void;
  onEventClick: (ym: string) => void;
  onMove?: (map: maplibregl.Map) => void;
}

/**
 * Screen space taken by page UI on the right (desktop only), so framing centres on what is left.
 * Pages set it on mount; the engine reads it whenever it frames the camera.
 */
export const frame = { right: 0 };

function finalCamera(w: number, h: number): CameraSpec {
  // Kazakhstan + Uzbekistan framed under the dateline and above the time bar.
  if (w < 768) return { center: [67.6, 47.4], zoom: 2.92 + Math.log2(Math.min(w, 430) / 390), pitch: 45, bearing: -12 };
  const usable = w - frame.right;
  const z = 4.3 + Math.log2(Math.min((usable + frame.right * 0.25) / 1440, h / 900));
  const zoom = Math.max(3.4, z);
  // Shift the centre east by half the inset, converted to degrees at this zoom.
  const pxPerDeg = (512 * 2 ** zoom) / 360;
  return { center: [67.4 + frame.right / 2 / pxPerDeg, 45.9], zoom, pitch: 45, bearing: -12 };
}

function buildStyle(): StyleSpecification {
  return {
    version: 8,
    projection: { type: 'globe' },
    sky: {
      'sky-color': '#0D1428',
      'sky-horizon-blend': 0.5,
      'horizon-color': '#14224A',
      'horizon-fog-blend': 0.7,
      'fog-color': '#0A1124',
      'fog-ground-blend': 0.35,
      'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 0.9, 2.5, 0.6, 4, 0.22, 6, 0],
    },
    sources: {
      bm: {
        type: 'raster',
        tiles: [GIBS_BLACK_MARBLE],
        tileSize: 256,
        maxzoom: 8,
        attribution: 'NASA Black Marble (VIIRS), GIBS',
      },
      dem: { type: 'raster-dem', tiles: [TERRARIUM], encoding: 'terrarium', tileSize: 256, maxzoom: 8 },
      borders: { type: 'geojson', data: `${import.meta.env.BASE_URL}geo/borders.json` },
      adm1: { type: 'geojson', data: { type: 'FeatureCollection', features: [] }, promoteId: 'shapeISO' },
    },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': '#0D1428' } },
      {
        id: 'bm',
        type: 'raster',
        source: 'bm',
        // ~35% toward navy: the background shows through, city lights stay faint.
        paint: { 'raster-opacity': 0.62, 'raster-saturation': -0.3, 'raster-contrast': 0.1, 'raster-fade-duration': 400 },
      },
      {
        id: 'relief',
        type: 'hillshade',
        source: 'dem',
        paint: {
          'hillshade-exaggeration': 0.55,
          'hillshade-shadow-color': 'rgba(2,4,12,0.85)',
          'hillshade-highlight-color': 'rgba(160,185,255,0.22)',
          'hillshade-accent-color': 'rgba(4,7,18,0.6)',
          'hillshade-illumination-direction': 315,
        },
      },
      {
        id: 'adm1-dim',
        type: 'fill',
        source: 'adm1',
        paint: { 'fill-color': '#04070F', 'fill-opacity': 0 },
      },
      {
        id: 'adm1-fill',
        type: 'fill',
        source: 'adm1',
        paint: { 'fill-color': '#000', 'fill-opacity': 0 },
      },
      {
        id: 'borders',
        type: 'line',
        source: 'borders',
        paint: { 'line-color': '#F5B83D', 'line-opacity': 0.2, 'line-width': 0.7 },
      },
      {
        id: 'adm1-glow',
        type: 'line',
        source: 'adm1',
        layout: { 'line-join': 'round' },
        paint: {
          'line-color': '#F5B83D',
          'line-width': 7,
          'line-blur': 6,
          'line-opacity': ['case', ['boolean', ['feature-state', 'hover'], false], 0.45, 0],
          'line-opacity-transition': { duration: 160 },
        },
      },
      {
        id: 'adm1-line',
        type: 'line',
        source: 'adm1',
        layout: { 'line-join': 'round' },
        paint: {
          'line-color': ['case', ['boolean', ['feature-state', 'hover'], false], '#FFE7A3', '#F5B83D'],
          'line-width': ['case', ['boolean', ['feature-state', 'hover'], false], 1.3, 0.6],
          'line-opacity': [
            'case',
            ['boolean', ['feature-state', 'hover'], false], 0.95,
            ['boolean', ['feature-state', 'selected'], false], 0.7,
            0.08,
          ],
          'line-opacity-transition': { duration: 160 },
        },
      },
    ],
  };
}

export class MapEngine {
  map: maplibregl.Map;
  private overlay: MapboxOverlay;
  private cb: EngineCallbacks;
  private reduced: boolean;
  private container: HTMLElement;
  private res: Res = 'r5';

  // Display set: the union of cells lit in the previous and the target month.
  private ids: string[] = [];
  private lng = new Float32Array(0);
  private lat = new Float32Array(0);
  private reg = new Int16Array(0);
  private from = new Float32Array(0);
  private to = new Float32Array(0);
  private delay: Float32Array = new Float32Array(0);
  private elev = new Float32Array(0);
  private col = new Uint8ClampedArray(0);
  private glowA = new Float32Array(0);
  private glowS = new Float32Array(0);

  private tweenStart = 0;
  private tweenDur = 0;
  private tweenSpan = 0; // duration + max delay
  private raf = 0;
  private version = 0;
  private hidden = true; // until the intro reveals the hexagons

  private regionIndex = new Map<string, number>();
  private regionBounds = new Map<string, [number, number, number, number]>();
  private regionMeta = new Map<string, { name: string; country: CountryCode }>();
  private selected: string | null = null;
  private hovered: string | null = null;
  private ym: string | null = null;
  private reqToken = 0;
  private lighting: LightingEffect;
  private eventMarker: { el: HTMLElement; lngLat: [number, number] } | null = null;
  private introTimers: number[] = [];
  private destroyed = false;
  private introFinished = false;
  private bornAt = performance.now();
  /** True once the style has parsed (isStyleLoaded() also waits for every tile). */
  private styleReady = false;
  private firstMonth!: Promise<void>;
  private resolveFirst!: (p: Promise<void>) => void;

  constructor(container: HTMLElement, cb: EngineCallbacks, reduced: boolean) {
    this.container = container;
    this.cb = cb;
    this.reduced = reduced;
    this.firstMonth = new Promise<void>((res) => (this.resolveFirst = (p) => p.then(res)));
    const start: CameraSpec = reduced
      ? finalCamera(container.clientWidth, container.clientHeight)
      : { center: [28, 26], zoom: 1.25, pitch: 0, bearing: 0 };

    this.map = new maplibregl.Map({
      container,
      style: buildStyle(),
      ...start,
      maxPitch: 70,
      minZoom: 1,
      maxZoom: MAX_ZOOM,
      attributionControl: false,
      fadeDuration: 200,
      canvasContextAttributes: { antialias: true },
    });
    this.map.dragRotate.enable();
    this.map.touchZoomRotate.enableRotation();

    this.lighting = new LightingEffect({
      ambient: new AmbientLight({ color: [255, 242, 224], intensity: 0.6 }),
      // From the south-west, slightly gold, so columns show a lit and a shaded side.
      sun: new DirectionalLight({ color: [255, 214, 150], intensity: 0.95, direction: [1, 1.2, -0.9] }),
    });
    this.overlay = new MapboxOverlay({ interleaved: true, layers: [], effects: [this.lighting] });
    this.map.addControl(this.overlay as unknown as maplibregl.IControl);

    this.map.once('style.load', () => (this.styleReady = true));
    this.bindEvents();
    this.freezeGlobeErrorMeasurement();
    this.map.on('error', (e) => console.error('map error', e.error?.message ?? e));
    if (import.meta.env.DEV) (window as unknown as { __engine: MapEngine }).__engine = this;
  }

  // ---------- public API ----------

  setRegions(fc: GeoJSON.FeatureCollection) {
    fc.features.forEach((f, i) => {
      const iso = String(f.properties?.shapeISO);
      this.regionIndex.set(iso, i);
      this.regionMeta.set(iso, { name: String(f.properties?.shapeName), country: f.properties?.country });
      let x0 = 180, y0 = 90, x1 = -180, y1 = -90;
      const g = f.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon;
      const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
      for (const p of polys)
        for (const [x, y] of p[0]) {
          x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
        }
      this.regionBounds.set(iso, [x0, y0, x1, y1]);
    });
    const apply = () => (this.map.getSource('adm1') as maplibregl.GeoJSONSource).setData(fc);
    if (this.styleReady) apply();
    else this.map.once('style.load', apply);
  }

  setEvent(a: Anomaly) {
    // MapLibre owns the root element's style (position, occlusion opacity); we style the child.
    const root = document.createElement('div');
    const el = document.createElement('button');
    el.type = 'button';
    el.className = 'event-marker';
    el.setAttribute('aria-label', `Show ${a.title}, ${a.ym}`);
    const ring = document.createElement('span');
    ring.className = 'event-ring';
    const label = document.createElement('span');
    label.className = 'event-label';
    const [y, m] = a.ym.split('-').map(Number);
    const month = new Date(Date.UTC(y, m - 1, 1)).toLocaleString('en-US', { month: 'long', timeZone: 'UTC' });
    label.textContent = `Abai forest fire, ${month} ${y}`;
    el.append(ring, label);
    root.appendChild(el);
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      this.cb.onEventClick(a.ym);
    });
    new maplibregl.Marker({ element: root, opacityWhenCovered: '0' }).setLngLat([a.lon, a.lat]).addTo(this.map);
    this.eventMarker = { el, lngLat: [a.lon, a.lat] };
  }

  /** Shows month `ym`; `duration` 0 = cut. */
  async setMonth(ym: string, duration: number) {
    const token = ++this.reqToken;
    const year = Number(ym.slice(0, 4));
    const m = Number(ym.slice(5, 7)) - 1;
    const res = this.res;
    let years;
    try {
      years = await Promise.all(HEX_COUNTRIES.map((cc) => loadHexYear(cc, res, year)));
    } catch (err) {
      console.warn('hex load failed', err);
      return;
    }
    if (token !== this.reqToken || this.destroyed) return;
    this.ym = ym;
    // Prefetch next year at this resolution.
    HEX_COUNTRIES.forEach((cc) => loadHexYear(cc, res, year + 1).catch(() => {}));

    const cur = this.currentValues();
    const ids: string[] = [];
    const lng: number[] = [];
    const lat: number[] = [];
    const reg: number[] = [];
    const from: number[] = [];
    const to: number[] = [];
    const seen = new Set<string>();
    for (const y of years) {
      for (let i = 0; i < y.ids.length; i++) {
        const v = y.values[i * 12 + m];
        if (!(v > 0)) continue;
        const id = y.ids[i];
        seen.add(id);
        ids.push(id);
        lng.push(y.lng[i]);
        lat.push(y.lat[i]);
        reg.push(this.regionIndex.get(y.region[i]) ?? -1);
        from.push(duration > 0 ? cur.get(id) ?? 0 : v);
        to.push(v);
      }
    }
    if (duration > 0) {
      // Cells lit now but dark next month: shrink them away.
      for (let i = 0; i < this.ids.length; i++) {
        const id = this.ids[i];
        if (seen.has(id)) continue;
        const v = cur.get(id) ?? 0;
        if (v <= 0.01) continue;
        ids.push(id);
        lng.push(this.lng[i]);
        lat.push(this.lat[i]);
        reg.push(this.reg[i]);
        from.push(v);
        to.push(0);
      }
    }
    this.setDisplay(ids, lng, lat, reg, from, to);
    this.startTween(duration, null);
  }

  /** Hexagons rise from zero, staggered by distance from the camera target. */
  rise(totalMs = 900) {
    this.hidden = false;
    for (let i = 0; i < this.from.length; i++) this.from[i] = 0;
    if (this.reduced) {
      this.startTween(0, null);
      return;
    }
    const c = this.map.getCenter();
    const d = new Float32Array(this.ids.length);
    let max = 1e-6;
    const kx = Math.cos((c.lat * Math.PI) / 180);
    for (let i = 0; i < d.length; i++) {
      const dx = (this.lng[i] - c.lng) * kx;
      const dy = this.lat[i] - c.lat;
      d[i] = Math.sqrt(dx * dx + dy * dy);
      if (d[i] > max) max = d[i];
    }
    const spread = totalMs * 0.45;
    for (let i = 0; i < d.length; i++) d[i] = (d[i] / max) * spread;
    this.startTween(totalMs - spread, d);
  }

  setSelected(iso: string | null) {
    if (this.selected && this.selected !== iso) this.map.setFeatureState({ source: 'adm1', id: this.selected }, { selected: false });
    this.selected = iso;
    if (iso) this.map.setFeatureState({ source: 'adm1', id: iso }, { selected: true });
    this.map.setPaintProperty(
      'adm1-dim',
      'fill-opacity',
      iso ? ['case', ['==', ['get', 'shapeISO'], iso], 0, 0.42] : 0,
    );
    this.writeFrame(performance.now());
    if (iso) {
      const b = this.regionBounds.get(iso);
      if (b) {
        const cam = this.map.cameraForBounds(
          [
            [b[0], b[1]],
            [b[2], b[3]],
          ],
          { padding: this.fitPadding(), bearing: this.map.getBearing() },
        );
        if (cam)
          this.map.easeTo({
            ...cam,
            zoom: Math.min(cam.zoom ?? 6, 7.4),
            pitch: 45,
            duration: this.reduced ? 0 : 1000,
            easing: easeOut,
          });
      }
    }
  }

  /** First month to show once the data has arrived; the intro waits for it only at the very end. */
  setFirstMonth(ym: string) {
    this.resolveFirst(this.setMonth(ym, 0));
  }

  /**
   * The intro, started the moment the map exists (not when the data arrives): the globe is on screen
   * by ~0.8 s, turns, flies ~4 s to Central Asia, then the hexagons rise.
   */
  startIntro() {
    const done = () => {
      this.introFinished = true;
      this.cb.onIntroDone();
      this.updateEventPulse();
    };
    if (this.reduced) {
      this.container.style.opacity = '1';
      const go = () => this.firstMonth.then(() => { this.rise(0); done(); });
      if (this.styleReady) go();
      else this.map.once('style.load', go);
      return;
    }
    this.container.style.opacity = '0';
    const t = (ms: number, f: () => void) => this.introTimers.push(window.setTimeout(f, ms));
    const lag = performance.now() - this.bornAt;
    // The navy globe body draws as soon as the style parses; tiles fade in on top of it.
    t(Math.max(0, 450 - lag), () => {
      this.container.style.transition = 'opacity 700ms cubic-bezier(0.22,1,0.36,1)';
      this.container.style.opacity = '1';
      this.map.easeTo({ center: [42, 29], duration: 1500, easing: (x) => x });
    });
    t(Math.max(0, 1800 - lag), () => {
      const final = finalCamera(this.container.clientWidth, this.container.clientHeight);
      this.map.flyTo({ ...final, duration: 4000, curve: 1.25, easing: easeFlight, essential: true });
      this.map.once('moveend', () => {
        this.firstMonth.then(() => {
          this.rise(900);
          t(950, done);
        });
      });
    });
  }

  flyToCountry(cc: CountryCode, bbox: [number, number, number, number]) {
    if (cc === 'KAZ') {
      const final = finalCamera(this.container.clientWidth, this.container.clientHeight);
      this.map.easeTo({ ...final, duration: this.reduced ? 0 : 1000, easing: easeOut });
      return;
    }
    const cam = this.map.cameraForBounds(
      [
        [bbox[0], bbox[1]],
        [bbox[2], bbox[3]],
      ],
      { padding: this.fitPadding(), bearing: -12 },
    );
    if (cam) this.map.easeTo({ ...cam, pitch: 45, duration: this.reduced ? 0 : 1000, easing: easeOut });
  }

  /** Re-frame the home view after the page's UI inset changed (no-op until the intro is done). */
  reframe() {
    if (!this.introFinished) return;
    const final = finalCamera(this.container.clientWidth, this.container.clientHeight);
    this.map.easeTo({ ...final, duration: this.reduced ? 0 : 1000, easing: easeOut });
  }

  destroy() {
    this.destroyed = true;
    this.introTimers.forEach(clearTimeout);
    cancelAnimationFrame(this.raf);
    this.map.remove();
  }

  // ---------- internals ----------

  private fitPadding() {
    const w = this.container.clientWidth;
    return w < 768
      ? { top: 170, bottom: 190, left: 24, right: 24 }
      : { top: 200, bottom: 170, left: 80, right: 80 + frame.right };
  }

  private bindEvents() {
    const map = this.map;
    map.on('mousemove', 'adm1-fill', (e) => {
      const f = e.features?.[0];
      if (!f) return;
      const iso = String(f.properties?.shapeISO);
      if (iso !== this.hovered) this.setHovered(iso);
      const meta = this.regionMeta.get(iso);
      if (meta) this.cb.onHover({ iso, ...meta, x: e.point.x, y: e.point.y });
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'adm1-fill', () => {
      this.setHovered(null);
      this.cb.onHover(null);
      map.getCanvas().style.cursor = '';
    });
    map.on('click', (e) => {
      const f = map.queryRenderedFeatures(e.point, { layers: ['adm1-fill'] })[0];
      const iso = f ? String(f.properties?.shapeISO) : null;
      if (iso && iso === this.selected) {
        this.cb.onSelect(null);
        return;
      }
      this.cb.onSelect(iso);
      if (iso && (e.originalEvent as PointerEvent).pointerType === 'touch') {
        const meta = this.regionMeta.get(iso);
        if (meta) this.cb.onHover({ iso, ...meta, x: e.point.x, y: e.point.y });
        this.setHovered(iso);
      }
    });
    map.on('zoomend', () => {
      const res: Res = map.getZoom() >= R7_ZOOM ? 'r7' : 'r5';
      if (res !== this.res) {
        this.res = res;
        if (this.ym && !this.hidden) this.setMonth(this.ym, 0);
      }
    });
    map.on('moveend', () => this.updateEventPulse());
    let zoomQueued = false;
    map.on('zoom', () => {
      if (zoomQueued || this.hidden || this.raf && this.tweenDur > 0) return;
      zoomQueued = true;
      requestAnimationFrame(() => {
        zoomQueued = false;
        this.writeFrame(performance.now());
      });
    });
    map.on('move', () => this.cb.onMove?.(map));
  }

  /**
   * MapLibre's globe re-measures GPU float precision every ~10 frames with a pixel readback. Under
   * ANGLE/D3D11 that readback stalls the pipeline (60–130 ms hitches while playing). The value is a
   * property of the GPU, so we let it measure once, then keep that value. Private API: fails safe.
   */
  private freezeGlobeErrorMeasurement() {
    type EM = { updateErrorLoop: (a: number, b: number) => number; _measuredError: number; _lastReadbackFrame: number };
    const find = (): EM | null => {
      const p = (this.map as unknown as { style?: { projection?: Record<string, unknown> } }).style?.projection;
      if (!p) return null;
      for (const c of [p, ...Object.values(p)] as Record<string, unknown>[]) {
        const em = c && typeof c === 'object' ? (c as { _errorMeasurement?: EM })._errorMeasurement : undefined;
        if (em && typeof em.updateErrorLoop === 'function') return em;
      }
      return null;
    };
    const onRender = () => {
      try {
        const em = find();
        if (!em || em._lastReadbackFrame < 0) return; // not created or not measured yet
        const value = em._measuredError;
        em.updateErrorLoop = () => value;
      } catch {
        /* keep MapLibre's default behaviour */
      }
      this.map.off('render', onRender);
    };
    this.map.on('render', onRender);
  }

  private setHovered(iso: string | null) {
    if (this.hovered) this.map.setFeatureState({ source: 'adm1', id: this.hovered }, { hover: false });
    this.hovered = iso;
    if (iso) this.map.setFeatureState({ source: 'adm1', id: iso }, { hover: true });
  }

  private updateEventPulse() {
    const ev = this.eventMarker;
    if (!ev) return;
    if (this.hidden) return;
    ev.el.classList.add('is-shown');
    const p = this.map.project(ev.lngLat);
    const c = this.map.getCanvas();
    const inView = p.x > 0 && p.y > 0 && p.x < c.clientWidth && p.y < c.clientHeight;
    ev.el.classList.toggle('is-live', inView && !this.reduced);
    ev.el.classList.toggle('is-flipped', p.x > c.clientWidth - 240);
  }

  private currentValues(): Map<string, number> {
    const out = new Map<string, number>();
    if (this.hidden) return out;
    const now = performance.now();
    for (let i = 0; i < this.ids.length; i++) out.set(this.ids[i], this.valueAt(i, now));
    return out;
  }

  private valueAt(i: number, now: number): number {
    const dur = this.tweenDur;
    if (dur <= 0) return this.to[i];
    const t = (now - this.tweenStart - this.delay[i]) / dur;
    const e = easeOut(Math.max(0, Math.min(1, t)));
    return this.from[i] + (this.to[i] - this.from[i]) * e;
  }

  private setDisplay(ids: string[], lng: number[], lat: number[], reg: number[], from: number[], to: number[]) {
    const n = ids.length;
    this.ids = ids;
    this.lng = Float32Array.from(lng);
    this.lat = Float32Array.from(lat);
    this.reg = Int16Array.from(reg);
    this.from = Float32Array.from(from);
    this.to = Float32Array.from(to);
    this.delay = new Float32Array(n);
    this.elev = new Float32Array(n);
    this.col = new Uint8ClampedArray(n * 4);
    this.glowA = new Float32Array(n);
    this.glowS = new Float32Array(n);
  }

  private startTween(duration: number, delays: Float32Array | null) {
    cancelAnimationFrame(this.raf);
    this.delay = delays ?? new Float32Array(this.ids.length);
    let maxDelay = 0;
    for (let i = 0; i < this.delay.length; i++) maxDelay = Math.max(maxDelay, this.delay[i]);
    this.tweenStart = performance.now();
    this.tweenDur = this.reduced ? 0 : duration;
    this.tweenSpan = this.tweenDur + maxDelay;
    const step = () => {
      const now = performance.now();
      this.writeFrame(now);
      if (now - this.tweenStart < this.tweenSpan) this.raf = requestAnimationFrame(step);
      else this.tweenDur = 0;
    };
    step();
  }

  private writeFrame(now: number) {
    const top = HEX_TOP[this.res];
    const flat = this.res === 'r7';
    // Columns grow slower than the ground when zooming in, so a close view stays readable.
    const z = this.map.getZoom();
    const maxH = MAX_H * Math.min(1.3, Math.max(0.35, Math.pow(2, -(z - 4.3) * 0.5)));
    const sel = this.selected ? this.regionIndex.get(this.selected) ?? -2 : -1;
    const rgb = [0, 0, 0];
    for (let i = 0; i < this.ids.length; i++) {
      const v = this.hidden ? 0 : this.valueAt(i, now);
      const t = logNorm(v, top);
      // Weak cells: low tiles in dark ember. Strong cells: tall, pale gold. Hierarchy first.
      this.elev[i] = flat ? 0 : Math.pow(t, 2.2) * maxH;
      rampRGB(flat ? 0.4 + 0.6 * Math.pow(t, 1.2) : 0.3 + 0.7 * Math.pow(t, 1.8), rgb);
      const a = Math.min(1, v / 0.6) * (flat ? 245 : 235);
      const dim = sel !== -1 && this.reg[i] !== sel ? 0.4 : 1;
      const o = i * 4;
      this.col[o] = rgb[0] * dim;
      this.col[o + 1] = rgb[1] * dim;
      this.col[o + 2] = rgb[2] * dim;
      this.col[o + 3] = a;
      const g = Math.max(0, (t - (flat ? 0.15 : 0.55)) / (flat ? 0.85 : 0.45));
      this.glowA[i] = Math.pow(g, 1.2) * (dim < 1 ? 0.25 : 1);
      this.glowS[i] = (0.6 + 0.4 * t) * GLOW_SIZE[this.res];
    }
    this.version++;
    this.overlay.setProps({ layers: this.layers() });
  }

  private layers() {
    const v = this.version;
    const { elev, col, glowA, glowS, lng, lat } = this;
    return [
      new H3HexagonLayer<string>({
        id: 'hex',
        data: this.ids,
        getHexagon: (d) => d,
        extruded: this.res === 'r5',
        coverage: this.res === 'r5' ? 0.93 : 0.96,
        // True polygons: the instanced shortcut draws the wrong footprint on the globe.
        highPrecision: true,
        elevationScale: 1,
        getElevation: (_: string, { index }) => elev[index],
        getFillColor: (_: string, { index, target }) => {
          const o = index * 4;
          target[0] = col[o];
          target[1] = col[o + 1];
          target[2] = col[o + 2];
          target[3] = col[o + 3];
          return target as [number, number, number, number];
        },
        // Flat r7 cells are unlit so they read as glowing tiles.
        material: this.res === 'r5' ? { ambient: 0.42, diffuse: 0.62, shininess: 24, specularColor: [255, 226, 170] } : false,
        pickable: false,
        updateTriggers: { getElevation: v, getFillColor: v },
      }),
      new GlowLayer<string>({
        id: 'hex-glow',
        data: this.ids,
        radiusUnits: 'meters',
        stroked: false,
        antialiasing: false,
        getPosition: (_: string, { index, target }) => {
          target[0] = lng[index];
          target[1] = lat[index];
          target[2] = elev[index];
          return target as [number, number, number];
        },
        getRadius: (_: string, { index }) => (glowA[index] > 0 ? glowS[index] * 0.5 : 0),
        getFillColor: (_: string, { index }) => [255, 190, 90, Math.round(glowA[index] * (this.res === 'r7' ? 170 : 150))],
        parameters: {
          blend: true,
          blendColorOperation: 'add',
          blendColorSrcFactor: 'src-alpha',
          blendColorDstFactor: 'one',
          blendAlphaOperation: 'add',
          blendAlphaSrcFactor: 'zero',
          blendAlphaDstFactor: 'one',
          depthWriteEnabled: false,
        },
        pickable: false,
        updateTriggers: { getPosition: v, getRadius: v, getFillColor: v },
      }),
    ];
  }
}
