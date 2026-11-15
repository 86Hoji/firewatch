import type { ReactNode } from 'react';

/** Floating glass panel over the map. Title is plain sentence case; `aside` sits on the title row. */
export function Panel({
  title,
  aside,
  children,
  className = '',
}: {
  title?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`glass pointer-events-auto rounded-[14px] px-5 py-4 ${className}`}>
      {(title || aside) && (
        <header className="mb-3 flex min-h-[22px] items-baseline justify-between gap-3">
          {title && <h2 className="m-0 text-[15px] font-medium text-text">{title}</h2>}
          {aside && <div className="num truncate text-right text-[13px] text-text-map-2">{aside}</div>}
        </header>
      )}
      {children}
    </section>
  );
}
