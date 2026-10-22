import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

type Variant = "default" | "outline" | "ghost";
type Size = "default" | "sm" | "lg";

/** Class names for a link or button styled as a button (green primary, white secondary). */
export function buttonVariants({ variant = "default", size = "default" }: { variant?: Variant | null; size?: Size | null } = {}): string {
  if (variant === "ghost") return "a-link";
  return cn("a-btn", variant === "outline" && "is-ghost", size === "sm" && "is-small");
}

export function Button({
  className,
  variant,
  size,
  ...props
}: ComponentProps<"button"> & { variant?: Variant | null; size?: Size | null }) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
