"""Render README.md from docs/README.template.md with every number taken from the current reports.

    python -m pipeline.readme_numbers            # write README.md
    python -m pipeline.readme_numbers --check    # exit 1 if README.md is out of date

Sources (nothing is typed by hand):
  reports/model_card.json   interval coverage before/after, T1-T4 scores, holdout period
  reports/validation.json   2012 steps (UZ, TM), burned-area steps, transfer table, Abai event rank
  web/public/data/series/KAZ.json   Kazakh monthly MODIS / VIIRS totals -> 2002-04 vs calibration activity and the
                                    T5 extrapolation test (pipeline.experiments.extrapolation_test, C2 vs C0)
Run it after the last pipeline / export run, so README and reports cannot disagree.
"""
import json
import sys

import numpy as np
import pandas as pd

from pipeline import experiments, models
from pipeline.common import REPORTS, ROOT, load_config

TEMPLATE = ROOT / "docs" / "README.template.md"
README = ROOT / "README.md"
NAMES = {"KAZ": "Kazakhstan", "UZB": "Uzbekistan", "TKM": "Turkmenistan", "KGZ": "Kyrgyzstan", "TJK": "Tajikistan",
         "PRT": "Portugal", "AUS": "Australia", "BRA": "Brazil", "USA": "the USA", "IND": "India"}


def x(v):
    return f"{v:.2f}"


def pct(v, signed=False):
    return f"{v:+.1f}".replace("-", "−") if signed else f"{v:.1f}"


def kilo(v):
    return f"{v / 1000:.0f}k"


def kz_series():
    j = json.loads((ROOT / "web" / "public" / "data" / "series" / "KAZ.json").read_text(encoding="utf-8"))
    ym = pd.to_datetime(j["ym"])
    return pd.DataFrame({"year": ym.year, "month": ym.month, "n_modis": np.array(j["modis_only"], float),
                         "v_target": np.array([0 if v is None else v for v in j["viirs"]], float)})


def values(cfg):
    card = json.loads((REPORTS / "model_card.json").read_text(encoding="utf-8"))
    val = json.loads((REPORTS / "validation.json").read_text(encoding="utf-8"))
    iv, sc = card["intervals"], card["scores"]
    st = {k: val[k]["steps"] for k in ("uz_test", "tm_stress")}
    ba = val["burned_area"]
    tr = val["transfer"]
    abai = next(e for e in val["events"]["KAZ"]["known_events"] if "Abai" in e["name"])
    s = kz_series()
    annual = s.groupby("year")["n_modis"].sum()
    cal = cfg["calibration"]["period"]
    t5 = {c: experiments.series_metrics(*experiments.extrapolation_test(models.SPECS[c], s, cfg)[["v_target", "pred"]]
                                        .to_numpy().T) for c in ("C0", "C2")}
    others = {c: r for c, r in tr.items() if c != "KAZ"}
    asis = [r["overlap_as_is"]["mae_pct_of_mean"] for r in others.values()]
    local = [r["overlap_local"]["mae_pct_of_mean"] for r in tr.values()]
    ratio = {c: r["ratio_observed"] for c, r in tr.items()}
    rmin, rmax = min(ratio, key=ratio.get), max(ratio, key=ratio.get)

    def ba_step(c, k):
        return ba[c][k]["step_given_burned_area"]

    return {
        "cov_before": f"{100 * iv['coverage_before']['T3_loro_region']:.0f}%",
        "cov_after": f"{100 * iv['coverage_after']['T3_loro_region']:.0f}%",
        "uz_naive": x(st["uz_test"]["naive"]["step_ratio"]), "uz_local": x(st["uz_test"]["harmonized_local"]["step_ratio"]),
        "uz_modis": x(st["uz_test"]["modis_only"]["step_ratio"]),
        "tm_naive": x(st["tm_stress"]["naive"]["step_ratio"]), "tm_local": x(st["tm_stress"]["harmonized_local"]["step_ratio"]),
        "tm_modis": x(st["tm_stress"]["modis_only"]["step_ratio"]),
        "uz_ba_naive": x(ba_step("UZB", "naive")["step_factor"]), "tm_ba_naive": x(ba_step("TKM", "naive")["step_factor"]),
        "uz_ba": x(ba_step("UZB", "harmonized_local")["step_factor"]),
        "uz_ba_ci": f"{x(ba_step('UZB', 'harmonized_local')['ci_low'])}–{x(ba_step('UZB', 'harmonized_local')['ci_high'])}",
        "tm_ba": x(ba_step("TKM", "harmonized_local")["step_factor"]),
        "tm_ba_ci": f"{x(ba_step('TKM', 'harmonized_local')['ci_low'])}–{x(ba_step('TKM', 'harmonized_local')['ci_high'])}",
        "t1": pct(sc["T1_backcast_mae_pct"]), "t3": pct(sc["T3_loro_mae_pct"]), "t4": pct(sc["T4_loyo_mae_pct"]),
        "t2": pct(sc["T2_forecast_mae_pct"]), "t2_bias": pct(sc["T2_forecast_bias_pct"], True),
        "n_regions": str(card["loro"]["regions_included"]), "holdout": f"{card['holdout'][0]}–{card['holdout'][1]}",
        "kz_0204": f"{kilo(annual.loc[2002:2004].min())}–{kilo(annual.loc[2002:2004].max())}",
        "kz_calmax": kilo(annual.loc[cal[0]:cal[1]].max()),
        "t5_c2_mae": pct(t5["C2"]["mae_pct_of_mean"]), "t5_c2_bias": pct(t5["C2"]["bias_total_pct"], True),
        "t5_c0_bias": pct(t5["C0"]["bias_total_pct"], True),
        "abai_rank": str(abai["rank"]), "abai_of": f"{abai['of']:,}",
        "ba_shifted": ", ".join(f"{NAMES.get(c, c)} ×{x(r['modis_only']['step_given_burned_area']['step_factor'])}"
                                for c, r in ba.items() if "modis_only" in r
                                and not r["modis_only"]["step_given_burned_area"]["ci_includes_1"]),
        "asis_range": f"{min(asis):.0f}–{max(asis):.0f}", "local_range": f"{min(local):.0f}–{max(local):.0f}",
        "ratio_min": f"{ratio[rmin]:.1f}", "ratio_min_c": NAMES.get(rmin, rmin),
        "ratio_max": f"{ratio[rmax]:.1f}", "ratio_max_c": NAMES.get(rmax, rmax),
    }


def render(cfg=None):
    return TEMPLATE.read_text(encoding="utf-8").format(**values(cfg or load_config()))


def main(argv):
    text = render()
    if "--check" in argv:
        ok = README.exists() and README.read_text(encoding="utf-8") == text
        print("README.md is up to date" if ok else "README.md is out of date: run python -m pipeline.readme_numbers")
        sys.exit(0 if ok else 1)
    README.write_text(text, encoding="utf-8")
    print("wrote README.md")


if __name__ == "__main__":
    main(sys.argv[1:])
