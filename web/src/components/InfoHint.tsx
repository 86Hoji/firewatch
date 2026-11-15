import { useId, useState } from 'react';

export const CELL_DAY = 'A cell-day is one ~5 km² hexagon with fire on that day.';

/** A small "i" that explains a term on hover, focus or tap. */
export function InfoHint({ text = CELL_DAY, label = 'What is a cell-day?' }: { text?: string; label?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span className="relative inline-flex align-[-2px]" style={{ pointerEvents: 'auto' }}>
      <button
        type="button"
        aria-label={label}
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen((o) => !o)}
        className="grid h-[15px] w-[15px] place-items-center rounded-full border border-current text-[10px] font-semibold leading-none text-text-map-2 transition-colors duration-[160ms] hover:text-text"
        style={{ textShadow: 'none' }}
      >
        i
      </button>
      {open && (
        <span
          id={id}
          role="tooltip"
          className="glass absolute left-1/2 top-[calc(100%+8px)] z-30 w-[220px] -translate-x-1/2 rounded-[6px] px-3 py-2 text-[13px] leading-snug text-text"
          style={{ textShadow: 'none' }}
        >
          {text}
        </span>
      )}
    </span>
  );
}
