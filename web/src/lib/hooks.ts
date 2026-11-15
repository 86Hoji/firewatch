import { useEffect, useRef, useState } from 'react';
import { loadRegions, loadSeries, type CountryCode, type Region, type Series } from './data';
import { easeOut } from './ease';

export function useSeries(cc: CountryCode): Series | null {
  const [s, setS] = useState<Series | null>(null);
  useEffect(() => {
    let live = true;
    loadSeries(cc).then((v) => live && setS(v));
    return () => {
      live = false;
    };
  }, [cc]);
  return s;
}

export function useRegions(cc: CountryCode | null): Region[] | null {
  const [r, setR] = useState<Region[] | null>(null);
  useEffect(() => {
    if (!cc) return;
    let live = true;
    loadRegions(cc).then((v) => live && setR(v));
    return () => {
      live = false;
    };
  }, [cc]);
  return r;
}

/** Counts to `value` over 280 ms when `animate`, otherwise jumps. */
export function useCount(value: number, animate: boolean): number {
  const [shown, setShown] = useState(value);
  const fromRef = useRef(value);
  const shownRef = useRef(value);
  useEffect(() => {
    if (!animate || !Number.isFinite(value) || !Number.isFinite(shownRef.current)) {
      shownRef.current = value;
      setShown(value);
      return;
    }
    fromRef.current = shownRef.current;
    const t0 = performance.now();
    let raf = 0;
    const step = (now: number) => {
      const t = Math.min(1, (now - t0) / 280);
      const v = fromRef.current + (value - fromRef.current) * easeOut(t);
      shownRef.current = v;
      setShown(v);
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value, animate]);
  return shown;
}

export function useMediaQuery(q: string): boolean {
  const [m, setM] = useState(() => window.matchMedia(q).matches);
  useEffect(() => {
    const mq = window.matchMedia(q);
    const f = () => setM(mq.matches);
    mq.addEventListener('change', f);
    return () => mq.removeEventListener('change', f);
  }, [q]);
  return m;
}

/** Live content width of an element. */
export function useWidth<T extends HTMLElement>(): [React.RefObject<T>, number] {
  const ref = useRef<T>(null);
  const [w, setW] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setW(el.clientWidth));
    ro.observe(el);
    setW(el.clientWidth);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

/** Mean of the same calendar month over 2012–2019 (the "normal"), for each month index 0..11. */
export function monthlyNormal(ym: string[], v: number[]): number[] {
  const sum = new Array(12).fill(0);
  const n = new Array(12).fill(0);
  ym.forEach((d, i) => {
    const y = Number(d.slice(0, 4));
    if (y >= 2012 && y <= 2019 && Number.isFinite(v[i])) {
      const m = Number(d.slice(5, 7)) - 1;
      sum[m] += v[i];
      n[m] += 1;
    }
  });
  return sum.map((s, m) => (n[m] ? s / n[m] : 0));
}
