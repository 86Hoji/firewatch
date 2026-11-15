import { useStore } from '../store';
import { useCount, useSeries } from '../lib/hooks';
import { fmtCD, ymLong } from '../lib/format';
import { InfoHint } from './InfoHint';
import { COUNTRY_NAMES } from '../lib/data';


/** "September 2023" set like a newspaper dateline, the country figure beneath it. */
export function Dateline() {
  const { yms, ymIndex, country, userChange, playing, reducedMotion, introDone } = useStore();
  const series = useSeries(country);
  const ym = yms[ymIndex];
  const i = series && ym ? series.ym.indexOf(ym) : -1;
  const value = i >= 0 ? series!.harmonized[i] : NaN;
  const lo = i >= 0 ? series!.lo90[i] : NaN;
  const hi = i >= 0 ? series!.hi90[i] : NaN;
  const animate = userChange && !playing && !reducedMotion;
  const shown = useCount(value, animate);
  const observed = Number.isFinite(lo) && lo === hi;

  return (
    <div
      className="pointer-events-none absolute left-[var(--gutter)] top-[64px] md:top-[76px]"
      style={{
        opacity: introDone || reducedMotion ? 1 : 0,
        transition: 'opacity 600ms var(--ease)',
        textShadow: '0 1px 18px rgba(7,11,24,0.85)',
      }}
    >
      <h1 className="display m-0 text-[44px] text-text md:text-[76px]" aria-live="polite">
        {ym ? ymLong(ym) : ' '}
      </h1>
      <p className="num m-0 mt-2 text-[15px] leading-snug text-text-map-2 md:mt-3">
        <span className="font-medium text-text">{COUNTRY_NAMES[country] ?? country}</span>
        <span className="ml-3 text-text">{fmtCD(shown)}</span>
        <span className="ml-1">cell-days</span>
        <span className="ml-1.5">
          <InfoHint />
        </span>
        <br className="md:hidden" />
        <span className="md:ml-3">
          {Number.isFinite(lo) ? (observed ? 'observed by VIIRS' : `90% range ${fmtCD(lo)}–${fmtCD(hi)}`) : ''}
        </span>
      </p>
    </div>
  );
}
