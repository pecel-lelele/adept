import { Inbox } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="a-card is-flat a-empty">
      <span className="a-empty-icon">
        <Inbox size={22} strokeWidth={1.6} aria-hidden />
      </span>
      <strong style={{ color: "var(--a-ink)", fontWeight: 500 }}>{title}</strong>
      {description ? <p className="a-muted a-small" style={{ margin: 0, maxWidth: 440 }}>{description}</p> : null}
      {action}
    </div>
  );
}
