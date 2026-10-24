import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

/** Card (partner design): white, 20px radius, thin sage border. Feature code adds layout. */
export function Card({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("a-card", className)} {...props} />;
}

export function CardHeader({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("a-card-top", className)} {...props} />;
}

export function CardTitle({ className, ...props }: ComponentProps<"h3">) {
  return <h3 className={cn("a-card-title", className)} {...props} />;
}

export function CardDescription({ className, ...props }: ComponentProps<"p">) {
  return <p className={cn("a-muted a-small", className)} {...props} />;
}

export function CardContent({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("a-card-body", className)} {...props} />;
}
