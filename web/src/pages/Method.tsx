import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { SiteNav } from '../components/SiteNav';
import { CalibrationScatter, FlareVsField, OneSeries, PointsToHexes } from '../components/method/Illustrations';
import { loadValidation, REGION_COVERAGE, type Validation } from '../lib/validation';
import { COUNTRY_NAMES } from '../lib/data';

const pct0 = (v: number) => `${Math.round(v)}%`;
const N = ({ children }: { children: ReactNode }) => <span className="num text-text">{children}</span>;

function Step({ n, title, children, art, caption }: { n: number; title: string; children: ReactNode; art: ReactNode; caption: string }) {
  return (
    <section className="grid gap-8 border-t border-line py-14 md:grid-cols-[minmax(0,1fr)_380px] md:gap-14">
      <div className="max-w-[52ch]">
        <p className="display m-0 text-[48px] leading-none text-ember" aria-hidden>
          {n}
        </p>
        <h2 className="m-0 mt-4 text-[22px] font-medium leading-[1.3] text-text">{title}</h2>
        <div className="mt-4 flex flex-col gap-4 text-[17px] leading-[1.6] text-text-2 [&_p]:m-0">{children}</div>
      </div>
      <figure className="m-0 self-center">
        {art}
        <figcaption className="mt-3 text-[13px] leading-[1.5] text-text-2">{caption}</figcaption>
      </figure>
    </section>
  );
}

export function Method() {
  const [v, setV] = useState<Validation | null>(null);
  useEffect(() => {
    loadValidation().then(setV).catch(() => {});
    window.scrollTo(0, 0);
  }, []);
  const kz = v?.transfer?.KAZ;
  const flares = v?.flare_load;
  const mask = flares?.KAZ?.mask_test;

  return (
    <div className="fixed inset-0 z-10 overflow-y-auto bg-deep">
      <div className="mx-auto max-w-[1040px] px-[var(--gutter)] pb-24 pt-[22px]">
        <header>
          <SiteNav onMap={false} />
        </header>

        <h1 className="display m-0 mt-16 text-[48px] leading-[1.05] tracking-[-0.01em] text-text md:text-[76px]">How the record is made</h1>
        <p className="m-0 mb-16 mt-5 max-w-[60ch] text-[17px] leading-[1.6] text-text-2">
          Five steps take raw satellite detections to one monthly series per country and region, comparable from 2001 to
          today.
        </p>

        <Step
          n={1}
          title="Start from fire points"
          art={<PointsToHexes snap={false} />}
          caption="The same three fires. Illustrative, not to scale."
        >
          <p>
            NASA FIRMS lists every hot pixel a satellite sees. MODIS has flown since 2000 with pixels about 1 km across;
            VIIRS joined in 2012 with pixels of 375 m. Over the same fire, VIIRS reports many more, smaller points.
          </p>
          <p>Count points directly and 2012 looks like the year Central Asia caught fire.</p>
        </Step>

        <Step
          n={2}
          title="Count hexagon-days, not points"
          art={<PointsToHexes snap />}
          caption="Each point moves into its hexagon; a hexagon counts once per day, whatever the number of points in it."
        >
          <p>
            We place every point in an H3 hexagon of about 5 km² and count each hexagon once for every day it burned. That
            unit, the cell-day, is far less sensitive to pixel size: ten VIIRS points and one MODIS point in the same
            hexagon on the same day both count as one.
          </p>
          <p>It narrows the gap between the satellites but does not close it. VIIRS still sees fires MODIS misses.</p>
        </Step>

        <Step
          n={3}
          title="Remove gas flares and industry"
          art={<FlareVsField />}
          caption="A flare is hot every month of the year; a field burns in spring and around harvest."
        >
          <p>
            Gas flares, steel plants and refineries look like fires to a satellite, and they burn all year. Hexagons that
            are hot in nearly every month are masked, so only real landscape fires remain.
          </p>
          {flares && (
            <p>
              The mask removes{' '}
              {(['KAZ', 'UZB', 'TKM'] as const)
                .filter((c) => flares[c])
                .map((c, i, arr) => (
                  <span key={c}>
                    <N>{pct0(flares[c].static_share_removed_pct)}</N> of confident detections in {COUNTRY_NAMES[c]}
                    {i < arr.length - 2 ? ', ' : i === arr.length - 2 ? ' and ' : ''}
                  </span>
                ))}
              .
              {mask && (
                <>
                  {' '}
                  Checked against FIRMS’ own labels, it catches <N>{pct0(mask.recall * 100)}</N> of industrial detections, and{' '}
                  <N>{pct0(mask.precision * 100)}</N> of what it removes is industrial.
                </>
              )}
            </p>
          )}
        </Step>

        <Step
          n={4}
          title="Calibrate on 2012–2019"
          art={<CalibrationScatter ratio={kz?.ratio_observed ?? null} />}
          caption="Kazakhstan, every month of 2012–2019. Dashed line: the overall ratio of VIIRS to MODIS."
        >
          <p>
            For eight years both satellites flew. Month by month we learn how many cell-days VIIRS records for a given
            MODIS count, with a Poisson model fitted to each country’s own overlap.
          </p>
          {kz && (
            <p>
              In Kazakhstan VIIRS sees <N>×{kz.ratio_observed.toFixed(2)}</N> as many cell-days as MODIS. The model is off
              by <N>{kz.overlap_as_is.mae_pct_of_mean.toFixed(1)}%</N> a month on the overlap and{' '}
              <N>{kz.holdout_as_is.mae_pct_of_mean.toFixed(1)}%</N> on 2020 onward, months it never saw.
            </p>
          )}
        </Step>

        <Step
          n={5}
          title="One series, with a 90% range"
          art={<OneSeries />}
          caption="Kazakhstan by year. Grey: the naive splice. Gold: harmonized, with its 90% range."
        >
          <p>
            Before 2012 each month is the calibrated MODIS estimate with a 90% range around it. From 2012 it is VIIRS as
            observed. The step disappears, and every number on the map carries its range.
          </p>
          <p>
            Tested on regions the model never saw, the range contains the true value <N>{REGION_COVERAGE.after}%</N> of the
            time, up from <N>{REGION_COVERAGE.before}%</N> on the same data
            {kz?.holdout_as_is.coverage != null && (
              <>
                ; on Kazakhstan’s months after 2019, <N>{pct0(kz.holdout_as_is.coverage * 100)}</N>
              </>
            )}
            .
          </p>
        </Step>

        <div className="flex flex-wrap gap-x-6 gap-y-2 border-t border-line pt-10 text-[15px]">
          <Link to="/evidence" className="text-gold underline-offset-4 hover:underline">
            See the evidence
          </Link>
          <Link to="/explore" className="text-text-2 underline-offset-4 hover:text-text hover:underline">
            Open the map
          </Link>
        </div>
      </div>
    </div>
  );
}
