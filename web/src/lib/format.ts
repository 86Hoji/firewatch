const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function ymParts(ym: string): [number, number] {
  return [Number(ym.slice(0, 4)), Number(ym.slice(5, 7))];
}
export function ymLong(ym: string): string {
  const [y, m] = ymParts(ym);
  return `${MONTHS[m - 1]} ${y}`;
}
export function ymShort(ym: string): string {
  const [y, m] = ymParts(ym);
  return `${MONTHS_SHORT[m - 1]} ${y}`;
}

const nf0 = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 });

/** Cell-day counts: whole numbers above 10, one decimal below (values are rounded to 3 s.f. upstream). */
export function fmtCD(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—';
  return Math.abs(v) >= 10 ? nf0.format(v) : nf1.format(v);
}

export function fmtPct(p: number): string {
  const s = Math.round(p);
  if (s === 0) return 'same as';
  return `${s > 0 ? '+' : '−'}${nf0.format(Math.abs(s))}%`;
}
