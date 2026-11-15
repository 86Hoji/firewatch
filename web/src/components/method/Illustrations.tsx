// Small live illustrations for the Method page. Each runs only while on screen and shows its
// final state under reduced motion.
import { useEffect, useMemo, useRef, useState } from 'react';
import { useStore } from '../../store';
import { useSeries } from '../../lib/hooks';

const GOLD = '#F5B83D';
const GOLD_PALE = '#FFE7A3';
const ICE = '#93C5FD';
const TEXT2 = '#9AA8C7';
const TEXT3 = '#5F6E91';
const LINE = 'rgba(148,170,220,0.14)';

export function useInView<T extends Element>(): [React.RefObject<T>, boolean] {
  const ref = useRef<T>(null);
  const [v, setV] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => setV(e.isIntersecting), { threshold: 0.35 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return [ref, v];
}

/** Alternates a boolean every `ms` while visible; always true under reduced motion. */
function usePhase(visible: boolean, ms: number): boolean {
  const reduced = useStore((s) => s.reducedMotion);
  const [on, setOn] = useState(false);
  useEffect(() => {
    if (reduced) return;
    if (!visible) {
      setOn(false);
      return;
    }
    const t0 = setTimeout(() => setOn(true), 500);
    const id = setInterval(() => setOn((o) => !o), ms);
    return () => {
      clearTimeout(t0);
      clearInterval(id);
    };
  }, [visible, ms, reduced]);
  return reduced || on;
}

// ---------- points and hexagons (steps 1 and 2) ----------

function rng(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function gauss(r: () => number) {
  return Math.sqrt(-2 * Math.log(r() + 1e-9)) * Math.cos(2 * Math.PI * r());
}

const FIRES = [
  { x: 52, y: 70, s: 13 },
  { x: 118, y: 128, s: 15 },
  { x: 62, y: 158, s: 9 },
];
const PANEL_W = 170;
const PANEL_H = 200;
const HEX = 15; // hexagon radius in px

function makePoints(seed: number, perFire: number, spread: number) {
  const r = rng(seed);
  return FIRES.flatMap((f) =>
    Array.from({ length: Math.round(perFire * (f.s / 13)) }, () => ({
      x: Math.min(PANEL_W - 6, Math.max(6, f.x + gauss(r) * spread * (f.s / 13))),
      y: Math.min(PANEL_H - 6, Math.max(6, f.y + gauss(r) * spread * (f.s / 13))),
    })),
  );
}

/** Pointy-top axial hex containing (x, y), and its centre. */
function hexOf(x: number, y: number) {
  const q = ((Math.sqrt(3) / 3) * x - y / 3) / HEX;
  const r = ((2 / 3) * y) / HEX;
  let rx = Math.round(q);
  let rz = Math.round(r);
  const ry = Math.round(-q - r);
  const dx = Math.abs(rx - q);
  const dy = Math.abs(ry - (-q - r));
  const dz = Math.abs(rz - r);
  if (dx > dy && dx > dz) rx = -ry - rz;
  else if (!(dy > dz)) rz = -rx - ry;
  return { key: `${rx},${rz}`, cx: HEX * Math.sqrt(3) * (rx + rz / 2), cy: HEX * 1.5 * rz };
}
function hexPath(cx: number, cy: number, r = HEX) {
  return (
    Array.from({ length: 6 }, (_, i) => {
      const a = (Math.PI / 180) * (60 * i - 30);
      return `${i ? 'L' : 'M'}${(cx + r * Math.cos(a)).toFixed(1)},${(cy + r * Math.sin(a)).toFixed(1)}`;
    }).join('') + 'Z'
  );
}

const SENSORS = [
  { name: 'MODIS', note: '1 km pixels', color: GOLD, r: 4, pts: makePoints(7, 6, 15) },
  { name: 'VIIRS', note: '375 m pixels', color: ICE, r: 2.2, pts: makePoints(11, 22, 13) },
];

/** The same three fires as seen by each satellite. With `snap`, points move into ~5 km² hexagons. */
export function PointsToHexes({ snap }: { snap: boolean }) {
  const [ref, visible] = useInView<SVGSVGElement>();
  const phase = usePhase(visible, 2600);
  // Step 1 reveals its points once; step 2 loops between scattered and snapped.
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    if (visible) setSeen(true);
  }, [visible]);
  const reduced = useStore((s) => s.reducedMotion);
  const snapped = snap && phase;
  const shown = snap || seen || reduced;

  const sensors = useMemo(
    () =>
      SENSORS.map((s) => {
        const cells = new Map<string, { cx: number; cy: number }>();
        const pts = s.pts.map((p) => {
          const h = hexOf(p.x, p.y);
          cells.set(h.key, h);
          return { ...p, ...h };
        });
        return { ...s, pts, cells: [...cells.values()] };
      }),
    [],
  );
  const grid = useMemo(() => {
    const out: { cx: number; cy: number }[] = [];
    for (let rz = -1; rz <= Math.ceil(PANEL_H / (HEX * 1.5)) + 1; rz++)
      for (let rx = -Math.ceil(rz / 2) - 1; rx <= PANEL_W / (HEX * Math.sqrt(3)) - rz / 2 + 1; rx++) {
        const cx = HEX * Math.sqrt(3) * (rx + rz / 2);
        const cy = HEX * 1.5 * rz;
        if (cx > -HEX && cx < PANEL_W + HEX && cy > -HEX && cy < PANEL_H + HEX) out.push({ cx, cy });
      }
    return out;
  }, []);

  return (
    <svg ref={ref} viewBox="0 0 380 250" className="h-auto w-full" role="img" aria-label={snap ? 'Fire points snapping into hexagons: both satellites end up with a similar count of hexagon-days' : 'The same three fires: MODIS records a few large-pixel points, VIIRS many small-pixel points'}>
      <defs>
        {sensors.map((_, i) => (
          <clipPath key={i} id={`panel-${snap ? 'h' : 'p'}-${i}`}>
            <rect width={PANEL_W} height={PANEL_H} rx={8} />
          </clipPath>
        ))}
      </defs>
      {sensors.map((s, i) => (
        <g key={s.name} transform={`translate(${i * (PANEL_W + 40)}, 0)`}>
          <rect width={PANEL_W} height={PANEL_H} rx={8} fill="#0A1124" stroke={LINE} />
          <g clipPath={`url(#panel-${snap ? 'h' : 'p'}-${i})`}>
            {snap &&
              grid.map((g, k) => <path key={k} d={hexPath(g.cx, g.cy)} fill="none" stroke={LINE} strokeWidth={1} />)}
            {snap &&
              s.cells.map((c) => (
                <path
                  key={`${c.cx},${c.cy}`}
                  d={hexPath(c.cx, c.cy, HEX - 1)}
                  fill={GOLD}
                  style={{ opacity: snapped ? 0.85 : 0, transition: `opacity 500ms var(--ease) ${snapped ? 450 : 0}ms` }}
                />
              ))}
            {s.pts.map((p, k) => (
              <circle
                key={k}
                r={s.r}
                cx={0}
                cy={0}
                fill={s.color}
                style={{
                  transform: `translate(${snapped ? p.cx : p.x}px, ${snapped ? p.cy : p.y}px)`,
                  opacity: shown ? (snapped ? 0 : 0.95) : 0,
                  transition: `transform 600ms var(--ease) ${k * 6}ms, opacity 400ms var(--ease) ${snapped ? 350 : k * 12}ms`,
                }}
              />
            ))}
          </g>
          <text x={0} y={PANEL_H + 22} fill="#EEF2FB" fontSize={13} fontWeight={500}>
            {s.name}
            <tspan fill={TEXT2} fontWeight={400}>
              {'  '}
              {s.note}
            </tspan>
          </text>
          <text x={0} y={PANEL_H + 42} fill={snapped ? GOLD_PALE : TEXT2} fontSize={13} className="num">
            {snapped ? `${s.cells.length} hexagon-days` : `${s.pts.length} points`}
          </text>
        </g>
      ))}
    </svg>
  );
}

// ---------- flares (step 3) ----------

const MONTHS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];
const FIELD = [0, 0, 0, 0.35, 0, 0, 0.5, 1, 0.7, 0, 0, 0];

/** A gas flare is hot every month of every year; a wheat field only around harvest. */
export function FlareVsField() {
  const [ref, visible] = useInView<SVGSVGElement>();
  const reduced = useStore((s) => s.reducedMotion);
  const [m, setM] = useState(7);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!visible || reduced) return;
    const id = setInterval(() => {
      setM((x) => (x + 1) % 12);
      setTick((t) => t + 1);
    }, 420);
    return () => clearInterval(id);
  }, [visible, reduced]);

  const rows = [
    { label: 'Gas flare', vals: MONTHS.map(() => 1), verdict: 'Hot in 12 of 12 months: removed', kept: false },
    { label: 'Wheat field', vals: FIELD, verdict: `Hot in ${FIELD.filter((v) => v > 0).length} of 12 months: kept`, kept: true },
  ];
  const X0 = 96;
  const STEP = 23;
  return (
    <svg ref={ref} viewBox="0 0 380 200" className="h-auto w-full" role="img" aria-label="A gas flare is hot every month and is removed; a wheat field burns around harvest and is kept">
      {MONTHS.map((l, i) => (
        <text key={i} x={X0 + i * STEP} y={14} textAnchor="middle" fontSize={13} fill={i === m ? GOLD_PALE : TEXT3} className="num">
          {l}
        </text>
      ))}
      {rows.map((r, k) => {
        const y = 52 + k * 78;
        return (
          <g key={r.label}>
            <text x={0} y={y + 5} fontSize={13} fill="#EEF2FB">
              {r.label}
            </text>
            {r.vals.map((v, i) => {
              const flicker = !r.kept && !reduced ? 0.75 + 0.25 * Math.sin((tick + i * 3) * 1.7) : 1;
              const a = v * flicker;
              return (
                <path
                  key={i}
                  d={hexPath(X0 + i * STEP, y, 9.5)}
                  fill={v > 0 ? GOLD : '#141C38'}
                  fillOpacity={v > 0 ? 0.25 + 0.75 * a : 1}
                  stroke={i === m ? GOLD_PALE : 'transparent'}
                  strokeWidth={1.5}
                  style={{ transition: 'fill-opacity 300ms var(--ease)' }}
                />
              );
            })}
            <text x={X0 - 10} y={y + 34} fontSize={13} fill={r.kept ? GOLD_PALE : TEXT2}>
              {r.verdict}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ---------- calibration scatter (step 4) ----------

/** Kazakhstan, every month of 2012–2019: MODIS cell-days against VIIRS cell-days, log axes. */
export function CalibrationScatter({ ratio }: { ratio: number | null }) {
  const series = useSeries('KAZ');
  const [ref, visible] = useInView<SVGSVGElement>();
  const reduced = useStore((s) => s.reducedMotion);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (visible || reduced) setShown(true);
  }, [visible, reduced]);

  const pts = useMemo(() => {
    if (!series) return [];
    const out: { x: number; y: number; k: number }[] = [];
    series.ym.forEach((ym, i) => {
      const y = Number(ym.slice(0, 4));
      const m = series.modis_only[i];
      const v = series.viirs[i];
      if (y >= 2012 && y <= 2019 && m > 0 && v != null && v > 0) out.push({ x: m, y: v, k: out.length });
    });
    return out;
  }, [series]);

  const L = 44;
  const B = 172;
  const W = 380 - L - 10;
  const H = B - 10;
  const lo = 0; // 10^0
  const hi = 5; // 10^5
  const sx = (v: number) => L + ((Math.log10(v) - lo) / (hi - lo)) * W;
  const sy = (v: number) => B - ((Math.log10(v) - lo) / (hi - lo)) * H;
  const ticks = [1, 10, 100, 1000, 10000, 100000];
  const lab = (t: number) => (t >= 1000 ? `${t / 1000}k` : String(t));

  return (
    <svg ref={ref} viewBox="0 0 380 210" className="h-auto w-full" role="img" aria-label="Scatter of monthly MODIS against VIIRS cell-days in Kazakhstan, 2012 to 2019, close to a straight line">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={sx(t)} x2={sx(t)} y1={10} y2={B} stroke={LINE} />
          <line x1={L} x2={L + W} y1={sy(t)} y2={sy(t)} stroke={LINE} />
          <text x={sx(t)} y={B + 16} fontSize={12} fill={TEXT2} textAnchor={t === 100000 ? 'end' : 'middle'} className="num">
            {lab(t)}
          </text>
          <text x={L - 6} y={sy(t) + 4} fontSize={12} fill={TEXT2} textAnchor="end" className="num">
            {lab(t)}
          </text>
        </g>
      ))}
      {ratio && (
        <line
          x1={sx(1)}
          y1={sy(ratio)}
          x2={sx(100000 / ratio)}
          y2={sy(100000)}
          stroke={GOLD_PALE}
          strokeDasharray="4 4"
          strokeWidth={1}
          style={{ opacity: shown ? 0.9 : 0, transition: 'opacity 600ms var(--ease) 1200ms' }}
        />
      )}
      {pts.map((p) => (
        <circle
          key={p.k}
          cx={sx(p.x)}
          cy={sy(p.y)}
          r={2.6}
          fill={GOLD}
          style={{ opacity: shown ? 0.8 : 0, transition: `opacity 300ms var(--ease) ${reduced ? 0 : p.k * 10}ms` }}
        />
      ))}
      <text x={L + W} y={B + 34} fontSize={12} fill={TEXT2} textAnchor="end">
        MODIS cell-days per month
      </text>
      <text x={L + 4} y={22} fontSize={12} fill={TEXT2}>
        VIIRS
      </text>
      {ratio && (
        <text x={sx(100000 / ratio) - 10} y={sy(100000) + 14} fontSize={13} fill={GOLD_PALE} textAnchor="end" className="num">
          VIIRS = ×{ratio.toFixed(2)} MODIS
        </text>
      )}
    </svg>
  );
}

// ---------- one series with a range (step 5) ----------

/** Kazakhstan by year: the naive splice (muted) and the harmonized record with its 90% range. */
export function OneSeries() {
  const series = useSeries('KAZ');
  const [ref, visible] = useInView<SVGSVGElement>();
  const reduced = useStore((s) => s.reducedMotion);
  const [drawn, setDrawn] = useState(false);
  useEffect(() => {
    if (visible || reduced) setDrawn(true);
  }, [visible, reduced]);

  const years = useMemo(() => {
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
    return [...acc.entries()].filter(([, a]) => a.n === 12).map(([y, a]) => ({ y, ...a }));
  }, [series]);
  if (!years) return <svg ref={ref} viewBox="0 0 380 210" className="h-auto w-full" />;

  const L = 44;
  const B = 172;
  const W = 380 - L - 10;
  const top = Math.max(...years.map((d) => d.hi)) * 1.05;
  const sx = (y: number) => L + ((y - years[0].y) / (years[years.length - 1].y - years[0].y)) * W;
  const sy = (v: number) => B - (v / top) * (B - 12);
  const line = (k: 'naive' | 'harm') => years.map((d, i) => `${i ? 'L' : 'M'}${sx(d.y).toFixed(1)},${sy(d[k]).toFixed(1)}`).join('');
  const band =
    years.map((d, i) => `${i ? 'L' : 'M'}${sx(d.y).toFixed(1)},${sy(d.hi).toFixed(1)}`).join('') +
    [...years].reverse().map((d) => `L${sx(d.y).toFixed(1)},${sy(d.lo).toFixed(1)}`).join('') +
    'Z';
  const yt = [0, 50000, 100000, 150000].filter((t) => t < top);
  const draw = (delay: number) => ({
    strokeDasharray: 1,
    strokeDashoffset: drawn ? 0 : 1,
    transition: reduced ? 'none' : `stroke-dashoffset 1600ms var(--ease) ${delay}ms`,
  });

  return (
    <svg ref={ref} viewBox="0 0 380 210" className="h-auto w-full" role="img" aria-label="Kazakhstan annual fire activity: the naive splice jumps at 2012, the harmonized record does not">
      {yt.map((t) => (
        <g key={t}>
          <line x1={L} x2={L + W} y1={sy(t)} y2={sy(t)} stroke={LINE} />
          <text x={L - 6} y={sy(t) + 4} fontSize={12} fill={TEXT2} textAnchor="end" className="num">
            {t ? `${t / 1000}k` : '0'}
          </text>
        </g>
      ))}
      {[2005, 2010, 2015, 2020, 2025].map((y) => (
        <text key={y} x={sx(y)} y={B + 16} fontSize={12} fill={TEXT2} textAnchor={sx(y) > L + W - 14 ? 'end' : 'middle'} className="num">
          {y}
        </text>
      ))}
      <line x1={sx(2012)} x2={sx(2012)} y1={10} y2={B} stroke={ICE} strokeOpacity={0.8} />
      <text x={sx(2012) + 5} y={20} fontSize={12} fill={ICE}>
        VIIRS joins
      </text>
      <path d={band} fill="rgba(245,184,61,0.2)" style={{ opacity: drawn ? 1 : 0, transition: 'opacity 800ms var(--ease) 900ms' }} />
      <path d={line('naive')} pathLength={1} fill="none" stroke={TEXT3} strokeWidth={1.5} style={draw(0)} />
      <path d={line('harm')} pathLength={1} fill="none" stroke={GOLD} strokeWidth={2} style={draw(500)} />
      <text x={L + W} y={B + 34} fontSize={12} fill={TEXT2} textAnchor="end">
        Cell-days per year, Kazakhstan
      </text>
    </svg>
  );
}
