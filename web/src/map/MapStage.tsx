import { useEffect, useRef } from 'react';
import { MapEngine } from './MapEngine';
import { Starfield } from './Starfield';
import { mapEvents } from './mapEvents';
import { pointer } from './pointer';
import { useStore } from '../store';
import { loadAdm1, loadAnomalies, loadMeta, loadSeries } from '../lib/data';

export let engine: MapEngine | null = null;

/** Step length while playing, by speed. */
export const STEP_MS = { 1: 900, 2: 450 } as const;

function startIndex(yms: string[], harmonized: number[]): number {
  const fromUrl = new URLSearchParams(location.search).get('ym');
  if (fromUrl) {
    const i = yms.indexOf(fromUrl);
    if (i >= 0) return i;
  }
  // The strongest month of the last three complete years: a busy, recent map to land on.
  const lastFull = Number(yms[yms.length - 1].slice(0, 4)) - 1;
  let best = yms.length - 1;
  yms.forEach((ym, i) => {
    const y = Number(ym.slice(0, 4));
    if (y >= lastFull - 2 && y <= lastFull && harmonized[i] > (harmonized[best] ?? -1)) best = i;
  });
  return best;
}

/** The one persistent map. Mounted once at the app root; pages float UI over it. */
export function MapStage() {
  const box = useRef<HTMLDivElement>(null);
  const reduced = useStore((s) => s.reducedMotion);

  useEffect(() => {
    const st = useStore.getState;
    let lastHover: string | null = null;
    const e = new MapEngine(
      box.current!,
      {
        onHover: (h) => {
          if (!h) {
            lastHover = null;
            st().setHover(null);
            return;
          }
          pointer.emit(h.x, h.y);
          if (h.iso !== lastHover) {
            lastHover = h.iso;
            st().setHover({ iso: h.iso, name: h.name, country: h.country });
          }
        },
        onSelect: (iso) => {
          // Clicking a region in the other country moves the panels there too (no camera jump).
          const cc = iso?.startsWith('UZ-') ? 'UZB' : iso?.startsWith('KZ-') ? 'KAZ' : null;
          if (cc && cc !== st().country) st().setCountry(cc);
          st().setSelected(iso);
        },
        onIntroDone: () => st().setIntroDone(),
        onEventClick: (ym) => {
          const i = st().yms.indexOf(ym);
          if (i >= 0) {
            st().setPlaying(false);
            st().setYmIndex(i, true);
          }
        },
        onMove: (map) => {
          const c = map.getCenter();
          mapEvents.emit({ bearing: map.getBearing(), lng: c.lng, zoom: map.getZoom() });
        },
      },
      reduced,
    );
    engine = e;
    e.startIntro();

    let cancelled = false;
    Promise.all([loadMeta(), loadSeries('KAZ'), loadAdm1(), loadAnomalies()]).then(([, kz, adm1, anomalies]) => {
      if (cancelled) return;
      const yms = kz.ym;
      const start = startIndex(yms, kz.harmonized);
      st().setYms(yms, start);
      e.setRegions(adm1);
      const abai = anomalies.find((a) => /abai/i.test(a.title));
      if (abai) e.setEvent(abai);
      e.setFirstMonth(yms[start]);
    });

    const unsubs = [
      useStore.subscribe((s, prev) => {
        if (s.ymIndex !== prev.ymIndex && s.yms.length && s.introDone) {
          const dur = s.reducedMotion ? 0 : s.playing ? Math.min(600, STEP_MS[s.speed]) : 600;
          e.setMonth(s.yms[s.ymIndex], dur);
        }
        if (s.selected !== prev.selected) e.setSelected(s.selected);
      }),
    ];

    return () => {
      cancelled = true;
      unsubs.forEach((u) => u());
      e.destroy();
      engine = null;
    };
  }, [reduced]);

  return (
    <div className="fixed inset-0 overflow-hidden bg-night">
      <Starfield reduced={reduced} />
      <div ref={box} className="absolute inset-0 h-full w-full" style={{ opacity: reduced ? 1 : 0 }} />
      {/* Vignette: soft darkening at the edges so the centre owns the eye. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(120% 90% at 50% 46%, rgba(7,11,24,0) 55%, rgba(7,11,24,0.55) 85%, rgba(7,11,24,0.85) 100%),' +
            // Scrim under the dateline so it passes AA over the atmosphere rim.
            'radial-gradient(640px 320px at 0% 0%, rgba(7,11,24,0.72), rgba(7,11,24,0) 100%)',
        }}
      />
    </div>
  );
}
