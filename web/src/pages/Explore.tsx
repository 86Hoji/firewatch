import { useLayoutEffect } from 'react';
import { Link } from 'react-router-dom';
import { Dateline } from '../components/Dateline';
import { TimeBar } from '../components/TimeBar';
import { RegionTooltip } from '../components/RegionTooltip';
import { ExplorePanels } from '../components/explore/ExplorePanels';
import { useStore } from '../store';
import { frame } from '../map/MapEngine';
import { engine } from '../map/MapStage';

/** Width of the panel column plus its gap, kept clear when framing the map. */
const PANEL_INSET = 380 + 16;

export function Explore() {
  useLayoutEffect(() => {
    frame.right = PANEL_INSET;
    engine?.reframe();
    return () => {
      frame.right = 0;
    };
  }, []);
  const introDone = useStore((s) => s.introDone);
  const reduced = useStore((s) => s.reducedMotion);
  const shown = introDone || reduced;
  return (
    <div className="pointer-events-none fixed inset-0">
      <header
        className="absolute left-[var(--gutter)] right-[var(--gutter)] top-[22px] flex items-baseline justify-between"
        style={{ opacity: shown ? 1 : 0, transition: 'opacity 600ms var(--ease)' }}
      >
        <Link to="/" className="display pointer-events-auto text-[22px] text-text no-underline">
          Firewatch
        </Link>
      </header>
      <Dateline />
      <RegionTooltip />
      <TimeBar rightInset={PANEL_INSET} />
      <ExplorePanels />
    </div>
  );
}
