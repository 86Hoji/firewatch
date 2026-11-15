import { useState } from 'react';
import { motion, type PanInfo } from 'framer-motion';
import { useStore } from '../../store';
import { useMediaQuery, useRegions, useSeries } from '../../lib/hooks';
import { fmtCD, ymLong } from '../../lib/format';
import { CountrySwitch } from './CountrySwitch';
import { ThisMonth } from './ThisMonth';
import { BeforeAfter } from './BeforeAfter';
import { FireCalendar } from './FireCalendar';

const SPRING = { type: 'spring', stiffness: 260, damping: 30 } as const;
const NAMES: Record<string, string> = { KAZ: 'Kazakhstan', UZB: 'Uzbekistan' };

function Credits() {
  return (
    <p className="m-0 px-1 pb-1 text-[13px] leading-[1.5] text-text-map-2">
      Fire detections from NASA FIRMS, MODIS and VIIRS. Night lights from NASA Black Marble, made by the same VIIRS
      instrument.
    </p>
  );
}

/** Right column on desktop; a bottom sheet above the time bar on phones. */
export function ExplorePanels() {
  const country = useStore((s) => s.country);
  const shown = useStore((s) => s.introDone || s.reducedMotion);
  const series = useSeries(country);
  const desktop = useMediaQuery('(min-width: 768px)');

  const body = (
    <>
      <CountrySwitch />
      <ThisMonth series={series} />
      <BeforeAfter series={series} />
      <FireCalendar series={series} />
      <Credits />
    </>
  );

  if (desktop) {
    return (
      <motion.aside
        aria-label="Details"
        initial={false}
        animate={{ opacity: shown ? 1 : 0, x: shown ? 0 : 16 }}
        transition={{ ...SPRING, opacity: { duration: 0.6, ease: [0.22, 1, 0.36, 1] } }}
        className="pointer-events-none absolute bottom-[var(--gutter)] right-[var(--gutter)] top-[22px] w-[380px]"
      >
        <div className="pointer-events-auto flex max-h-full flex-col gap-3 overflow-y-auto overscroll-contain pr-0.5 [scrollbar-width:thin]">
          {body}
        </div>
      </motion.aside>
    );
  }
  return <Sheet shown={shown}>{body}</Sheet>;
}

function Sheet({ shown, children }: { shown: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const { country, yms, ymIndex, selected } = useStore();
  const series = useSeries(country);
  const regions = useRegions(selected ? country : null);
  const region = selected ? regions?.find((r) => r.iso === selected) : undefined;
  const row = region ?? series;
  const ym = yms[ymIndex];
  const v = row && ym ? row.harmonized[row.ym.indexOf(ym)] : NaN;
  const onPanEnd = (_: unknown, info: PanInfo) => {
    if (info.offset.y < -24 || info.velocity.y < -300) setOpen(true);
    else if (info.offset.y > 24 || info.velocity.y > 300) setOpen(false);
  };

  return (
    <motion.section
      aria-label="Details"
      initial={false}
      animate={{ opacity: shown ? 1 : 0, height: open ? 'min(64vh, 560px)' : 58 }}
      transition={{ ...SPRING, opacity: { duration: 0.6 } }}
      className="glass pointer-events-auto absolute left-[var(--gutter)] right-[var(--gutter)] flex flex-col overflow-hidden rounded-[14px]"
      style={{ bottom: 'calc(var(--gutter) + 84px)' }}
    >
      <motion.button
        type="button"
        onPanEnd={onPanEnd}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex h-[58px] w-full shrink-0 touch-none flex-col items-stretch px-4 pt-2 text-left"
      >
        <span aria-hidden className="mx-auto mb-2 h-1 w-9 rounded-full bg-[rgba(238,242,251,0.28)]" />
        <span className="flex items-baseline justify-between gap-3">
          <span className="truncate text-[15px] font-medium text-text">
            {region?.name ?? NAMES[country]}
          </span>
          {ym && (
            <span className="num shrink-0 text-[13px] text-text-map-2">
              <span className="text-gold-pale">{fmtCD(v)}</span> in {ymLong(ym)}
            </span>
          )}
        </span>
      </motion.button>
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto overscroll-contain px-2 pb-2 [&_.glass]:bg-transparent [&_.glass]:shadow-none [&_.glass]:[backdrop-filter:none] [&_.glass]:border-[rgba(148,170,220,0.12)]">
        {children}
      </div>
    </motion.section>
  );
}
