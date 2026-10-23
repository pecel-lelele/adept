"use client";

import { Leaf } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "@/lib/next-compat/router";
import { useState, useTransition } from "react";
import { useBusy } from "@/components/useBusy";

/**
 * SDG-weighted ranking: how much the UN Goals should count, 0-100 %. Releasing the slider
 * re-ranks the roles on the server (GET /matches?sdg_weight=). 0 keeps the standard score.
 */
export function SdgWeightSlider({
  value,
  label,
  hint,
  offLabel,
}: {
  value: number;
  label: string;
  hint: string;
  offLabel: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, start] = useTransition();
  useBusy(pending);
  const [draft, setDraft] = useState(Math.round(value * 100));
  const commit = (pct: number) => {
    const next = new URLSearchParams(params.toString());
    if (pct > 0) next.set("sdg", (pct / 100).toFixed(2));
    else next.delete("sdg");
    start(() => router.replace(`${pathname}?${next.toString()}`, { scroll: false }));
  };
  return (
    <div className="a-sdgslider" data-pending={pending}>
      <label htmlFor="sdg-weight">
        <Leaf size={16} aria-hidden /> {label}
        <strong>{draft === 0 ? offLabel : `${draft}%`}</strong>
      </label>
      <input
        id="sdg-weight"
        className="a-range"
        type="range"
        min={0}
        max={60}
        step={10}
        value={draft}
        onChange={(e) => setDraft(Number(e.target.value))}
        onPointerUp={() => commit(draft)}
        onKeyUp={() => commit(draft)}
        aria-describedby="sdg-weight-hint"
      />
      <small id="sdg-weight-hint">{hint}</small>
    </div>
  );
}
