import { useEffect, useMemo, useRef, useState } from 'react';
import { useStore } from '../../store';
import { echarts, C, axisLabel } from '../../lib/echarts';
import { fmtCD, ymLong } from '../../lib/format';
import { COUNTRY_NAMES, loadMeta, type Meta, type Series } from '../../lib/data';
import { Panel } from './Panel';


/**
 * The naive MODIS→VIIRS splice (muted) against the harmonized record (gold, with its 90% range).
 * Log scale, so the 2012 jump reads as a level shift rather than a spike.
 */
export function BeforeAfter({ series }: { series: Series | null }) {
  const country = useStore((s) => s.country);
  const yms = useStore((s) => s.yms);
  const ymIndex = useStore((s) => s.ymIndex);
  const hoverIndex = useStore((s) => s.hoverIndex);
  const box = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);

  useEffect(() => {
    loadMeta().then(setMeta);
  }, []);

  const data = useMemo(() => {
    if (!series || !yms.length) return null;
    const idx = new Map(series.ym.map((d, i) => [d, i]));
    // Trailing 12-month totals: seasons cancel out, so the 2012 step in the naive splice is plain to see.
    const pick = (arr: (number | null)[]) => {
      const m = yms.map((ym) => {
        const i = idx.get(ym);
        return i == null ? null : arr[i];
      });
      return m.map((_, k) => {
        if (k < 11) return null;
        let sum = 0;
        for (let j = k - 11; j <= k; j++) {
          const v = m[j];
          if (v == null) return null;
          sum += v;
        }
        return sum;
      });
    };
    const lo = pick(series.lo90);
    const hi = pick(series.hi90);
    return {
      naive: pick(series.naive_celldays),
      harm: pick(series.harmonized),
      lo,
      band: hi.map((h, i) => (h == null || lo[i] == null ? null : h - (lo[i] as number))),
    };
  }, [series, yms]);

  // Build once per data set.
  useEffect(() => {
    if (!box.current || !data) return;
    const c = chart.current ?? echarts.init(box.current, undefined, { renderer: 'canvas' });
    chart.current = c;
    const seam = yms.indexOf('2012-01');
    c.setOption(
      {
        animation: false,
        grid: { left: 40, right: 8, top: 24, bottom: 22 },
        tooltip: {
          trigger: 'axis',
          showContent: false,
          axisPointer: { type: 'line', lineStyle: { color: 'rgba(238,242,251,0.55)', width: 1 }, label: { show: false } },
        },
        xAxis: {
          type: 'category',
          data: yms,
          boundaryGap: false,
          axisLine: { lineStyle: { color: C.line } },
          axisTick: { show: false },
          axisLabel: {
            ...axisLabel,
            interval: (i: number) => yms[i].endsWith('-01') && Number(yms[i].slice(0, 4)) % 5 === 0,
            formatter: (v: string) => v.slice(0, 4),
          },
        },
        yAxis: {
          type: 'value',
          splitNumber: 3,
          splitLine: { lineStyle: { color: C.line } },
          axisLabel: { ...axisLabel, formatter: (v: number) => (v >= 1000 ? `${v / 1000}k` : String(v)) },
        },
        series: [
          { name: 'lo', type: 'line', data: data.lo, stack: 'band', symbol: 'none', lineStyle: { opacity: 0 }, silent: true },
          {
            name: 'band',
            type: 'line',
            data: data.band,
            stack: 'band',
            symbol: 'none',
            lineStyle: { opacity: 0 },
            areaStyle: { color: 'rgba(245,184,61,0.22)' },
            silent: true,
          },
          { name: 'naive', type: 'line', data: data.naive, symbol: 'none', lineStyle: { color: C.text3, width: 1.25 } },
          {
            name: 'harmonized',
            type: 'line',
            data: data.harm,
            symbol: 'none',
            lineStyle: { color: C.gold, width: 1.5 },
            markLine: {
              silent: true,
              symbol: 'none',
              animation: false,
              data: [
                {
                  xAxis: seam,
                  lineStyle: { color: C.ice, width: 1, type: 'solid', opacity: 0.8 },
                  label: { formatter: 'VIIRS joins', position: 'end', distance: 4, color: C.ice, fontFamily: C.font, fontSize: 13 },
                },
                { xAxis: ymIndex, lineStyle: { color: C.goldPale, width: 1, type: 'solid', opacity: 0.9 }, label: { show: false } },
              ],
            },
          },
        ],
      },
      true,
    );
    const onPointer = (e: { axesInfo?: { value: number }[] }) => {
      const v = e.axesInfo?.[0]?.value;
      useStore.getState().setHoverIndex(typeof v === 'number' ? v : null);
    };
    c.on('updateAxisPointer', onPointer as never);
    const zr = c.getZr();
    const onOut = () => useStore.getState().setHoverIndex(null);
    const onClick = (ev: { offsetX: number; offsetY: number }) => {
      const p = c.convertFromPixel({ seriesIndex: 3 }, [ev.offsetX, ev.offsetY]) as number[] | undefined;
      if (!p || !Number.isFinite(p[0])) return;
      const s = useStore.getState();
      s.setPlaying(false);
      s.setYmIndex(Math.round(p[0]), true);
    };
    zr.on('globalout', onOut);
    zr.on('click', onClick);
    const ro = new ResizeObserver(() => c.resize());
    ro.observe(box.current);
    return () => {
      c.off('updateAxisPointer', onPointer as never);
      zr.off('globalout', onOut);
      zr.off('click', onClick);
      ro.disconnect();
    };
    // ymIndex handled below without a rebuild
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, yms]);

  // Move the current-month marker only.
  useEffect(() => {
    const c = chart.current;
    if (!c || !data) return;
    const seam = yms.indexOf('2012-01');
    c.setOption({
      series: [
        {},
        {},
        {},
        {
          markLine: {
            data: [
              {
                xAxis: seam,
                lineStyle: { color: C.ice, width: 1, type: 'solid', opacity: 0.8 },
                label: { formatter: 'VIIRS joins', position: 'end', distance: 4, color: C.ice, fontFamily: C.font, fontSize: 13 },
              },
              { xAxis: ymIndex, lineStyle: { color: C.goldPale, width: 1, type: 'solid', opacity: 0.9 }, label: { show: false } },
            ],
          },
        },
      ],
    });
  }, [ymIndex, data, yms]);

  useEffect(() => () => chart.current?.dispose(), []);

  const hi = hoverIndex ?? ymIndex;
  const ym = yms[hi];
  const coef = meta?.model?.coefficients as Record<string, string> | undefined;
  const fittedOwn = coef?.[country]?.startsWith('refitted');

  return (
    <Panel title="Before and after" aside="12 months to date">
      <p className="num m-0 -mt-1 mb-1 text-[13px] text-text-map-2">
        {data && ym && data.harm[hi] != null ? (
          <>
            To {ymLong(ym)}: <span className="text-text">{fmtCD(data.naive[hi])}</span> naive,{' '}
            <span className="text-gold-pale">{fmtCD(data.harm[hi])}</span> harmonized
          </>
        ) : (
          'Hover the chart to compare'
        )}
      </p>
      <div ref={box} className="h-[150px] w-full" role="img" aria-label={`Naive and harmonized monthly fire activity for ${COUNTRY_NAMES[country] ?? country}, 2001 to the present`} />
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-text-map-2">
        <span className="flex items-center gap-1.5">
          <span aria-hidden className="h-[2px] w-4 bg-text-3" />
          Naive splice
        </span>
        <span className="flex items-center gap-1.5">
          <span aria-hidden className="relative h-2.5 w-4 rounded-[1px] bg-[rgba(245,184,61,0.22)]">
            <span className="absolute inset-x-0 top-1/2 h-[1.5px] -translate-y-1/2 bg-gold" />
          </span>
          Harmonized, 90% range
        </span>
      </div>
      <p className="m-0 mt-2 text-[13px] leading-snug text-text-map-2">
        {fittedOwn
          ? `Calibrated on ${COUNTRY_NAMES[country] ?? country}'s own 2012–2019 overlap, when both satellites flew.`
          : 'Calibrated on the 2012–2019 overlap, when both satellites flew.'}
      </p>
    </Panel>
  );
}
