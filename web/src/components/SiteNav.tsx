import { NavLink } from 'react-router-dom';

const LINKS = [
  { to: '/explore', label: 'Map' },
  { to: '/evidence', label: 'Evidence' },
];

/** Wordmark plus the three pages. Plain links, current page in gold. */
export function SiteNav({ className = '', onMap = true }: { className?: string; onMap?: boolean }) {
  return (
    <nav aria-label="Site" className={`pointer-events-auto flex items-baseline gap-5 ${className}`}>
      <NavLink to="/" className="display mr-2 text-[22px] text-text no-underline">
        Firewatch
      </NavLink>
      {LINKS.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          className={({ isActive }) =>
            `text-[15px] no-underline underline-offset-4 transition-colors duration-[160ms] hover:underline ${
              isActive ? 'text-gold' : onMap ? 'text-text-map-2 hover:text-text' : 'text-text-2 hover:text-text'
            }`
          }
        >
          {l.label}
        </NavLink>
      ))}
      <a
        href="https://github.com/86Hoji/firewatch"
        target="_blank"
        rel="noreferrer"
        className={`text-[15px] no-underline underline-offset-4 transition-colors duration-[160ms] hover:underline ${onMap ? 'text-text-map-2 hover:text-text' : 'text-text-2 hover:text-text'}`}
      >
        GitHub
      </a>
    </nav>
  );
}
