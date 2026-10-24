import type { ReactNode } from "react";

/** Page heading (partner design): small square eyebrow, editorial title, quiet description. */
export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
  children,
}: {
  title: string;
  description?: string;
  eyebrow?: string;
  actions?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <header className="a-pagehead">
      <div style={{ minWidth: 0 }}>
        {eyebrow ? <span className="a-eyebrow is-square">{eyebrow}</span> : null}
        <h1 className="a-h1">{title}</h1>
        {description ? <p className="a-lead">{description}</p> : null}
        {children ? <div className="a-pagehead-meta">{children}</div> : null}
      </div>
      {actions ? <div className="a-hero-actions">{actions}</div> : null}
    </header>
  );
}
