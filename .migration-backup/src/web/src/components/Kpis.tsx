import type { ReactNode } from "react";

export type Kpi = {
  label: string;
  value: ReactNode;
  /** Short unit after the value ("h / week", "%"). */
  unit?: string;
  /** One line under the value: context, not a second number. */
  note?: ReactNode;
  icon?: ReactNode;
  tone?: "up" | "down" | "warn";
};

/**
 * The page's key numbers in one strip: label, value, one line of context. Same height and
 * alignment on every page; two per row on phones.
 */
export function Kpis({ items, label }: { items: Kpi[]; label?: string }) {
  return (
    <dl className="a-kpis" aria-label={label} data-count={items.length}>
      {items.map((k) => (
        <div className="a-kpi" key={k.label} data-tone={k.tone}>
          <dt>
            {k.icon ? <span className="a-kpi-icon">{k.icon}</span> : null}
            {k.label}
          </dt>
          <dd className="a-kpi-value">
            <strong>{k.value}</strong>
            {k.unit ? <span>{k.unit}</span> : null}
          </dd>
          {k.note ? <dd className="a-kpi-note">{k.note}</dd> : null}
        </div>
      ))}
    </dl>
  );
}
