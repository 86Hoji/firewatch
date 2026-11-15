// Activity ramp and the one log scale everything shares (map, scrubber, calendar).

export const RAMP: [number, number, number][] = [
  [0x14, 0x1c, 0x38],
  [0x3b, 0x2f, 0x1a],
  [0x8a, 0x5a, 0x12],
  [0xd4, 0x89, 0x1c],
  [0xf5, 0xb8, 0x3d],
  [0xff, 0xe7, 0xa3],
];

/** 0..1 on a log1p scale with a fixed top, so a month in 2001 and one in 2024 read the same. */
export function logNorm(v: number, top: number): number {
  if (!(v > 0)) return 0;
  return Math.min(1, Math.log1p(v) / Math.log1p(top));
}

/** Writes the ramp colour for t∈[0,1] into out (rgb, 0..255). */
export function rampRGB(t: number, out: number[] | Uint8ClampedArray, offset = 0): void {
  const x = Math.max(0, Math.min(1, t)) * (RAMP.length - 1);
  const i = Math.min(RAMP.length - 2, Math.floor(x));
  const f = x - i;
  const a = RAMP[i];
  const b = RAMP[i + 1];
  out[offset] = a[0] + (b[0] - a[0]) * f;
  out[offset + 1] = a[1] + (b[1] - a[1]) * f;
  out[offset + 2] = a[2] + (b[2] - a[2]) * f;
}

export function rampCSS(t: number): string {
  const c = [0, 0, 0];
  rampRGB(t, c);
  return `rgb(${c[0] | 0},${c[1] | 0},${c[2] | 0})`;
}

/** Cell-day tops per hexagon resolution (≈ 99.9th percentile over 2001–2026, KZ + UZ). */
export const HEX_TOP = { r5: 90, r7: 16 } as const;
export type Res = keyof typeof HEX_TOP;

/** Log scale with a floor at top/span: for country totals, where log1p would flatten the seasons. */
export function logNormFloor(v: number, top: number, span = 400): number {
  const lo = top / span;
  if (!(v > lo)) return 0;
  return Math.min(1, Math.log(v / lo) / Math.log(span));
}
