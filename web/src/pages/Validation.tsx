import { useEffect, useState, type ReactNode } from 'react';
import { SiteNav } from '../components/SiteNav';
import { loadValidation, type Validation as V } from '../lib/validation';

const NAMES: Record<string, string> = {
  KAZ: 'Kazakhstan',
  UZB: 'Uzbekistan',
  TKM: 'Turkmenistan',
  KGZ: 'Kyrgyzstan',
  TJK: 'Tajikistan',
  PRT: 'Portugal',
  AUS: 'Australia',
  BRA: 'Brazil',
  USA: 'United States',
  IND: 'India',
};
const x = (v: number) => `×${v.toFixed(2)}`;
const pct = (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`;
const abs = (v: number) => `${v.toFixed(1)}%`;

function Table({ head, rows, caption }: { head: string[]; rows: ReactNode[][]; caption: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="num w-full min-w-[520px] border-collapse text-left text-[15px]">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {head.map((h, i) => (
              <th key={h} scope="col" className={`border-b border-line pb-2 pr-4 text-[13px] font-normal text-text-2 ${i ? 'text-right' : ''}`}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, k) => (
            <tr key={k}>
              {r.map((c, i) => (
                <td key={i} className={`border-b border-line py-2.5 pr-4 ${i ? 'text-right' : 'text-text'}`}>
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Section({ title, lede, children }: { title: string; lede: string; children: ReactNode }) {
  return (
    <section className="mt-16">
      <h2 className="display m-0 text-[32px] leading-[1.1] text-text">{title}</h2>
      <p className="m-0 mt-3 max-w-[68ch] text-[15px] leading-[1.6] text-text-2">{lede}</p>
      <div className="mt-6">{children}</div>
    </section>
  );
}

const Ci = ({ lo, hi }: { lo: number; hi: number }) => (
  <span className="text-text-3">
    {' '}
    ({lo.toFixed(2)}–{hi.toFixed(2)})
  </span>
);

export function Validation() {
  const [v, setV] = useState<V | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    loadValidation().then(setV).catch(() => setErr(true));
    window.scrollTo(0, 0);
  }, []);

  const stepRows = (s: V['uz_test']['steps']) =>
    (
      [
        ['Naive splice', s.naive],
        ['MODIS alone', s.modis_only],
        ['Kazakhstan calibration', s.harmonized],
        ['Local calibration', s.harmonized_local],
      ] as const
    ).map(([label, st]) => [
      label,
      x(st.step_ratio),
      <>
        {x(st.monthly_step.step_factor)}
        <Ci lo={st.monthly_step.ci_low} hi={st.monthly_step.ci_high} />
      </>,
    ]);

  return (
    <div className="fixed inset-0 z-10 overflow-y-auto bg-deep">
      <div className="mx-auto max-w-[920px] px-[var(--gutter)] pb-24 pt-[22px]">
        <header>
          <SiteNav onMap={false} />
        </header>

        <h1 className="display m-0 mt-16 text-[48px] leading-[1.05] tracking-[-0.01em] text-text md:text-[76px]">The evidence</h1>
        <p className="m-0 mt-5 max-w-[68ch] text-[17px] leading-[1.6] text-text-2">
          We fitted the calibration on Kazakhstan’s 2012–2019 overlap, when MODIS and VIIRS both flew, and tested it where
          it had never seen data. Every number below comes from the pipeline’s own validation file.
        </p>

        {err && <p className="mt-10 text-coral">The validation file could not be loaded.</p>}
        {!v && !err && <p className="mt-10 text-text-2">Loading the numbers.</p>}

        {v && (
          <>
            <Section
              title="Does the 2012 step disappear?"
              lede="How much the record jumps when VIIRS joins in 2012: the ratio of mean monthly activity after to before, and a monthly model of the step with its 95% interval. A value near 1 means no step. MODIS alone shows what real change in the fires looks like."
            >
              <h3 className="m-0 mb-3 text-[15px] font-medium text-text">Uzbekistan, never used in fitting</h3>
              <Table caption="2012 step in Uzbekistan" head={['Series', 'Step ratio', 'Monthly step (95% interval)']} rows={stepRows(v.uz_test.steps)} />
              <h3 className="m-0 mb-3 mt-8 text-[15px] font-medium text-text">Turkmenistan, the hardest case</h3>
              <Table caption="2012 step in Turkmenistan" head={['Series', 'Step ratio', 'Monthly step (95% interval)']} rows={stepRows(v.tm_stress.steps)} />
            </Section>

            <Section
              title="Does the calibration travel?"
              lede="Monthly error as a share of mean activity, on the 2012–2019 overlap, using Kazakhstan’s coefficients as they are and refitted on each country’s own overlap. The method travels; the coefficients do not, so every country on the map uses its own fit."
            >
              <Table
                caption="Calibration transfer by country"
                head={['Country', 'Error, Kazakhstan fit', 'Error, local fit', 'Bias, local fit', 'VIIRS ÷ MODIS']}
                rows={Object.entries(v.transfer).map(([cc, t]) => [
                  NAMES[cc] ?? cc,
                  abs(t.overlap_as_is.mae_pct_of_mean),
                  abs(t.overlap_local.mae_pct_of_mean),
                  pct(t.overlap_local.bias_total_pct),
                  x(t.ratio_observed),
                ])}
              />
            </Section>

            <Section
              title="Checked against burned area"
              lede="MODIS burned area (MCD64A1) is an independent product with no 2012 change. Holding burned area fixed, a continuous fire record should show no step: the 95% interval should include 1."
            >
              <Table
                caption="2012 step given burned area"
                head={['Country', 'Naive splice', 'Harmonized', 'Continuous']}
                rows={Object.entries(v.burned_area).map(([cc, b]) => {
                  const h = (b.harmonized_local ?? b.harmonized).step_given_burned_area;
                  return [
                    NAMES[cc] ?? cc,
                    <>
                      {x(b.naive.step_given_burned_area.step_factor)}
                      <Ci lo={b.naive.step_given_burned_area.ci_low} hi={b.naive.step_given_burned_area.ci_high} />
                    </>,
                    <>
                      {x(h.step_factor)}
                      <Ci lo={h.ci_low} hi={h.ci_high} />
                    </>,
                    h.ci_includes_1 ? <span className="text-gold-pale">Yes</span> : <span className="text-text-2">No</span>,
                  ];
                })}
              />
            </Section>

            <Section
              title="Small fire countries, by year"
              lede="Kyrgyzstan and Tajikistan have only a few hundred fire cell-days a year, so only annual totals are meaningful. Raw MODIS misses most of what VIIRS sees; the harmonized totals are close."
            >
              <Table
                caption="Annual accuracy in Kyrgyzstan and Tajikistan"
                head={['Country', 'Annual error', 'Bias, harmonized', 'Bias, raw MODIS', 'Correlation']}
                rows={Object.entries(v.annual).map(([cc, a]) => [
                  NAMES[cc] ?? cc,
                  abs(a.mae_pct_of_mean),
                  pct(a.bias_total_pct),
                  pct(a.naive_modis_bias_pct),
                  a.pearson_r.toFixed(2),
                ])}
              />
            </Section>
          </>
        )}

        <footer className="mt-20 border-t border-line pt-6 text-[13px] leading-[1.55] text-text-2">
          Made by the Firewatch team for NASA Space Apps 2026. Pipeline baseline by Elbek. Fire detections from NASA FIRMS
          (MODIS and VIIRS); night lights from NASA GIBS Black Marble; burned area from MODIS MCD64A1.
        </footer>
      </div>
    </div>
  );
}
