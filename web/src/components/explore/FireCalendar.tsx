import { useMemo, useState } from 'react';
import { useStore } from '../../store';
import { useWidth } from '../../lib/hooks';
import { rampCSS } from '../../lib/scale';
import { fmtCD, ymLong } from '../../lib/format';
import type { Series } from '../../lib/data';
import { Panel } from './Panel';

const ROW = 10;
const GAP = 1.5;
const LABEL_W = 30;
const MONTH_LABELS: [number, string][] = [
  [0, 'Jan'],
  [3, 'Apr'],
  [6, 'Jul'],
  [9, 'Oct'],
];

/**
 * Years across, months down: one cell per month, coloured on the same square-root ramp as the time
 * bar. The current month is outlined in gold; a click jumps the map there.
 */
export function FireCalendar({ series }: { series: Series | null }) {
  const yms = useStore((s) => s.yms);
  const ymIndex = useStore((s) => s.ymIndex);
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);

  const grid = useMemo(() => {
    if (!series || !yms.length) return null;
    const y0 = Number(yms[0].slice(0, 4));
    const y1 = Number(yms[yms.length - 1].slice(0, 4));
    const top = Math.max(...series.harmonized);
    const byYm = new Map(series.ym.map((d, i) => [d, series.harmonized[i]]));
    const cells = yms.map((ym, i) => {
      const v = byYm.get(ym) ?? 0;
      return { i, ym, v, col: Number(ym.slice(0, 4)) - y0, row: Number(ym.slice(5, 7)) - 1, fill: rampCSS(0.1 + 0.9 * Math.sqrt(Math.max(0, v) / top)) };
    });
    return { y0, nYears: y1 - y0 + 1, cells };
  }, [series, yms]);

  const colW = grid && width ? (width - LABEL_W) / grid.nYears : 0;
  const h = 12 * (ROW + GAP);
  const cur = grid?.cells[ymIndex];
  const hv = hover != null ? grid?.cells[hover] : null;
  const jump = (i: number) => {
    const s = useStore.getState();
    s.setPlaying(false);
    s.setYmIndex(i, true);
  };

  return (
    <Panel title="Fire calendar" aside={hv ? <><span className="text-text">{fmtCD(hv.v)}</span> in {ymLong(hv.ym)}</> : 'Click a month to show it'}>
      <div ref={ref} className="relative">
        {grid && colW > 0 && (
          <svg width={width} height={h + 22} role="grid" aria-label="Harmonized fire activity by month and year" onMouseLeave={() => setHover(null)}>
            {MONTH_LABELS.map(([r, l]) => (
              <text key={l} x={0} y={r * (ROW + GAP) + ROW} className="num" fill="#B7C2DB" fontSize={13}>
                {l}
              </text>
            ))}
            {grid.cells.map((c) => (
              <rect
                key={c.ym}
                x={LABEL_W + c.col * colW}
                y={c.row * (ROW + GAP)}
                width={Math.max(1, colW - GAP)}
                height={ROW}
                rx={1.5}
                fill={c.fill}
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHover(c.i)}
                onClick={() => jump(c.i)}
              >
                <title>{`${ymLong(c.ym)}: ${fmtCD(c.v)} cell-days`}</title>
              </rect>
            ))}
            {/* 2012 seam: where VIIRS joins the record */}
            {2012 - grid.y0 > 0 && (
              <line
                x1={LABEL_W + (2012 - grid.y0) * colW - GAP / 2}
                x2={LABEL_W + (2012 - grid.y0) * colW - GAP / 2}
                y1={-2}
                y2={h + 2}
                stroke="#93C5FD"
                strokeOpacity={0.75}
                strokeWidth={1}
              />
            )}
            {cur && (
              <rect
                x={LABEL_W + cur.col * colW - 1.5}
                y={cur.row * (ROW + GAP) - 1.5}
                width={colW - GAP + 3}
                height={ROW + 3}
                rx={2.5}
                fill="none"
                stroke="#F5B83D"
                strokeWidth={1.5}
                pointerEvents="none"
              />
            )}
            {Array.from({ length: grid.nYears }, (_, k) => grid.y0 + k)
              .filter((y) => y % 5 === 0)
              .map((y) => (
                <text
                  key={y}
                  x={LABEL_W + (y - grid.y0) * colW + colW / 2}
                  y={h + 16}
                  textAnchor="middle"
                  className="num"
                  fill="#B7C2DB"
                  fontSize={13}
                >
                  {y}
                </text>
              ))}
          </svg>
        )}
      </div>
    </Panel>
  );
}
