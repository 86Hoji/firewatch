import { useEffect, useRef } from 'react';
import { AnimatePresence, motion, useMotionValue, useSpring } from 'framer-motion';
import { useStore } from '../store';
import { useMediaQuery, useRegions } from '../lib/hooks';
import { fmtCD, fmtPct, ymLong } from '../lib/format';
import { pointer } from '../map/pointer';

const W = 248;

/** Glass tooltip that follows the cursor on a spring; docks above the time bar on touch. */
export function RegionTooltip() {
  const hover = useStore((s) => s.hover);
  const ym = useStore((s) => s.yms[s.ymIndex]);
  const regions = useRegions(hover?.country ?? null);
  const coarse = useMediaQuery('(pointer: coarse)');

  const mx = useMotionValue(pointer.x);
  const my = useMotionValue(pointer.y);
  const x = useSpring(mx, { stiffness: 260, damping: 30, mass: 0.6 });
  const y = useSpring(my, { stiffness: 260, damping: 30, mass: 0.6 });
  const box = useRef<HTMLDivElement>(null);

  useEffect(
    () =>
      pointer.subscribe((px, py) => {
        const h = box.current?.offsetHeight ?? 120;
        const flipX = px + 20 + W > window.innerWidth - 16;
        const flipY = py + 20 + h > window.innerHeight - 140;
        mx.set(flipX ? px - 20 - W : px + 20);
        my.set(flipY ? py - 20 - h : py + 20);
      }),
    [mx, my],
  );

  const region = regions?.find((r) => r.iso === hover?.iso);
  const i = region && ym ? region.ym.indexOf(ym) : -1;
  const v = i >= 0 ? region!.harmonized[i] : null;
  const lo = i >= 0 ? region!.lo90[i] : null;
  const hi = i >= 0 ? region!.hi90[i] : null;
  const m = ym ? Number(ym.slice(5, 7)) - 1 : 0;
  const normal = region?.normal[m] ?? 0;
  const pct = v != null && normal > 0.5 ? (100 * (v - normal)) / normal : null;
  const observed = lo != null && lo === hi;
  const monthName = ym ? ymLong(ym).split(' ')[0] : '';

  const body = hover && (
    <div className="glass rounded-[14px] px-4 py-3.5" style={{ width: coarse ? undefined : W }}>
      <div className="text-[15px] font-medium leading-tight text-text">{hover.name}</div>
      <div className="mt-0.5 text-[13px] text-text-map-2">{ym ? ymLong(ym) : ''}</div>
      <div className="num mt-3 flex items-baseline gap-2">
        <span className="text-[22px] leading-none text-gold-pale">{fmtCD(v)}</span>
        <span className="text-[13px] text-text-map-2">cell-days of fire</span>
      </div>
      <div className="num mt-1.5 text-[13px] text-text-map-2">
        {v == null ? 'No data for this region' : observed ? 'Observed by VIIRS' : `90% range ${fmtCD(lo)}–${fmtCD(hi)}`}
      </div>
      {pct != null && (
        <div className="num mt-2.5 border-t border-[rgba(148,170,220,0.12)] pt-2.5 text-[13px] text-text-map-2">
          {Math.round(pct) === 0 ? (
            <>About the {monthName} average of 2012–2019</>
          ) : (
            <>
              <span className={pct > 0 ? 'text-gold' : 'text-text'}>{fmtPct(Math.abs(pct)).replace('+', '')}</span>{' '}
              {pct > 0 ? 'above' : 'below'} the {monthName} average of 2012–2019
            </>
          )}
        </div>
      )}
    </div>
  );

  if (coarse) {
    return (
      <AnimatePresence>
        {hover && (
          <motion.div
            key="dock"
            role="status"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ type: 'spring', stiffness: 260, damping: 30 }}
            className="pointer-events-none absolute bottom-[112px] left-[var(--gutter)] right-[var(--gutter)]"
          >
            {body}
          </motion.div>
        )}
      </AnimatePresence>
    );
  }

  return (
    <motion.div
      ref={box}
      role="status"
      className="pointer-events-none fixed left-0 top-0 z-20"
      style={{ x, y }}
      animate={{ opacity: hover ? 1 : 0 }}
      transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}
    >
      {body}
    </motion.div>
  );
}
