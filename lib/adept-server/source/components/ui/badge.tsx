import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

type Variant = "default" | "secondary" | "outline" | "warning" | "success" | "danger";
const TONE: Record<Variant, string | undefined> = {
  default: "dark",
  secondary: undefined,
  outline: "outline",
  warning: "warn",
  success: "up",
  danger: "down",
};

/** Small label chip; tones map to the shared .a-chip palette. */
export function Badge({
  className,
  variant = "default",
  ...props
}: ComponentProps<"span"> & { variant?: Variant | null }) {
  return <span className={cn("a-chip", className)} data-tone={TONE[variant ?? "default"]} {...props} />;
}
