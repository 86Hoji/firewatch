import { useEffect, useRef } from 'react';
import { mapEvents } from './mapEvents';

/** Sparse stars behind the globe. Drifts slowly and turns with the map's bearing. */
export function Starfield({ reduced }: { reduced: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current!;
    const ctx = canvas.getContext('2d')!;
    let w = 0, h = 0, dpr = 1;
    // Deterministic field so screenshots are stable.
    let seed = 7;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const stars = Array.from({ length: 420 }, () => {
      const r = rnd();
      return {
        x: rnd(),
        y: rnd(),
        s: r > 0.985 ? 1.5 : r > 0.9 ? 1.0 : 0.6,
        a: 0.18 + rnd() * 0.55,
        warm: rnd() > 0.88,
      };
    });
    let bearing = 0, lng = 0;
    const off = mapEvents.subscribe((m) => {
      bearing = m.bearing;
      lng = m.lng;
      if (reduced) draw(0);
    });

    const resize = () => {
      dpr = Math.min(2, window.devicePixelRatio || 1);
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
    };
    const draw = (t: number) => {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const span = Math.max(w, h) * 1.6;
      const drift = reduced ? 0 : t * 0.0000035;
      const ang = (-bearing * Math.PI) / 180;
      const cx = w / 2, cy = h / 2;
      const cos = Math.cos(ang), sin = Math.sin(ang);
      for (const s of stars) {
        const u = (((s.x + drift + lng / 720) % 1) + 1) % 1;
        const x0 = (u - 0.5) * span;
        const y0 = (s.y - 0.5) * span;
        const x = cx + x0 * cos - y0 * sin;
        const y = cy + x0 * sin + y0 * cos;
        if (x < -2 || y < -2 || x > w + 2 || y > h + 2) continue;
        ctx.globalAlpha = s.a;
        ctx.fillStyle = s.warm ? '#FFE7C2' : '#DCE6FF';
        ctx.beginPath();
        ctx.arc(x, y, s.s * 0.5, 0, Math.PI * 2);
        ctx.fill();
      }
    };
    resize();
    let raf = 0;
    const loop = (t: number) => {
      draw(t);
      raf = requestAnimationFrame(loop);
    };
    if (reduced) draw(0);
    else raf = requestAnimationFrame(loop);
    window.addEventListener('resize', resize);
    return () => {
      cancelAnimationFrame(raf);
      off();
      window.removeEventListener('resize', resize);
    };
  }, [reduced]);

  return (
    <canvas
      ref={ref}
      aria-hidden
      className="pointer-events-none absolute inset-0 h-full w-full"
      style={{
        opacity: reduced ? 1 : 0,
        animation: reduced ? undefined : 'stars-in 800ms cubic-bezier(0.22,1,0.36,1) 300ms forwards',
      }}
    />
  );
}
