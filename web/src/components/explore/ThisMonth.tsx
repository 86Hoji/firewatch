import { useMemo } from 'react';
import { useStore } from '../../store';
import { monthlyNormal, useCount, useRegions } from '../../lib/hooks';
import { fmtCD, fmtPct, ymLong } from '../../lib/format';
import type { Series } from '../../lib/data';
import { InfoHint } from '../InfoHint';
import { Panel } from './Panel';

const NAMES: Record<string, string> = { KAZ: 'Kazakhstan', UZB: 'Uzbekistan' };

interface Row {
  ym: string[];
  harmonized: number[];
  lo90: number[];
  hi90: number[];
  naive?: number[];
  viirs?: (number | null)[];
}

function downloadCSV(name: string, r: Row) {
  const head = ['month', 'harmonized_cell_days', 'lo90', 'hi90'];
  if (r.naive) head.push('naive_cell_days', 'viirs_cell_days');
  const lines = [head.join(',')];
  r.ym.forEach((ym, i) => {
    const row = [ym, r.harmonized[i], r.lo90[i], r.hi90[i]];
    if (r.naive) row.push(r.naive[i], r.viirs?.[i] ?? '');
    lines.push(row.join(','));
  });
  const blob = new Blob([lines.join('\n') + '\n'], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `firewatch_${name}_monthly.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

/** The selected place in the current month: value, range, change vs normal, and its data as CSV. */
export function ThisMonth({ series }: { series: Series | null }) {
  const { country, selected, yms, ymIndex, userChange, playing, reducedMotion } = useStore();
  const regions = useRegions(selected ? country : null);
  const region = selected ? regions?.find((r) => r.iso === selected) ?? null : null;

  const row: Row | null = useMemo(() => {
    if (region) return region;
    if (!series) return null;
    return { ...series, naive: series.naive_celldays, viirs: series.viirs };
  }, [region, series]);
  const normal = useMemo(() => (row ? monthlyNormal(row.ym, row.harmonized) : null), [row]);

  const ym = yms[ymIndex];
  const i = row && ym ? row.ym.indexOf(ym) : -1;
  const v = i >= 0 ? row!.harmonized[i] : NaN;
  const lo = i >= 0 ? row!.lo90[i] : NaN;
  const hi = i >= 0 ? row!.hi90[i] : NaN;
  const nm = normal && ym ? normal[Number(ym.slice(5, 7)) - 1] : 0;
  const pct = Number.isFinite(v) && nm > 0.5 ? (100 * (v - nm)) / nm : null;
  const animate = userChange && !playing && !reducedMotion;
  const shown = useCount(v, animate);
  const shownPct = useCount(pct ?? 0, animate);
  const observed = Number.isFinite(lo) && lo === hi;
  const place = region ? region.name : NAMES[country] ?? country;
  const month = ym ? ymLong(ym).split(' ')[0] : '';

  return (
    <Panel
      title={place}
      aside={
        region ? (
          <button type="button" onClick={() => useStore.getState().setSelected(null)} className="text-[13px] text-text-map-2 underline-offset-4 hover:text-text hover:underline">
            Back to {NAMES[country]}
          </button>
        ) : (
          ym && ymLong(ym)
        )
      }
    >
      <div className="num flex items-baseline gap-2">
        <span className="text-[32px] leading-none text-gold-pale">{fmtCD(shown)}</span>
        <span className="text-[15px] text-text-map-2">cell-days of fire</span>
        <InfoHint />
      </div>
      <dl className="num m-0 mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-[13px]">
        <dt className="text-text-map-2">{observed ? 'Source' : '90% range'}</dt>
        <dd className="m-0 text-text">{Number.isFinite(lo) ? (observed ? 'Observed by VIIRS' : `${fmtCD(lo)}–${fmtCD(hi)}`) : '—'}</dd>
        <dt className="text-text-map-2">Normal {month}</dt>
        <dd className="m-0 text-text">
          {fmtCD(nm)}
          <span className="text-text-map-2"> (2012–2019 average)</span>
        </dd>
        <dt className="text-text-map-2">Change</dt>
        <dd className={`m-0 ${pct == null ? 'text-text' : pct > 0 ? 'text-gold' : 'text-text'}`}>
          {pct == null ? 'Too few fires to compare' : Math.round(pct) === 0 ? 'About normal' : `${fmtPct(shownPct)} vs normal`}
        </dd>
      </dl>
      <button
        type="button"
        disabled={!row}
        onClick={() => row && downloadCSV(region ? region.iso : country, row)}
        className="mt-4 flex h-9 w-full items-center justify-center gap-2 rounded-[6px] border border-[rgba(255,231,163,0.22)] text-[15px] text-text transition-colors duration-[160ms] hover:border-[rgba(255,231,163,0.45)] hover:bg-[rgba(245,184,61,0.08)]"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden fill="none" stroke="currentColor" strokeWidth="1.4">
          <path d="M7 1.5v8M3.8 6.6 7 9.8l3.2-3.2M2 12.5h10" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Download CSV
        <span className="text-text-map-2">{region ? region.name : NAMES[country]}, monthly</span>
      </button>
    </Panel>
  );
}
