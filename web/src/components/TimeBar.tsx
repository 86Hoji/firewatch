import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useStore } from '../store';
import { useSeries } from '../lib/hooks';
import { logNormFloor, rampCSS } from '../lib/scale';
import { ymLong } from '../lib/format';
import { STEP_MS } from '../map/MapStage';

/**
 * The time control. Its track is the data: one column per month, coloured by the country's
 * harmonized total, so the fire seasons are visible in the scrubber itself.
 */
export function TimeBar() {
  const { yms, ymIndex, playing, speed, country, introDone, reducedMotion } = useStore();
  const { setYmIndex, setPlaying, setSpeed } = useStore.getState();
  const series = useSeries(country);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [dragging, setDragging] = useState(false);
  const n = yms.length;

  useLayoutEffect(() => {
    const el = trackRef.current!;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    setWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  // Paint the heat strip.
  useEffect(() => {
    const c = canvasRef.current;
    if (!c || !series || !width || !n) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const h = c.clientHeight;
    c.width = Math.round(width * dpr);
    c.height = Math.round(h * dpr);
    const ctx = c.getContext('2d')!;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, h);
    const top = Math.max(...series.harmonized);
    const colW = width / n;
    for (let i = 0; i < n; i++) {
      const j = series.ym.indexOf(yms[i]);
      const v = j >= 0 ? series.harmonized[j] : 0;
      const t = logNormFloor(v, top);
      ctx.fillStyle = rampCSS(t);
      // Height also follows the value a little, so peaks read even in greyscale.
      const bh = h * (0.16 + 0.84 * t);
      ctx.fillRect(i * colW, h - bh, Math.max(1, colW - (colW > 2.2 ? 0.6 : 0)), bh);
    }
  }, [series, width, n, yms]);

  // Playback.
  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      const s = useStore.getState();
      if (s.ymIndex >= s.yms.length - 1) {
        s.setPlaying(false);
        return;
      }
      s.setYmIndex(s.ymIndex + 1, false);
    }, STEP_MS[speed]);
    return () => clearInterval(id);
  }, [playing, speed]);

  const indexAt = useCallback(
    (clientX: number) => {
      const r = trackRef.current!.getBoundingClientRect();
      return Math.round(((clientX - r.left) / r.width) * n - 0.5);
    },
    [n],
  );

  const onPointerDown = (e: React.PointerEvent) => {
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    setDragging(true);
    setPlaying(false);
    setYmIndex(indexAt(e.clientX));
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (dragging) setYmIndex(indexAt(e.clientX));
  };
  const onKey = (e: React.KeyboardEvent) => {
    const step = e.shiftKey ? 12 : 1;
    if (e.key === 'ArrowRight') setYmIndex(ymIndex + step);
    else if (e.key === 'ArrowLeft') setYmIndex(ymIndex - step);
    else if (e.key === 'Home') setYmIndex(0);
    else if (e.key === 'End') setYmIndex(n - 1);
    else return;
    e.preventDefault();
    setPlaying(false);
  };

  const x = (i: number) => (n ? ((i + 0.5) / n) * width : 0);
  const years = n ? yms.map((ym, i) => [ym, i] as const).filter(([ym]) => ym.endsWith('-01') && Number(ym.slice(0, 4)) % 5 === 0) : [];
  const seam = yms.indexOf('2012-01');
  const glide = playing && !dragging && !reducedMotion;

  return (
    <div
      className="glass pointer-events-auto absolute bottom-[var(--gutter)] left-[var(--gutter)] right-[var(--gutter)] flex items-center gap-4 rounded-[14px] px-4 py-3 md:right-auto md:w-[min(920px,calc(100vw-2*var(--gutter)-300px))] md:gap-5 md:px-5 md:py-4"
      style={{
        opacity: introDone || reducedMotion ? 1 : 0,
        transform: introDone || reducedMotion ? 'none' : 'translateY(8px)',
        transition: 'opacity 600ms var(--ease), transform 600ms var(--ease)',
      }}
    >
      <div className="flex shrink-0 items-center gap-1.5">
        <button
          type="button"
          onClick={() => {
            if (!playing && ymIndex >= n - 1) setYmIndex(0, false);
            setPlaying(!playing);
          }}
          aria-label={playing ? 'Pause' : 'Play through the months'}
          className="grid h-9 w-9 place-items-center rounded-[6px] bg-gold text-night transition-colors duration-[160ms] hover:bg-gold-pale active:bg-ember"
        >
          {playing ? (
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden>
              <rect x="2" y="1.5" width="2.6" height="9" rx="0.6" fill="currentColor" />
              <rect x="7.4" y="1.5" width="2.6" height="9" rx="0.6" fill="currentColor" />
            </svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden>
              <path d="M3 1.6v8.8c0 .45.5.72.88.47l6.6-4.4a.56.56 0 0 0 0-.94L3.88 1.13A.56.56 0 0 0 3 1.6Z" fill="currentColor" />
            </svg>
          )}
        </button>
        <button
          type="button"
          onClick={() => setSpeed(speed === 1 ? 2 : 1)}
          aria-label={`Playback speed ${speed}×, switch to ${speed === 1 ? 2 : 1}×`}
          className="num h-9 w-10 rounded-[6px] text-[15px] text-text-map-2 transition-colors duration-[160ms] hover:bg-white/5 hover:text-text"
        >
          {speed}×
        </button>
      </div>

      <div className="min-w-0 flex-1">
        <div
          ref={trackRef}
          role="slider"
          tabIndex={0}
          aria-label="Month"
          aria-valuemin={0}
          aria-valuemax={Math.max(0, n - 1)}
          aria-valuenow={ymIndex}
          aria-valuetext={yms[ymIndex] ? ymLong(yms[ymIndex]) : ''}
          onKeyDown={onKey}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={() => setDragging(false)}
          onPointerCancel={() => setDragging(false)}
          className="relative h-7 cursor-pointer touch-none select-none rounded-[2px] focus-visible:outline-offset-4"
        >
          <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" aria-hidden />
          {seam >= 0 && (
            <div
              aria-hidden
              className="absolute -bottom-1 -top-1 w-px bg-ice/70"
              style={{ left: (seam / n) * width }}
            />
          )}
          <div
            aria-hidden
            className="pointer-events-none absolute -bottom-1.5 -top-1.5 w-[2px] -translate-x-1/2 rounded-full bg-gold-pale"
            style={{
              left: x(ymIndex),
              boxShadow: '0 0 0 1px rgba(7,11,24,0.6), 0 0 12px rgba(245,184,61,0.8)',
              transition: glide ? `left ${Math.min(600, STEP_MS[speed])}ms linear` : 'none',
            }}
          />
        </div>
        <div className="num relative mt-2 h-4 text-[13px] leading-4 text-text-map-2" aria-hidden>
          {years.map(([ym, i]) => (
            <span key={ym} className="absolute -translate-x-1/2" style={{ left: (i / n) * width }}>
              {ym.slice(0, 4)}
            </span>
          ))}
          {seam >= 0 && width > 420 && (
            <span className="absolute text-ice" style={{ left: (seam / n) * width + 5 }}>
              VIIRS
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
