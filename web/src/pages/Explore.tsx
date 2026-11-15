import { Dateline } from '../components/Dateline';
import { TimeBar } from '../components/TimeBar';
import { RegionTooltip } from '../components/RegionTooltip';
import { useStore } from '../store';

export function Explore() {
  const introDone = useStore((s) => s.introDone);
  const reduced = useStore((s) => s.reducedMotion);
  const shown = introDone || reduced;
  return (
    <div className="pointer-events-none fixed inset-0">
      <header
        className="absolute left-[var(--gutter)] right-[var(--gutter)] top-[22px] flex items-baseline justify-between"
        style={{ opacity: shown ? 1 : 0, transition: 'opacity 600ms var(--ease)' }}
      >
        <a href="/" className="display pointer-events-auto text-[22px] text-text no-underline">
          Firewatch
        </a>
      </header>
      <Dateline />
      <RegionTooltip />
      <TimeBar />
      <p
        className="absolute bottom-[var(--gutter)] right-[var(--gutter)] m-0 hidden max-w-[300px] text-right text-[13px] leading-[1.45] text-text-2 md:block"
        style={{ opacity: shown ? 1 : 0, transition: 'opacity 600ms var(--ease)' }}
      >
        Fire detections from NASA FIRMS, MODIS and VIIRS. Night lights from NASA Black Marble, made by the same VIIRS
        instrument.
      </p>
    </div>
  );
}
