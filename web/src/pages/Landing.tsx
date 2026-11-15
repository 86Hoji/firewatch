import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import Lenis from 'lenis';
import { SiteNav } from '../components/SiteNav';
import { SceneChart, stepStats, type SceneChartHandle } from '../components/landing/SceneChart';
import { useStore } from '../store';
import { frame, type CameraSpec } from '../map/MapEngine';
import { engine } from '../map/MapStage';
import { loadValidation, REGION_COVERAGE as COVERAGE, type Validation } from '../lib/validation';
import { COUNTRY_NAMES, loadAnomalies, type Anomaly, type CountryCode } from '../lib/data';
import { useMediaQuery, useSeries } from '../lib/hooks';
import { fmtCD, ymLong } from '../lib/format';

/** Width of the text column plus gutter, kept clear when framing the globe. */
const COLUMN_INSET = 520 + 28;
/** The country whose 2012 step the story shows: the clearest naive jump among the five. */
const STORY: CountryCode = 'UZB';
const STORY_CENTER: [number, number] = [64.2, 41.5];

const x2 = (v: number) => `×${v.toFixed(2)}`;
const ok = (...xs: unknown[]) => xs.every((x) => typeof x === 'number' && Number.isFinite(x));
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const smooth = (x: number) => x * x * (3 - 2 * x);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

function mixCam(a: CameraSpec, b: CameraSpec, t: number): CameraSpec {
  const k = smooth(clamp01(t));
  return {
    center: [lerp(a.center[0], b.center[0], k), lerp(a.center[1], b.center[1], k)],
    zoom: lerp(a.zoom, b.zoom, k),
    pitch: lerp(a.pitch, b.pitch, k),
    bearing: lerp(a.bearing, b.bearing, k),
  };
}

/** Camera looking at `target`, shifted so the target sits clear of the text column. */
function aim(target: [number, number], zoom: number, pitch: number, bearing: number, mobile: boolean): CameraSpec {
  const ppd = (512 * 2 ** zoom) / 360;
  const lng = target[0] - frame.left / 2 / ppd;
  // On phones the panel covers the top of the screen; put the target in the lower half.
  const lat = target[1] + (mobile ? (window.innerHeight * 0.24) / ppd : 0);
  return { center: [lng, lat], zoom, pitch, bearing };
}

export function Landing() {
  const shown = useStore((s) => s.introDone || s.reducedMotion);
  const reduced = useStore((s) => s.reducedMotion);
  const mobile = !useMediaQuery('(min-width: 768px)');
  const [v, setV] = useState<Validation | null>(null);
  const [event, setEvent] = useState<Anomaly | null>(null);
  const [phase, setPhase] = useState<1 | 2>(1);
  const [lit, setLit] = useState(false);
  const story = useSeries(STORY);
  const steps = useMemo(() => (story ? stepStats(story) : null), [story]);

  const wrap = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const s12 = useRef<HTMLElement>(null);
  const s3 = useRef<HTMLElement>(null);
  const chart = useRef<SceneChartHandle>(null);
  const lenis = useRef<Lenis | null>(null);

  useLayoutEffect(() => {
    frame.left = mobile ? 0 : COLUMN_INSET;
    engine?.reframe();
    return () => {
      frame.left = 0;
    };
  }, [mobile]);

  useEffect(() => {
    loadValidation().then(setV).catch(() => {});
    loadAnomalies()
      .then((a) => setEvent(a[0] ?? null))
      .catch(() => {});
  }, []);

  // Smooth scrolling (not under reduced motion).
  useEffect(() => {
    if (reduced || !wrap.current || !content.current) return;
    const l = new Lenis({ wrapper: wrap.current, content: content.current, autoRaf: true, lerp: 0.09 });
    lenis.current = l;
    return () => {
      l.destroy();
      lenis.current = null;
    };
  }, [reduced]);

  // Scroll drives the scenes: camera, chart morph, text and the event month.
  useEffect(() => {
    let raf = 0;
    let lastS = -1;
    let lastT = -1;
    let savedIndex: number | null = null;
    const tick = () => {
      raf = requestAnimationFrame(tick);
      const w = wrap.current;
      const a = s12.current;
      const b = s3.current;
      if (!w || !a || !b) return;
      const vh = w.clientHeight;
      const top = w.scrollTop;
      const s01 = clamp01((top - (a.offsetTop - vh)) / vh);
      const p = clamp01((top - a.offsetTop) / Math.max(1, a.offsetHeight - vh));
      const morphRaw = clamp01((p - 0.38) / 0.45);
      const morph = reduced ? (morphRaw > 0.5 ? 1 : 0) : smooth(morphRaw);
      const s23 = clamp01((top - (b.offsetTop - vh * 0.9)) / (vh * 0.9));

      if (morph !== lastT) {
        lastT = morph;
        chart.current?.setMorph(morph);
      }
      setPhase(p < 0.38 ? 1 : 2);

      // Scene 3: show the event's month on the map (and restore the landing month on the way back).
      const st = useStore.getState();
      if (event && st.introDone) {
        if (s23 > 0.55 && savedIndex == null) {
          const i = st.yms.indexOf(event.ym);
          if (i >= 0) {
            savedIndex = st.ymIndex;
            st.setPlaying(false);
            st.setYmIndex(i, true);
            if (!st.reducedMotion) engine?.setMonth(event.ym, 1400);
            setLit(true);
          }
        } else if (s23 < 0.35 && savedIndex != null) {
          st.setYmIndex(savedIndex, false);
          savedIndex = null;
          setLit(false);
        }
      }

      if (reduced || !engine?.ready) return;
      const s = s01 + morph + s23;
      if (Math.abs(s - lastS) < 1e-4) return;
      lastS = s;
      const home = engine.homeCamera();
      const z = home.zoom;
      const k1 = aim(STORY_CENTER, mobile ? 4.3 : Math.max(z + 0.9, 5), 48, -8, mobile);
      const k2 = aim(STORY_CENTER, mobile ? 4.4 : Math.max(z + 1.0, 5.1), 34, 8, mobile);
      const k3 = event ? aim([event.lon, event.lat], mobile ? 5.0 : 5.7, 58, 22, mobile) : k2;
      const cam = s <= 1 ? mixCam(home, k1, s) : s <= 2 ? mixCam(k1, k2, s - 1) : mixCam(k2, k3, s - 2);
      engine.setCamera(cam);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      if (savedIndex != null) useStore.getState().setYmIndex(savedIndex, false);
    };
  }, [event, reduced, mobile]);

  const toScenes = () => {
    const el = s12.current;
    if (!el) return;
    if (lenis.current) lenis.current.scrollTo(el, { duration: 1.6 });
    else wrap.current?.scrollTo({ top: el.offsetTop, behavior: reduced ? 'auto' : 'smooth' });
  };

  // Numbers are read from data/validation.json; a sentence whose values are missing is left out.
  // Exception: the interval coverage pair is not in validation.json (see REGION_COVERAGE).
  const uzNaive = v?.uz_test?.steps?.naive?.step_ratio;
  const uzLocal = v?.uz_test?.steps?.harmonized_local?.step_ratio;
  const baNaive = v?.burned_area?.KAZ?.naive?.step_given_burned_area?.step_factor;
  const baHarm = v?.burned_area?.KAZ?.harmonized?.step_given_burned_area?.step_factor;
  const proofs = [
    <>
      Tested on regions the model never saw, the 90% ranges contain the true value{' '}
      <span className="num text-gold-pale">{COVERAGE.after}%</span> of the time, up from{' '}
      <span className="num text-gold-pale">{COVERAGE.before}%</span> on the same data.
    </>,
    ok(uzNaive, uzLocal) && (
      <>
        In Uzbekistan the naive record jumps <span className="num text-gold-pale">{x2(uzNaive!)}</span> at 2012; ours
        moves <span className="num text-gold-pale">{x2(uzLocal!)}</span>.
      </>
    ),
    ok(baNaive, baHarm) && (
      <>
        Against MODIS burned area, an independent product, the naive record steps{' '}
        <span className="num text-gold-pale">{x2(baNaive!)}</span> at 2012; the harmonized one stays continuous at{' '}
        <span className="num text-gold-pale">{x2(baHarm!)}</span>.
      </>
    ),
  ].filter(Boolean);

  const fade = (on: boolean) => ({
    opacity: on ? 1 : 0,
    transition: reduced ? 'none' : 'opacity 280ms var(--ease)',
  });
  const storyName = COUNTRY_NAMES[STORY];

  return (
    <div className="pointer-events-none fixed inset-0">
      <div ref={wrap} className="pointer-events-auto absolute inset-0 overflow-y-auto overscroll-contain [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div ref={content} className="relative px-[var(--gutter)] pb-[var(--gutter)]">
          <header className="pt-[22px]">
            <SiteNav />
          </header>

          {/* Hero */}
          <section className="flex min-h-[calc(100svh-70px)] items-center py-10">
            <div
              className="glass w-full rounded-[22px] px-6 py-7 md:w-[520px] md:px-9 md:py-9"
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
                  onClick={toScenes}
                  className="inline-flex h-11 items-center rounded-[6px] px-4 text-[15px] text-text-map-2 transition-colors duration-[160ms] hover:bg-white/5 hover:text-text"
                >
                  How it works
                </button>
              </div>
            </div>
          </section>

          {/* Scenes 1 and 2: the step, then the step disappears */}
          <section ref={s12} aria-label="The 2012 step" className="relative" style={{ height: reduced ? 'auto' : '300vh' }}>
            <div className={`${reduced ? '' : 'sticky top-[76px] md:top-[16vh]'} glass w-full rounded-[14px] px-6 py-6 md:w-[520px] md:px-8`}>
              <div className="grid [&>*]:col-start-1 [&>*]:row-start-1">
                <div style={fade(phase === 1)} aria-hidden={phase !== 1}>
                  <h2 className="m-0 text-[22px] font-medium leading-[1.3] text-text">The fires didn’t change. The satellite did.</h2>
                  <p className="m-0 mt-3 text-[15px] leading-[1.6] text-text-map-2">
                    In 2012 {storyName}’s fire count jumped{' '}
                    {steps ? <span className="num text-text">×{steps.naive.toFixed(1)}</span> : 'several times'} overnight. VIIRS
                    had joined MODIS.
                    {steps && (
                      <>
                        {' '}
                        MODIS alone, flying the whole time, saw <span className="num text-text">×{steps.modis.toFixed(1)}</span>.
                      </>
                    )}
                  </p>
                </div>
                <div style={fade(phase === 2)} aria-hidden={phase !== 2}>
                  <h2 className="m-0 text-[22px] font-medium leading-[1.3] text-text">The step disappears.</h2>
                  <p className="m-0 mt-3 text-[15px] leading-[1.6] text-text-map-2">
                    During the eight years both satellites flew, we learn how VIIRS sees compared with MODIS, then carry that
                    back to 2001.
                    {steps && (
                      <>
                        {' '}
                        The harmonized record moves <span className="num text-gold-pale">×{steps.harmonized.toFixed(1)}</span> at
                        2012.
                      </>
                    )}
                  </p>
                </div>
              </div>
              <div className="mt-5">
                <SceneChart ref={chart} cc={STORY} />
              </div>
              <p className="m-0 mt-2 text-[13px] text-text-map-2">
                {storyName}, cell-days of fire per year. Ratios compare 2012–2016 with 2007–2011.
              </p>
            </div>
          </section>

          {/* Scene 3: the top event, on today's scale */}
          <section ref={s3} aria-label="One scale" className="relative" style={{ height: reduced ? 'auto' : '220vh' }}>
            <div className={`${reduced ? 'mt-6' : 'sticky top-[76px] md:top-[22vh]'} glass w-full rounded-[14px] px-6 py-6 md:w-[520px] md:px-8`}>
              <h2 className="m-0 text-[22px] font-medium leading-[1.3] text-text">
                Now a month in 2001 and a month in 2024 mean the same thing.
              </h2>
              {event && (
                <div className="mt-5 border-t border-[rgba(255,231,163,0.12)] pt-5">
                  <p className="display m-0 text-[32px] leading-[1.1] text-text">{event.title}</p>
                  <p className="num m-0 mt-3 flex flex-wrap items-baseline gap-x-2 text-[15px] text-text-map-2">
                    <span>{ymLong(event.ym)}</span>
                    <span
                      className="text-[32px] leading-none text-gold-pale"
                      style={{ textShadow: lit && !reduced ? '0 0 24px rgba(245,184,61,0.55)' : 'none', transition: 'text-shadow 900ms var(--ease)' }}
                    >
                      {fmtCD(event.value)}
                    </span>
                    <span>cell-days in one area of {event.region}</span>
                  </p>
                  {Number(event.ym.slice(0, 4)) < 2012 && (
                    <p className="m-0 mt-3 text-[15px] leading-[1.6] text-text-map-2">
                      Only MODIS was flying then. On the harmonized scale this month reads as VIIRS would have seen it.
                    </p>
                  )}
                </div>
              )}
            </div>
          </section>

          {/* Proof */}
          <section aria-labelledby="proof" className="glass mt-6 w-full rounded-[14px] px-6 py-6 md:w-[520px] md:px-8">
            <h2 id="proof" className="m-0 text-[17px] font-medium text-text">
              Why you can trust it
            </h2>
            {proofs.length > 0 && (
              <ul className="m-0 mt-4 flex list-none flex-col gap-3 p-0 text-[15px] leading-[1.6] text-text">
                {proofs.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            )}
            <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-[15px]">
              <Link to="/evidence" className="text-gold underline-offset-4 hover:underline">
                See the evidence
              </Link>
              <Link to="/method" className="text-text-map-2 underline-offset-4 hover:text-text hover:underline">
                How the record is made
              </Link>
            </div>
          </section>

          <footer className="mt-10 max-w-[520px] px-1 pb-4 text-[13px] leading-[1.55] text-text-map-2">
            <p className="m-0">Made by the Firewatch team for NASA Space Apps 2026. Pipeline baseline by Elbek.</p>
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
