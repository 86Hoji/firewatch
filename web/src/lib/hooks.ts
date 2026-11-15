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
