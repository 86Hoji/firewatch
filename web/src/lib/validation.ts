// Typed view of the parts of data/validation.json the site shows (written by the pipeline).

export interface Step {
  step_ratio: number;
  monthly_step: { step_factor: number; ci_low: number; ci_high: number; n_months: number; ci_includes_1: boolean };
}
export interface Fit {
  n_months: number;
  mae_pct_of_mean: number;
  bias_total_pct: number;
  pearson_r: number;
  coverage?: number;
}
export interface Transfer {
  role: string;
  overlap_as_is: Fit;
  overlap_local: Fit;
  holdout_as_is: Fit;
  holdout_local: Fit;
  ratio_observed: number;
  ratio_kz_model: number;
  transfers: boolean;
}
export interface BAStep {
  step_factor: number;
  ci_low: number;
  ci_high: number;
  ci_includes_1: boolean;
}
export interface Validation {
  model: { label: string; train_country: string };
  uz_test: { steps: Record<'naive' | 'harmonized' | 'modis_only' | 'harmonized_local', Step> };
  tm_stress: { steps: Record<'naive' | 'harmonized' | 'modis_only' | 'harmonized_local', Step> };
  transfer: Record<string, Transfer>;
  burned_area: Record<string, Record<'naive' | 'harmonized' | 'harmonized_local', { r_log_all: number; step_given_burned_area: BAStep }> & { months: number }>;
  annual: Record<string, { mae_pct_of_mean: number; bias_total_pct: number; pearson_r: number; naive_modis_bias_pct: number }>;
  takeaways: Record<string, string>;
  flare_load?: Record<string, FlareLoad>;
}

let p: Promise<Validation> | null = null;
export function loadValidation(): Promise<Validation> {
  p ??= fetch(`${import.meta.env.BASE_URL}data/validation.json`).then((r) => {
    if (!r.ok) throw new Error(`validation.json: ${r.status}`);
    return r.json();
  });
  return p;
}

/**
 * Interval coverage before/after sizing the 90% ranges at the predicted level. Not exported to
 * validation.json: it is the leave-one-region-out test in reports/validation_kz.md
 * ("before 50%, after 92%" over the same region-months), kept here by hand.
 */
export const REGION_COVERAGE = { before: 50, after: 92 };

export interface FlareLoad {
  static_share_removed_pct: number;
  mask_test: { precision: number; recall: number };
}
