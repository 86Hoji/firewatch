import { forwardRef, useImperativeHandle, useMemo, useRef } from 'react';
import { useSeries } from '../../lib/hooks';
import type { CountryCode, Series } from '../../lib/data';

const W = 380;
const H = 190;
const L = 40;
const R = 8;
const T = 22;
const B = 164;

/**
 * The 2012 step as the ratio of mean yearly cell-days, 2012–2016 against 2007–2011, for the naive
 * splice, MODIS alone (one satellite throughout) and the harmonized record.
 */
export function stepStats(series: Series) {
  const sum = (arr: number[], y0: number, y1: number) => {
    let t = 0;
    series.ym.forEach((ym, i) => {
      const y = Number(ym.slice(0, 4));
      if (y >= y0 && y <= y1) t += arr[i];
    });
    return t;
  };
  const r = (arr: number[]) => sum(arr, 2012, 2016) / sum(arr, 2007, 2011);
  return { naive: r(series.naive_celldays), modis: r(series.modis_only), harmonized: r(series.harmonized) };
}

export interface SceneChartHandle {
  /** 0 = naive splice with its 2012 step, 1 = harmonized record with its 90% range. */
  setMorph(t: number): void;
}

/**
 * One country by year. One line whose shape morphs from the naive splice into the harmonized
 * record; driven imperatively by scroll so React does not re-render every frame.
 */
export const SceneChart = forwardRef<SceneChartHandle, { cc: CountryCode }>(function SceneChart({ cc }, ref) {
  const series = useSeries(cc);
  const line = useRef<SVGPathElement>(null);
  const band = useRef<SVGPathElement>(null);
  const label = useRef<SVGTextElement>(null);

  const geo = useMemo(() => {
    if (!series) return null;
    const acc = new Map<number, { n: number; naive: number; harm: number; lo: number; hi: number }>();
    series.ym.forEach((ym, i) => {
      const y = Number(ym.slice(0, 4));
      const a = acc.get(y) ?? { n: 0, naive: 0, harm: 0, lo: 0, hi: 0 };
      a.n++;
      a.naive += series.naive_celldays[i];
      a.harm += series.harmonized[i];
      a.lo += series.lo90[i];
      a.hi += series.hi90[i];
      acc.set(y, a);
    });
    const ys = [...acc.entries()].filter(([, a]) => a.n === 12).map(([y, a]) => ({ y, ...a }));
    const top = Math.max(...ys.map((d) => Math.max(d.hi, d.naive))) * 1.04;
    const sx = (y: number) => L + ((y - ys[0].y) / (ys[ys.length - 1].y - ys[0].y)) * (W - L - R);
    const sy = (v: number) => B - (v / top) * (B - T);
    const raw = top / 3;
    const mag = 10 ** Math.floor(Math.log10(raw));
    const stepT = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((v) => v >= raw) ?? raw;
    const ticks = Array.from({ length: 6 }, (_, i) => i * stepT).filter((t) => t < top);
    const bandD =
      ys.map((d, i) => `${i ? 'L' : 'M'}${sx(d.y).toFixed(1)},${sy(d.hi).toFixed(1)}`).join('') +
      [...ys].reverse().map((d) => `L${sx(d.y).toFixed(1)},${sy(d.lo).toFixed(1)}`).join('') +
      'Z';
    const path = (t: number) =>
      ys.map((d, i) => `${i ? 'L' : 'M'}${sx(d.y).toFixed(1)},${sy(d.naive + (d.harm - d.naive) * t).toFixed(1)}`).join('');
    return { ys, sx, sy, ticks, bandD, path, step: stepStats(series).naive };
  }, [series]);

  useImperativeHandle(
    ref,
    () => ({
      setMorph(t: number) {
        if (!geo) return;
        const k = Math.max(0, Math.min(1, t));
        line.current?.setAttribute('d', geo.path(k));
        // Muted grey into gold.
        const c = (a: number, b: number) => Math.round(a + (b - a) * k);
        line.current?.setAttribute('stroke', `rgb(${c(154, 245)},${c(168, 184)},${c(199, 61)})`);
        band.current?.setAttribute('opacity', String(Math.max(0, (k - 0.5) * 2)));
        label.current?.setAttribute('opacity', String(1 - Math.min(1, k * 2.5)));
      },
    }),
    [geo],
  );

  if (!geo) return <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" aria-hidden />;
  const x12 = geo.sx(2012);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Fire activity by year: the naive splice steps up in 2012, the harmonized record does not">
      {geo.ticks.map((t) => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={geo.sy(t)} y2={geo.sy(t)} stroke="rgba(148,170,220,0.14)" />
          <text x={L - 6} y={geo.sy(t) + 4} fontSize={12} fill="#B7C2DB" textAnchor="end" className="num">
            {t >= 1000 ? `${t / 1000}k` : t}
          </text>
        </g>
      ))}
      {[2005, 2010, 2015, 2020, 2025].map((y) => (
        <text key={y} x={geo.sx(y)} y={B + 18} fontSize={12} fill="#B7C2DB" textAnchor={geo.sx(y) > W - R - 14 ? 'end' : 'middle'} className="num">
          {y}
        </text>
      ))}
      <line x1={x12} x2={x12} y1={T - 8} y2={B} stroke="#93C5FD" strokeOpacity={0.8} />
      <text x={x12 + 5} y={T - 10} fontSize={12} fill="#93C5FD" dominantBaseline="hanging">
        VIIRS joins
      </text>
      <path ref={band} d={geo.bandD} fill="rgba(245,184,61,0.22)" opacity={0} />
      <path ref={line} d={geo.path(0)} fill="none" stroke="rgb(154,168,199)" strokeWidth={2} strokeLinejoin="round" />
      <text ref={label} x={x12 + 6} y={B - 6} fontSize={13} fill="#EEF2FB" className="num">
        ×{geo.step.toFixed(1)} overnight
      </text>
    </svg>
  );
});
