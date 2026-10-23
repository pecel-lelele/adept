"use client";

import { usePathname, useRouter, useSearchParams } from "@/lib/next-compat/router";
import { useTransition } from "react";
import { useBusy } from "@/components/useBusy";

/** Trend replay: pick a stored snapshot date; rankings re-compute on that date's data. */
export function SnapshotPicker({
  dates,
  value,
  label,
  latestLabel,
}: {
  dates: string[];
  value: string;
  label: string;
  latestLabel: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, start] = useTransition();
  useBusy(pending);
  return (
    <label className="a-field" style={{ maxWidth: 280 }}>
      {label}
      <select
        className="a-select"
        value={value}
        disabled={pending}
        onChange={(e) => {
          const next = new URLSearchParams(params.toString());
          if (e.target.value) next.set("snapshot_date", e.target.value);
          else next.delete("snapshot_date");
          start(() => router.push(`${pathname}?${next.toString()}`, { scroll: false }));
        }}
      >
        <option value="">{latestLabel}</option>
        {[...dates].reverse().map((d) => (
          <option key={d} value={d}>
            {d}
          </option>
        ))}
      </select>
    </label>
  );
}
