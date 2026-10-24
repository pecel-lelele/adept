import { ChevronDown } from "lucide-react";
import type { ReactNode } from "react";

/**
 * A card that shows one line (title + the key number) and opens for detail. Native
 * <details>, so it works without JavaScript and is keyboard and screen-reader accessible.
 */
export function Fold({
  title,
  meta,
  icon,
  open = false,
  children,
  id,
}: {
  title: ReactNode;
  meta?: ReactNode;
  icon?: ReactNode;
  open?: boolean;
  children: ReactNode;
  id?: string;
}) {
  return (
    <details className="a-card a-fold" open={open}>
      <summary className="a-fold-head">
        <span className="a-fold-title">
          {icon}
          <span>{title}</span>
        </span>
        {meta ? <span className="a-fold-meta">{meta}</span> : null}
        <ChevronDown size={18} aria-hidden className="a-fold-chevron" />
      </summary>
      <div className="a-fold-body">
        {/* The anchor sits inside, so following a link to it opens the section. */}
        {id ? <span id={id} className="a-fold-anchor" /> : null}
        {children}
      </div>
    </details>
  );
}
