import { useStore } from '../../store';
import { COUNTRY_NAMES, COUNTRY_SHORT, loadMeta, type CountryCode } from '../../lib/data';
import { engine } from '../../map/MapStage';

/** Compact segmented control: which country the panels, the dateline and the camera follow. */
export function CountrySwitch() {
  const country = useStore((s) => s.country);
  const countries = useStore((s) => s.countries);

  const pick = (cc: CountryCode) => {
    const s = useStore.getState();
    if (s.country === cc) return;
    s.setSelected(null);
    s.setCountry(cc);
    loadMeta().then((m) => {
      const c = m.countries.find((x) => x.code === cc);
      if (c) engine?.flyToCountry(cc, c.bbox);
    });
  };

  const onKey = (e: React.KeyboardEvent) => {
    const i = countries.indexOf(country);
    const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    const next = countries[(i + d + countries.length) % countries.length];
    pick(next);
    (e.currentTarget.querySelector(`[data-cc="${next}"]`) as HTMLElement | null)?.focus();
  };

  return (
    <div
      role="radiogroup"
      aria-label="Country"
      onKeyDown={onKey}
      className="glass pointer-events-auto relative grid shrink-0 rounded-[10px] p-[3px]"
      style={{ gridTemplateColumns: `repeat(${countries.length}, minmax(0, 1fr))` }}
    >
      {countries.map((cc) => {
        const on = cc === country;
        return (
          <button
            key={cc}
            data-cc={cc}
            type="button"
            role="radio"
            aria-checked={on}
            aria-label={COUNTRY_NAMES[cc]}
            title={COUNTRY_NAMES[cc]}
            tabIndex={on ? 0 : -1}
            onClick={() => pick(cc)}
            className={`num h-8 rounded-[6px] text-[15px] font-medium transition-colors duration-[160ms] ${
              on ? 'bg-[rgba(245,184,61,0.14)] text-gold-pale shadow-[inset_0_0_0_1px_rgba(245,184,61,0.35)]' : 'text-text-map-2 hover:text-text'
            }`}
          >
            {COUNTRY_SHORT[cc] ?? cc}
          </button>
        );
      })}
    </div>
  );
}
