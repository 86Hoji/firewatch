# FIREWATCH — art direction

The site is one instrument: a night globe on which twenty-five years of fire rise as lit gold
columns. Everything that is not the map is quiet, set like a printed atlas — serif datelines, small
sans figures, hairlines. Boldness is spent once, on the map.

## What makes this ours

1. **The basemap is our sensor.** The night lights under the fires are NASA Black Marble, made by the
   same VIIRS instrument whose detections we harmonize. The page says so in the credits, and the
   city lights are kept faintly visible for that reason.
2. **The scrubber is a chart.** The time bar's track is a one-column-per-month heat strip of the
   harmonized country total, so the spring and autumn fire seasons and the big years (2002–2003,
   2008, 2012) are visible before anyone presses play.
3. **The 2012 seam.** One hairline at January 2012 appears on every time axis we draw (time bar,
   calendar, charts). It is the place where MODIS and VIIRS were stitched — a recurring mark that only
   this project has a reason to draw.
4. **Every number carries its range.** Harmonized values are always written with their 90% range
   ("1,240 cell-days, 980–1,560"). Observed VIIRS months (2012 on) show a single value, because they
   are not modelled. Honesty as a typographic rule.
5. **Dateline, not dashboard.** The current month is set like a newspaper dateline — "September 2023"
   in Instrument Serif at 76 px — with the country figure beneath it in small tabular Geist. No KPI tiles.

## Tokens

| token | value | use |
|---|---|---|
| `--night` | `#070B18` | page, space behind the globe |
| `--deep` | `#0D1428` | raised surfaces, map tint |
| `--ink` | `#111A33` | solid panels (non-map pages) |
| `--line` | `rgba(148,170,220,0.12)` | hairlines, dividers |
| `--text` | `#EEF2FB` | primary text |
| `--text-2` | `#9AA8C7` | secondary text, axis labels |
| `--text-3` | `#5F6E91` | tertiary, naive series line |
| `--text-map-2` | `#B7C2DB` | secondary text over the map (AA over the brightest cluster) |
| `--gold` | `#F5B83D` | the harmonized record, playhead, primary action |
| `--ember` | `#D4891C` | gold's shaded side, pressed states |
| `--gold-pale` | `#FFE7A3` | hottest cells, glass edge tint |
| `--ice` | `#93C5FD` | the word/series "VIIRS" in charts only |
| `--coral` | `#FF6B6B` | anomalies and errors only |

Activity ramp (map, calendar, scrubber), log scale on cell-days:
`#141C38 → #3B2F1A → #8A5A12 → #D4891C → #F5B83D → #FFE7A3`.
The first stop is never drawn on the map (zero cells are omitted); it exists for the calendar.

**Glass** — only for panels floating over the map: `rgba(13,20,40,0.55)`, `blur(18px) saturate(140%)`,
1 px border `rgba(255,231,163,0.10)`, inner top highlight `inset 0 1px 0 rgba(255,231,163,0.08)`,
shadow `0 24px 64px rgba(0,0,0,0.45)`. Measured on screenshots over the brightest cluster (October 2003,
north Kazakhstan): `--text` 7.8:1, `--gold` 4.9:1, `--gold-pale` 7.2:1 pass; `--text-2` 3.7:1 fails, so all
secondary text over the map (glass or not) uses `--text-map-2` `#B7C2DB` (≈4.8:1). Checked by
`scripts/contrast.mjs`. `--text-3` never appears on glass.

**Radii** — 6 controls, 14 floating panels, 22 hero overlays. Charts and hairlines: 0.

## Type

- Display: **Instrument Serif** 400, leading 1.05, tracking −0.015em. Used for headlines and the map
  dateline only. Never bold, never italic for emphasis.
- Everything else: **Geist** (variable). Numbers: `font-variant-numeric: tabular-nums`. No monospace.
- Scale (px): 13 / 15 / 17 / 22 / 32 / 48 / 76 / 112.
  - 13 — axis labels, credits, tooltip meta (Geist 450, text-2)
  - 15 — UI labels, tooltip body, buttons
  - 17 — body copy (max 68ch, line-height 1.6)
  - 22 — panel titles, figures in the tooltip
  - 32 — section heads on editorial pages (serif)
  - 48 — mobile dateline, page titles (serif)
  - 76 — desktop map dateline (serif)
  - 112 — landing headline on desktop (serif)
- Labels are sentence case. No letter-spaced caps anywhere.

## Layout

### Map, desktop 1440 × 900

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ FIREWATCH (wordmark, 15, text-2)                                   Explore   │  ← 28 px from edges
│                                                                              │
│ September 2023            ← serif 76                                          │
│ Kazakhstan  4,120 cell-days, 3,860–4,410   ← Geist 15, tabular                │
│                                                                              │
│                         ·  ·    ▲▲   ▲                                       │
│                    ▲ ▲▲▲  ▲▲▲▲▲▲▲▲▲▲  ▲     (globe, pitch 45°, bearing −12°)   │
│               ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲                                    │
│                  ▲▲▲▲  ▲▲▲▲▲   ◎ Abai 2023                ┌ tooltip (glass 14)┐ │
│                                                         │ East Kazakhstan   │ │
│                                                         │ June 2023         │ │
│                                                         │ 412  (380–450)    │ │
│                                                         │ +38% vs 2012–19   │ │
│                                                         └───────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │ ▶  1×   ▁▂▇▃▁▁▂█▅▁▁▃▇▂▁▁▂▆▃▁ … ▏(2012 seam) … ▃█▂▁▂▇▃┃▁▂▅          │    │  ← glass, r14
│  │         2005      2010      2015      2020      2025                │    │     920 wide, centred
│  └──────────────────────────────────────────────────────────────────────┘    │
│ Night lights: NASA Black Marble (VIIRS)   (credits, 13, bottom-right)        │
└──────────────────────────────────────────────────────────────────────────────┘
```

Grid: 12 columns, 28 px outer margin on desktop, 16 px on mobile. The dateline and the time bar share
the left edge of the content box (x = 28).

### Map, mobile 390 × 844

```
┌──────────────────────────────┐
│ FIREWATCH            Explore │
│ September 2023   ← serif 48  │
│ Kazakhstan 4,120 cell-days   │
│ 3,860–4,410                  │
│                              │
│      ▲▲▲ ▲▲▲▲▲▲▲  ▲          │
│   ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲          │
│        ▲▲▲  ◎               │
│                              │
│ ┌──────────────────────────┐ │
│ │ ▶ 1×                     │ │  ← glass bar, full width − 32
│ │ ▁▂▇▃▁▁▂█▅▁ … ▃█▂▁┃▁▂▅    │ │
│ │ 2005  2010  2015  2020   │ │
│ └──────────────────────────┘ │
└──────────────────────────────┘
```
On touch, hover becomes tap: a tap on a region shows the tooltip docked above the time bar.

## Motion

- Ease: `cubic-bezier(0.22,1,0.36,1)`. Durations: 160 hover/press, 280 panels, 600 map transitions,
  4000 intro flight. Panels: spring (stiffness 260, damping 30).
- **One autoplay sequence, once per load:** black (0–300 ms) → stars fade in (300–1100) → globe fades
  in, rotating slowly eastward (800–2000) → 4 s flight to Central Asia ending at pitch 45°, bearing
  −12° → hexagons rise from 0 over 900 ms, staggered by distance from the camera target (centre
  first, edges last). Nothing else on the page moves unless asked.
- Playing the time bar: elevation and colour interpolate over 600 ms between months (shortened to the
  step length at 2×), so the map breathes.
- Numbers count between values over 280 ms, only on a user change of month or region.
- Abai 2023 ring pulses (2.4 s period) only while it is on screen and only when its month is shown or
  the map is paused near it; otherwise it is a still ring.
- `prefers-reduced-motion`: no flight (camera cut to final view), hexagons appear at full height, no
  interpolation between months, no ring pulse, no count-up.

## Review against the AVOID list

| tell | where it could have crept in | what we do instead |
|---|---|---|
| Tracked caps eyebrows | above the dateline, panel titles | Sentence-case labels; the dateline needs no eyebrow |
| Middle-dot meta strings | credits, the country line | Credits are a short sentence; the country line uses spacing and weight, not dots |
| "→" on buttons/links | "Open the map", "See the evidence" | Plain text buttons; links underline on hover |
| One highlighted word | landing headline | Headline set in one colour, one style |
| Grid of identical cards | validation tests, method steps | Editorial sections with one chart each; panels on Explore differ in size and content |
| Gradient washes | hero, section backgrounds | Flat `--night`; the only gradient is the vignette over the map (functional) and the data ramp |
| Fade-up on every section | landing, validation | The map moves; text appears with scroll-pinned scenes only on the landing |
| Hover animation everywhere | buttons, panels | Hover changes colour only, 160 ms; regions on the map are the one hover effect with glow |
| Big number + small label hero | country total | The total sits under the dateline at 15 px — the month is the headline, not the number |
| 01/02/03 markers | method | Only on /method, which is a true sequence |
| Spinners | data loading | Loading = the globe's own intro; late year files fade in, no spinner |
| Filler words | all copy | Copy names fires, satellites, regions, months |

Revisions made after this review: dropped a planned "LIVE DATA" pill on the time bar (eyebrow tell);
removed a planned "→" on the map's Explore link; replaced a planned three-tile stat row under the
dateline with a single line of text; the credits are no longer a dotted list.
