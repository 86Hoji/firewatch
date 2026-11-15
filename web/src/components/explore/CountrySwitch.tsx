import { useStore } from '../../store';
import { loadMeta, type CountryCode } from '../../lib/data';
import { engine } from '../../map/MapStage';

const OPTIONS: { code: CountryCode; short: string; name: string }[] = [
  { code: 'KAZ', short: 'KZ', name: 'Kazakhstan' },
  { code: 'UZB', short: 'UZ', name: 'Uzbekistan' },
];

/** Segmented control: which country the panels, the dateline and the camera follow. */
export function CountrySwitch() {
  const country = useStore((s) => s.country);
  return (
    <div role="radiogroup" aria-label="Country" className="glass pointer-events-auto relative grid shrink-0 grid-cols-2 rounded-[10px] p-[3px]">
      {OPTIONS.map((o) => {
        const on = o.code === country;
        return (
          <button
            key={o.code}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => {
              const s = useStore.getState();
              if (s.country !== o.code) {
                s.setSelected(null);
                s.setCountry(o.code);
                loadMeta().then((m) => {
                  const c = m.countries.find((x) => x.code === o.code);
                  if (c) engine?.flyToCountry(o.code, c.bbox);
                });
              }
            }}
            className={`h-8 rounded-[4px] text-[15px] transition-colors duration-[160ms] ${
              on ? 'bg-[rgba(245,184,61,0.14)] text-gold-pale shadow-[inset_0_0_0_1px_rgba(245,184,61,0.35)]' : 'text-text-map-2 hover:text-text'
            }`}
          >
            <span className="font-medium">{o.short}</span>
            <span className="ml-2 hidden sm:inline">{o.name}</span>
          </button>
        );
      })}
    </div>
  );
}
