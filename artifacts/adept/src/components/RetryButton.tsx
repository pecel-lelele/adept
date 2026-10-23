"use client";

import { RotateCw } from "lucide-react";
import { useRouter } from "@/lib/next-compat/router";
import { useTransition } from "react";

export function RetryButton({ label }: { label: string }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <button type="button" className="a-btn is-ghost is-small" disabled={pending} onClick={() => start(() => router.refresh())}>
      <RotateCw size={14} aria-hidden /> {label}
    </button>
  );
}
