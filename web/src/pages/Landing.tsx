import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useStore } from '../store';
import { frame } from '../map/MapEngine';
import { engine } from '../map/MapStage';
import { loadValidation, type Validation } from '../lib/validation';

/** Width of the text column plus gutter, kept clear when framing the globe. */
const COLUMN_INSET = 520 + 28;

const x2 = (v: number | undefined) => (v == null ? '…' : `×${v.toFixed(2)}`);

export function Landing() {
  const shown = useStore((s) => s.introDone || s.reducedMotion);
  const [v, setV] = useState<Validation | null>(null);
  const how = useRef<HTMLElement>(null);

  useLayoutEffect(() => {
    frame.left = COLUMN_INSET;
    engine?.reframe();
    return () => {
      frame.left = 0;
    };
  }, []);
  useEffect(() => {
    loadValidation().then(setV).catch(() => {});
  }, []);

  const uz = v?.uz_test.steps;
  const ba = v?.burned_area.KAZ;

  return (
    <div className="pointer-events-none fixed inset-0">
      <div className="pointer-events-auto absolute inset-y-0 left-0 w-full overflow-y-auto overscroll-contain md:w-[calc(520px+2*var(--gutter))]">
        <div className="flex min-h-full flex-col gap-4 px-[var(--gutter)] pb-[var(--gutter)] pt-[22px]">
          <header>
            <span className="display text-[22px] text-text">Firewatch</span>
          </header>

          <section
            className="glass mt-[18vh] rounded-[22px] px-6 py-7 md:mt-[12vh] md:px-9 md:py-9"
            style={{ opacity: shown ? 1 : 0, transform: shown ? 'none' : 'translateY(8px)', transition: 'opacity 600ms var(--ease), transform 600ms var(--ease)' }}
          >
            <h1 className="display m-0 text-[40px] leading-[1.05] tracking-[-0.01em] text-text md:text-[60px]">
              Twenty-five years of fire in Central Asia, on one scale.
            </h1>
            <p className="m-0 mt-5 max-w-[44ch] text-[17px] leading-[1.6] text-text-map-2">
              Two generations of NASA satellites saw the same fires differently. We stitched MODIS (since 2000) and VIIRS
              (since 2012) into one consistent record.
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-3">
              <Link
                to="/explore"
                className="inline-flex h-11 items-center rounded-[6px] bg-gold px-5 text-[15px] font-medium text-night no-underline transition-colors duration-[160ms] hover:bg-gold-pale active:bg-ember"
              >
                Open the map
              </Link>
              <button
                type="button"
                onClick={() => how.current?.scrollIntoView({ behavior: useStore.getState().reducedMotion ? 'auto' : 'smooth', block: 'start' })}
                className="inline-flex h-11 items-center rounded-[6px] px-4 text-[15px] text-text-map-2 transition-colors duration-[160ms] hover:bg-white/5 hover:text-text"
              >
                How it works
              </button>
            </div>
          </section>

          <section
            ref={how}
            aria-labelledby="how"
            className="glass scroll-mt-[22px] rounded-[14px] px-6 py-6 md:px-9"
            style={{ opacity: shown ? 1 : 0, transition: 'opacity 600ms var(--ease) 150ms' }}
          >
            <h2 id="how" className="m-0 text-[17px] font-medium text-text">
              How it works
            </h2>
            <p className="m-0 mt-3 max-w-[60ch] text-[15px] leading-[1.6] text-text-map-2">
              In 2012 the number of fires nearly tripled overnight. The fires didn’t change — the satellite did. During
              the eight years both satellites flew, we learn how VIIRS sees compared with MODIS, then carry that back to
              2000. Now a month in 2001 and a month in 2024 mean the same thing.
            </p>
            <ul className="m-0 mt-5 flex list-none flex-col gap-3 p-0 text-[15px] leading-[1.6] text-text">
              <li>The 90% ranges now contain the true value in 91% of test months, up from 41%.</li>
              <li>
                In Uzbekistan the naive record jumps <span className="num text-gold-pale">{x2(uz?.naive.step_ratio)}</span> at
                2012; ours moves <span className="num text-gold-pale">{x2(uz?.harmonized_local.step_ratio)}</span>.
              </li>
              <li>
                Against MODIS burned area, an independent product, the naive record steps{' '}
                <span className="num text-gold-pale">{x2(ba?.naive.step_given_burned_area.step_factor)}</span> at 2012; the
                harmonized one stays continuous at{' '}
                <span className="num text-gold-pale">{x2(ba?.harmonized.step_given_burned_area.step_factor)}</span>.
              </li>
            </ul>
            <Link to="/validation" className="mt-5 inline-block text-[15px] text-gold underline-offset-4 hover:underline">
              See the evidence
            </Link>
          </section>

          <footer className="mt-auto px-1 text-[13px] leading-[1.55] text-text-map-2">
            <p className="m-0">
              Made by the Firewatch team for NASA Space Apps 2026. Pipeline baseline by Elbek.
            </p>
            <p className="m-0 mt-1">
              Fire detections from NASA FIRMS (MODIS and VIIRS). Night lights from NASA GIBS Black Marble. Burned area from
              MODIS MCD64A1.
            </p>
          </footer>
        </div>
      </div>
    </div>
  );
}
