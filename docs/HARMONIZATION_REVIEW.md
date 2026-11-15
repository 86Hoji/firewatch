# Harmonization review: MODIS → VIIRS (after phase C3, updated with checks on real data)

A review of the method that puts MODIS on the VIIRS S-NPP scale: what follows best practice, where the main product
(the 2000–2011 series) is at risk, and what to improve in the project as a whole. Written against `main` at
`80a8a68`; updated on 2026-11-15 with results on the real data (§2.1, §6). Numbers come from `reports/` or are
recomputed from the exported series and `cell_month_all.parquet`.

---

## 0. Verdict

**The engineering and validation are well above a typical hackathon project:** cell-days instead of points, a stable
reference scale, calibration in a window without orbit drift, a model-selection protocol fixed before the run,
cross-fitted conformal intervals, a regression check at 1e-9, and weak spots stated openly.

**The main risk was in the product, not in the code.** The 2000–2011 series is the model applied beyond the data it
was fitted on, and none of the tests T1–T4 checked that. The choice of model form moves 2002–2004 by 11–20%, while the
published yearly 90% interval is about ±8%.

> **Update (2026-11-15, real data).** The extrapolation test T5 **largely removes this risk**. On the busier years the
> chosen model C2 errs by 7.3% with +3.7% bias; a constant ratio (C0) gives 10.7% and +10.4%, and would raise the
> 2003–2011 level by almost as much (+8.9%). The data reject C0, not C2 (§2.1, §6.2). Only months far outside the
> calibration range remain a caveat.

| aspect | rating | in short |
|---|---|---|
| Unit (H3 cell-days) | ★★★★★ | Removes about half of the resolution gap before any statistics |
| Reference scale (S-NPP only, NOAA-20 only for outages) | ★★★★★ | The right stable reference |
| Calibration window and test direction | ★★★★☆ | 2012–2019 is drift-free; T1 tests "backwards in time"; T5 now tests "beyond the range" |
| Model form | ★★★★☆ | The power law passed T5 on real data; the constant ratio failed (§2.1) |
| Spatial fidelity | ★★☆☆☆ | The map is MODIS times one number per country and season (§2.2) |
| Intervals | ★★★★☆ | Conformal and cross-fitted, but they do not cover the whole chain (§2.4) |
| Independent check before 2012 | ★★★☆☆ | Burned-area test (C4) with a MODIS-only control; it can show the seam is gone, not ±10% accuracy (§2.3, §6.4) |
| Reproducibility and transparency | ★★★★☆ | Excellent audit trail; no CI or pinned environment yet (§3) |

---

## 1. What is done well (keep)

1. **H3 res-7 cell-days.** The naive 2012 jump is ×2.81 in points and ×1.63 in cell-days: half of the resolution gap
   goes away without any model.
2. **Target = S-NPP only**; NOAA-20 only fills outage days, with its own coefficient, so there is no second seam at
   2018 (NOAA-20 launch).
3. **Calibration 2012–2019, holdout 2020+.** MODIS orbit drift is named and measured: Terra/Aqua cell-day ratio
   0.86–1.02 until 2021, then 1.36 → 0.62.
4. **T1 backcast (2016–19 → 2012–15)** reproduces the real direction of use: backwards in time.
5. **Selection protocol** with a parsimony rule (within 0.5 points the model with fewer parameters wins), which guards
   against tuning to the result.
6. **Intervals at the level predicted (C3).** Region coverage of the 90% interval went from 50% to 92% (current
   reports), all cross-fitted.
7. **One source of truth:** [`reports/model_card.json`](../reports/model_card.json); step 06 refuses to run on a
   mismatch.
8. **Regression checks and audit trail.** For example, FIRMS re-labelling MODIS 6.03/6.2 was found and explained, not
   hidden.

---

## 2. Harmonization issues (most important first)

### 2.1 🟠 The 2000–2011 series is extrapolation (now tested by T5)

**Fact.** MODIS gave 51–57k cell-days a year in 2002–2004; the busiest calibration year has 36k (2017). Peak months
lie even further out.

| year | MODIS cell-days | harmonization multiplier | with a constant 1.80 (2012–19 mean) | difference |
|---|---|---|---|---|
| 2002 | 53,732 | 1.59 | ≈96,700 | **+13%** |
| 2003 | 56,768 | 1.50 | ≈102,100 | **+20%** |
| 2004 | 51,477 | 1.62 | ≈92,600 | **+11%** |
| 2008 | 41,862 | 1.70 | ≈75,300 | +6% |
| 2011 | 13,330 | 1.92 | ≈24,000 | −6% |

Annual multipliers in 2012–2019 lie between 1.67 and 2.07. C2 (`exp(a)·(M+1)^b`, b < 1) lowers the multiplier as
activity grows and gives 1.50 in 2003, below anything observed. The published 2003 interval is 79–92k (±8%), so the
difference between two plausible models (C0 and C2) was larger than the interval. (Rough: annual ratios, while C0 is
calibrated per month.)

**Why T1–T4 do not catch it.** T1 fits 2016–19 (12–36k a year) and predicts 2012–15 (9.5–30k): interpolation. T3 and
T4 stay inside 2012–2019. T2 tests quieter years and is distorted by orbit drift.

**Code note.** C2 is fitted **per season**, not per month. Log-link models need at least `loglog_min_points = 12`
points per stratum and a month has 8 in 2012–2019, so `models.fit` and `calib._resolve` always fall back to the season
(24 points); the ratio model C0 is fitted per month. Checked for both implementations. So C2 is 4 power laws with
2 parameters each, and within a season the seasonal cycle enters only through M. [AUDIT.md](AUDIT.md) §2 says
"for each calendar month … on the 8 yearly values", which is not exact.

**Done (in `main`).** [`pipeline/experiments.py`](../pipeline/experiments.py) now reports:
- **T5:** for each calendar month, fit on the 2012–2019 years whose MODIS total is at or below that month's 75th
  percentile, test on the two busiest years. Reported only; the protocol and the score are unchanged.
- **`range_stats`:** share of 2003–2011 months above the same month's calibration maximum, with median and maximum
  ratio; per-month flags in [`reports/extrapolation_flags.json`](../reports/extrapolation_flags.json).
- **`sensitivity`:** 2003–2011 annual totals of all 8 candidates vs the selected one (structural uncertainty). Years
  before July 2002 are excluded: they need the Terra → Terra∪Aqua bridge.
- **`score_bootstrap`:** paired bootstrap over years of the selection score (§2.6).

Unit tests on synthetic data live on the branch `feat/t5-extrapolation-test` (`tests/test_extrapolation.py`).

**Result on real data** (each country fitted on its own 2012–2019 data; exported country series after `33b7d7d`,
values rounded to 3 significant digits):

| country | T5 C0: MAE / bias | T5 C1 | T5 C2 | how far the test leaves the range (median) | 2003–11: C0 vs C2 | 2003–11 months above calibration max |
|---|---|---|---|---|---|---|
| **KAZ** | 10.7% / **+10.4%** | 8.1% / +3.1% | **7.3% / +3.7%** | ×1.32 | **+8.9%** | 32% |
| UZB | 38.9% / +35.9% | 20.9% / +0.5% | 17.7% / −1.6% | ×1.53 | +3.1% | 16% |
| TKM | 23.9% / +15.0% | 13.7% / −7.3% | 13.4% / −6.6% | ×1.45 | +2.5% | 16% |
| KGZ | 27.0% / +4.2% | **19.5% / +3.4%** | 24.5% / +1.8% | ×1.36 | +0.5% | 40% |
| TJK | 68.5% / +68.0% | 42.0% / +39.7% | 29.7% / +23.3% | ×1.74 | +25.1% | 23% |
| PRT | 22.1% / +15.8% | 20.6% / +0.8% | 16.3% / −10.5% | ×1.68 | +3.6% | 10% |
| AUS | 9.4% / +7.8% | 8.1% / −2.9% | 5.4% / −0.9% | ×1.23 | +0.1% | 4% |
| BRA | 6.4% / +5.8% | 6.8% / +1.2% | 6.5% / +0.5% | ×1.22 | +5.6% | 32% |
| USA | 14.7% / +13.7% | 10.9% / −3.0% | 10.9% / −2.5% | ×1.14 | +2.4% | 13% |
| IND | 8.9% / +6.6% | 9.0% / +2.1% | 8.1% / +2.6% | ×1.21 | −1.7% | 7% |

**Conclusions** (these correct the first estimate in this section):
- On the test that mimics applying the model to busier years, **C2 is best or within 0.1 points of the best in 9 of
  10 countries**. The exception is Kyrgyzstan, where C1 is more accurate (19.5% vs 24.5%) though C2 has less bias.
  **C0 over-predicts in all 10 countries** (+4…+68%).
- In Kazakhstan C0's T5 over-prediction (+10.4%) almost equals how much C0 would raise the 2003–2011 level (+8.9%).
  The C0–C2 difference before 2012 is C0's error, not uncertainty.
- C1 and C2 give nearly the same level before 2012 (−0.1% in Kazakhstan), so the choice between the two power laws
  does not move the product.
- Month by month the excursion is smaller than annual totals suggest: 32% of 2003–2011 months in Kazakhstan exceed
  the calibration maximum, median ×0.66 of it. Large ratios (up to ×10–17) are months with almost no fire in the
  calibration years (small absolute numbers).
- **Two implementations agree.** C2 in `models.py` and the published series from `calib.py` differ by −0.13…+0.14% in
  Kazakhstan's 2003–2011 annual totals, which is the export rounding.

**Still open:** T5 tests excursions up to about ×1.3–1.7. For months much further out, capping the multiplier at the
edge of the calibration range remains a recommendation.

### 2.2 🔴 The map is MODIS times one number

The multiplier comes from the country total of the month and is the same for every cell. C3 fixed the interval width
for regions, not the bias: median region error 13.5% (current reports), region biases from −15% to +13.5% (phase C3).

**Best practice: a hierarchical model with partial pooling.**

```
V_rm ~ NegBin(μ_rm, φ)
log μ_rm = a_month(m) + b · log(M_rm + 1) + u_region + β · x_rm
u_region ~ N(0, σ²)                       # shrinks to the country when data are sparse
x_rm: features MODIS sees before 2012 too:
      points per cell-day (p_modis / n_modis) as a fire-size proxy,
      median FRP, low-confidence share, night share, land cover (MCD12Q1), latitude
```

- x is observable before 2012, so extrapolation becomes checkable (compare x in 2001–11 vs 2012–19).
- Pooling the 10 countries and **leave-one-country-out** is the strongest transfer test (phase C4).
- Model seasonality as a smooth cyclic function or a month random effect instead of the hard month → season →
  country fallback (which for C2 always lands on the season, §2.1).

A first implementation was tried and **did not beat C2 on real data** (§6.3).

### 2.3 🟠 Independent check of the product before 2012

All model tests compare with VIIRS, which does not exist before 2012, so the "harmonized step ×0.92" is largely true
by construction (AUDIT §5.5). An independent check needs another data source.

**Burned area (MCD64A1).** [`data/external/burned_area.csv`](../data/external/burned_area.csv) (monthly, KAZ/UZB/TKM/KGZ/TJK)
is now used by the C4 package (`07b`): the step at 2012 in fire cell-days given burned area. MCD64A1 is also MODIS,
but a different algorithm (burn scars, not thermal anomalies), and it does not depend on the VIIRS seam.

A first annual check (Kazakhstan, cell-days per burned hectare, 2012–2019 vs 2003–2011, geometric means, 5,000
bootstrap draws over years):

| series | after / before 2012 | 90% interval |
|---|---|---|
| MODIS alone (one sensor, no seam) | 1.07 | 0.84–1.36 |
| naive splice | **1.96** | 1.51–2.55 |
| harmonized | 1.16 | 0.89–1.52 |

The naive jump is confirmed and removed; annual data cannot tell C2 from a constant ratio (±30% interval). The monthly
test in `07b` agrees (Kazakhstan ×1.16, 0.88–1.53). The MODIS-only control and its limits are in §6.4.

**Next:** sensor-independent products — ESA FireCCILT11 (AVHRR-LTDR, 1982–2018), Landsat 30 m burned area (e.g.
GABAM) — and known events before 2012, not only after 2022.

### 2.4 🟠 Uncertainty does not cover the whole chain

The interval comes only from the leave-one-year-out residuals of the main model. Not included:

| source | where | effect |
|---|---|---|
| Terra → Terra∪Aqua bridge (Nov 2000 – Jun 2002, 20 months) | `calib.modis_effective` | interval too narrow for those months |
| Model structure (§2.1) | — | now small between C1 and C2; C0 rejected by T5 |
| Only 8 calibration years | bootstrap over years | unstable tails of the coefficient distribution |
| S-NPP outages 2012–2017 left as zero (no NOAA-20 yet) | `03_grid` | calibration target and multiplier slightly low |
| Yearly interval = sum of monthly 90% bounds | `07_validate.jump_test`, API `/yearly` | not a 90% annual interval; on real data it covers 99% of held-out years at about twice the needed width (§6) |

**Best practice: a Monte Carlo ensemble.** 200–500 members of the whole series (coefficient bootstrap → Terra bridge →
NOAA-20 coefficient → conformal residual), stored per region × month, so any aggregate (year, area, trend, rank) gets
honest quantiles. A version exists on a side branch; on real country totals its annual interval covers 82% at half
the width, so it needs calibration before use.

### 2.5 🟠 Seasons: winter and spring

Holdout by season: winter bias +26%, spring coverage 56% at a nominal 90% (KZ report, §1). Spring is the season of
farm burning, with a different fire-size distribution — the same cause as in §2.2. Per-season (Mondrian) conformal
intervals and a fire-size feature would address it.

### 2.6 🟠 Metrics and model selection

- **MAE as % of the mean is driven by peak months.** Add log-scale errors (MASE or `|log(1+a) − log(1+p)|`) and, for
  intervals, an interval/Winkler score or CRPS, which reward both coverage and width.
- **Score differences had no uncertainty.** *Done:* `score_bootstrap` gives the interval of each candidate's score
  difference from the winner and its share of wins ("How sure is the choice?" in `model_comparison.md`). On real data
  C2 wins 62% of draws and C1 32% (difference interval includes 0); C0 is significantly worse (§6.2).
- **The step test over-rejects.** `metrics.step_test` uses Newey-West with 12 lags on ~200 monthly points; on
  synthetic noise without a step it excludes 1 in about 9% of cases at a nominal 5% (up to ~18% when months are
  dropped). A CI that barely excludes 1 is weak evidence. Fix: lags `floor(4·(n/100)^(2/9))` or a block bootstrap over
  years.
- **Selection optimism.** T1, T3 and T4 both select the model and report its quality; say so, or use a nested scheme.
- **T3 inconsistency.** The model is fitted on country totals *without* the region, while the multiplier is evaluated
  at the *whole* country total; for b ≠ 1 this is a small shift. Document it or evaluate at the training total.
- **Interval label.** `model_comparison.md` called the intervals "negative binomial at the predicted level"; they are
  empirical conformal quantiles by bin ([`intervals.py`](../pipeline/intervals.py)). *Fixed:* "conformal, sized at
  the predicted level".

### 2.7 🟡 Sensitivity to definitions

- **H3 resolution:** how the multiplier and the 2012 step change at res 6 and 8 is not tested yet.
- **Scan angle:** the MODIS pixel grows to about 2 × 4.8 km at the swath edge while VIIRS 375 m stays under ~0.8 km,
  and detection depends on it. FIRMS has `scan`/`track`; use them as a feature or test near-nadir data only. Code for
  both checks exists on a side branch; it needs the cleaned points or raw zips.
- **UTC dates:** a night pass near local midnight falls on the neighbouring day. No bias between sensors, but worth a
  line in the method.

---

## 3. The project as a whole

### 3.1 Product and presentation

| item | state | next |
|---|---|---|
| Root README | done: summary, three numbers, limitations, run, credits, generated from the reports | keep it generated (`python -m pipeline.readme_numbers`) |
| Website `web/` | done (MapLibre + deck.gl, validation page) | — |
| Dataset | inside the pipeline only | publish the series (Parquet/CSV, data dictionary, license, DOI) with the model version |
| Uncertainty on the site | low/high bounds | ensemble quantile fan; mark extrapolated months (`reports/extrapolation_flags.json`) |

### 3.2 Engineering

- **CI:** GitHub Actions with `pytest` and `ruff` on every PR (prepared on a side branch, not merged).
- **Environment:** pin Python 3.11–3.12 and a lock file (uv). On Python 3.15 `h3` has no wheels and installation fails.
- **Data provenance:** `manifest.csv` holds only the request id; add the archive sha256, download date and FIRMS
  version.
- **Two model implementations** (`models.py` for selection, `calib.py` for the product): add an equivalence test or
  merge them. On real data they agree to export rounding (§2.1).
- **Tests:** no end-to-end test on a small real sample; no tests for `07_validate` and `experiments`.
- **API:** `on_event` is deprecated (use `lifespan`); `CORS *`; SQL built with f-strings (ints, but parameters are
  safer).

### 3.3 Roadmap

| # | step | status |
|---|---|---|
| 1 | T5 extrapolation test (§2.1) | done; capping the multiplier still open |
| 2 | Burned-area seam test (§2.3) | done in `07b`, with a MODIS-only control |
| 3 | Interval label, README, website (§2.6, §3.1) | done |
| 4 | Hierarchical model with fire-size features, leave-one-country-out (§2.2) | tried, not better (§6.3) |
| 5 | Monte Carlo ensemble (§2.4) | side branch, needs calibration |
| 6 | H3 / scan-angle sensitivity (§2.7), FireCCILT11 (§2.3) | code on a side branch, needs raw data |
| 7 | CI, lock file, checksums, model equivalence test (§3.2) | side branch, not merged |

---

## 4. Fixed along the way

**The API summed per-cell intervals** (`sum(n_harm_low)` / `sum(n_harm_high)`), which
[`06_harmonize.py`](../pipeline/06_harmonize.py) explicitly forbids. A cell predicted at 2 gets [0, 32], so for a
country or large area the upper bound was inflated several times (the correct interval for a prediction of ~2,490 is
[2,123, 2,921]). Fixed in PR #1: the interval is sized on the area's total, with country parameters for the whole
territory and region parameters for any smaller area; a test covers it.

---

## 5. Comparison with other work

No peer-reviewed harmonized MODIS+VIIRS *active-fire* record was found; the closest analogues are burned-area products
and record-continuity studies.

| question | literature | this project | conclusion |
|---|---|---|---|
| How many more fires VIIRS sees | Punjab: VIIRS 375 m ×4.8 vs Terra+Aqua, ×6.5 vs Aqua, because the I-band pixel is ~7× smaller and catches small farm fires [1] (but MODIS averaged over 2003–2016 and VIIRS over 2012–2016) | India: ×5.79 in points, ×4.54 in cell-days, same years 2013–2019 | Same order; the project compares like with like |
| What drives the ratio | MODIS misses more in low-biomass land (crops, steppe, grass); detection rises with fire size [2, 3] | ×1.6–2.0 for large steppe/forest fires, ×3.9–4.5 for small farm fires | Supports §2.1–2.2: the multiplier should depend on fire size and land cover |
| How an operational product converts VIIRS | GFED5 NRT calibrates VIIRS on burned area over 2012–2022 with multipliers per region × land-cover type (up to 224) and scan-angle lookup tables; it warns that country-level and finer uncertainty is "substantially higher" [4] | one multiplier per country and season, no scan angle | Best practice: land-cover/region strata and scan angle (§2.2, §2.7) |
| MODIS orbit drift | GFED5 stops at 2022 because drift exceeded science-quality thresholds [4]; Terra lowered in Oct 2022, its overpass ~1.5 h earlier, Aqua later [5] | calibration 2012–2019, 2020+ treated as a drift test; Terra/Aqua 1.36 → 0.62 after 2021 | The window is right, stricter than GFED5 |
| Regression over a sensor overlap | MODIS → VIIRS for volcano monitoring: per-target linear fits over 2012–2020, slopes 0.78–1.14 depending on local conditions [6] | one model per country; region spread −15…+13.5% | Per-target spread is normal: an argument for a region effect (§2.2) |
| Trend in Kazakhstan | Northern Eurasia burned area (MODIS) fell 53% over 2002–2016, 84% of it from Kazakh steppe; drivers: wetter climate and grazing [7] | 2002 → 2016: MODIS −77% in cell-days, harmonized −71%, naive splice −54% | Same direction; magnitudes differ (area vs cell-days, different geography) |

**Stricter than the literature:** same-year comparisons, separate drift and backcast tests, cross-fitted intervals.
**Behind:** no land-cover/region strata, no scan-angle correction.

**Sources**
1. Vadrevu, Lasko et al. 2018. *Intercomparison of MODIS AQUA and VIIRS I-Band Fires and Emissions in an Agricultural
   Landscape*. https://pmc.ncbi.nlm.nih.gov/articles/PMC6108185/
2. *Fire Detection and Fire Radiative Power in Forests and Low-Biomass Lands in Northeast Asia: MODIS versus VIIRS*,
   Remote Sensing 2020. https://www.mdpi.com/2072-4292/12/18/2870
3. Schroeder et al. 2014. *The New VIIRS 375 m active fire detection data product*.
   https://www.earthdata.nasa.gov/sites/default/files/imported/Schroeder_et_al_2014b_RSE.pdf
4. Near-real-time extension to GFED, ESSD 18, 7535 (2026). https://essd.copernicus.org/articles/18/7535/2026/
5. NASA LANCE UWG, November 2022 (Terra/Aqua orbit drift).
   https://wiki.earthdata.nasa.gov/download/attachments/5702164/LANCE%20UWG%20Nov_2022_Final.pdf?api=v2
6. *The Transition from MODIS to VIIRS for Global Volcano Thermal Monitoring*.
   https://pmc.ncbi.nlm.nih.gov/articles/PMC8914890/
7. Hao et al. 2021. *Wetter environment and increased grazing reduced the area burned in northern Eurasia from 2002
   to 2016*, Biogeosciences 18, 2559–2572, doi:10.5194/bg-18-2559-2021.

---

## 6. Checks on real cell-level data (2026-11-15)

Input: `cell_month_all.parquet` from the machine that runs the pipeline (1,072,248 rows; KAZ, UZB, TKM, KGZ, TJK).
All runs in a temporary folder; no report in the repository was overwritten by them.

### 6.1 The team's reports reproduce (commit `33b7d7d`)
- `experiments` for Kazakhstan: `model_card.json` matches to a relative 2.3·10⁻⁵ (scipy optimizer, Windows vs macOS).
  All 8 candidate scores match to 4 decimals except C7 (15.39 vs 15.41), a 4-parameter model on which the optimizer
  is unstable; the ranking is unchanged.
- The burned-area test (`07b`) matches exactly for all 5 countries, factors and 95% intervals.

### 6.2 T5 and robustness of the choice (full `experiments`, Kazakhstan)

| model | score | T5 MAE / bias | share of bootstrap wins | score − C2 (90% interval) |
|---|---|---|---|---|
| C2 (selected) | 8.94 | **7.3% / +3.7%** | 62% | — |
| C1 | 9.03 | 8.2% / +3.1% | 32% | +0.13 (−0.28 … +0.65) |
| C0 | 9.91 | 10.7% / **+10.4%** | 2% | +0.94 (+0.14 … +1.68) |

- C2 and C1 are statistically tied but give the **same** 2003–2011 total (−0.0%), so the pre-2012 level does not
  depend on the choice between them.
- The constant ratio C0 is significantly worse; its +9.0% on the 2003–2011 level is error, not uncertainty.
- T5 computed from the exported country totals gives the same numbers to one decimal: two independent paths agree.

### 6.3 Hierarchical model (`pipeline/hier.py`, side branch): not confirmed
It won on synthetic data. On real data, leave-one-region-out in Kazakhstan gives 20.6% (bias −18.7%) against 13.5% for
C2. By region it is better in UZB and TKM (44.7% vs 53.0%, 26.4% vs 32.5%), but worse more often across countries and
when trained on Kazakhstan only. The fire-size feature gets a weak coefficient (−0.17). Not for the product.

### 6.4 Burned area with a MODIS-only control
MODIS has no sensor change in 2012, so its step against burned area measures how the link between fires and burned
area itself changes. That is the background against which to read the harmonized series. (The MODIS-only row is now
in `reports/VALIDATION.md` §5, commit `86fd3c3`.)

| country | window | naive splice | harmonized (own coefficients) | MODIS alone | harmonized / MODIS | naive / MODIS |
|---|---|---|---|---|---|---|
| KAZ | 2003–2025 | ×2.41 | ×1.16 (0.88–1.53) | ×1.22 (0.82–1.83) | ×0.95 | ×1.97 |
| UZB | 2003–2025 | ×3.87 | ×1.04 (0.80–1.35) | ×1.06 (0.77–1.46) | ×0.98 | ×3.66 |
| TKM | 2003–2025 | ×3.93 | ×1.14 (0.87–1.49) | **×1.44 (1.09–1.90)** | ×0.79 | ×2.73 |
| KGZ | 2003–2025 | ×1.77 | ×0.54 (0.37–0.80) | **×0.62 (0.43–0.90)** | ×0.88 | ×2.86 |
| TJK | 2003–2025 | ×2.26 | ×0.71 (0.47–1.07) | ×0.84 (0.55–1.27) | ×0.85 | ×2.70 |
| KAZ | 2003–2019 | ×2.21 | ×1.05 | ×0.96 | ×1.09 | ×2.30 |
| UZB | 2003–2019 | ×4.85 | ×1.27 | ×1.33 | ×0.96 | ×3.66 |
| TKM | 2003–2019 | ×4.24 | ×1.20 | ×1.34 | ×0.89 | ×3.17 |
| KGZ | 2003–2019 | ×2.00 | ×0.62 | ×0.59 | ×1.04 | ×3.39 |
| TJK | 2003–2019 | ×3.05 | ×0.93 | ×0.94 | ×0.99 | ×3.25 |

- **Kyrgyzstan is not "over-corrected".** Its ×0.54 is close to MODIS alone (×0.62), and with Kazakh coefficients
  Kyrgyzstan is rather under-estimated (annual check −14%). The burned-area test is simply inconclusive there.
- **Turkmenistan:** the control itself shifts ×1.44, so the test is not clean there.
- **"The MODIS step comes from 2020+ orbit drift"** holds only for Kazakhstan (×1.22 → ×0.96 on 2003–2019); in UZB and
  KGZ the fire–burned-area link really changes.
- On the drift-free window the harmonized series stays within **×0.89–1.09 of MODIS in all 5 countries**; the naive
  splice is ×2.3–3.7.
- **Resolution of the test:** the ratio to MODIS partly holds by construction (the model is fitted on 2012–2019), and
  MODIS itself moves ±40% against burned area. The test reliably shows that the ×2–4 seam is gone, not ±10% accuracy;
  accuracy is shown by T1, T4, T5 and leave-one-region-out.
- **Suggestion for `07b`** (after the submission, so README and site stay in step): the 2003–2019 window, for the same
  reason the calibration excludes 2020+.

### 6.5 Accuracy hypotheses (fixed before testing)
H1: a separate intercept per month with a shared slope. H2: + log(MODIS points per cell-day). H3: + night share.
H4: H1 + H2. The harness first reproduced C2 exactly (score 8.945, T1 6.97, T3 13.49, T4 6.37, T2 9.77 / −0.9,
T5 7.33 / +3.7).

Protocol score (lower is better), each country fitted on its own cell-level data:

| | KAZ | UZB | TKM | KGZ | TJK |
|---|---|---|---|---|---|
| C2 | 8.94 | 28.44 | **21.45** | **34.82** | 48.94 |
| H1 | 8.38 | 28.34 | 22.17 | 38.53 | **45.46** |
| H2 | 8.62 | 28.69 | 21.77 | 35.20 | 48.10 |
| H3 | 9.21 | 28.42 | 21.93 | 36.94 | 47.84 |
| H4 | **7.67** | **26.69** | 22.55 | 36.09 | 45.88 |

H1 vs C2 on country totals for all 10 countries (regions cannot be tested this way):

| test | H1 more accurate | mean \|bias\| C2 → H1 |
|---|---|---|
| T2, holdout 2020–2025 | **10 of 10** | 6.8% → 6.4% |
| T4, leave-one-year-out | 8 of 10 | 0.6% → 0.4% |
| T1, backcast (direction of use) | 6 of 10 | 3.5% → **4.7%** |
| T5, extrapolation | 5 of 10 | 5.4% → 4.2% |

- **H4 is not robustly better than C2:** it wins in 3 of 5 countries and has more holdout bias in Kazakhstan (−2.4% vs
  −0.9%).
- **H1 is a real candidate:** more accurate on the holdout everywhere (10 of 10 by chance has p ≈ 0.002), but tied in
  the direction the product is used (T1, T5) and with more T1 bias.
- H1 was formulated after seeing results; the honest path is to add it to the protocol in advance and test it in full,
  including regions. **The model is not changed for the submission.**
