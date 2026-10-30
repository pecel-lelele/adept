import Link from "next/link";

/** The Adept mark (partner design): an "A" whose green stroke is the step forward. */
export function BrandMark({ size = 28 }: { size?: number }) {
  return (
    <svg
      className="a-brand-mark"
      width={size}
      height={Math.round(size * 1.1)}
      viewBox="0 0 31 34"
      fill="none"
      aria-hidden
    >
      <path d="M2 28 13 5h6L8 28Z" fill="currentColor" />
      <path d="m17 15 10 13h-9l-5-7Z" fill="var(--a-accent)" />
      <path d="M20 5 30 28h-5L17 10Z" fill="currentColor" />
    </svg>
  );
}

/** Mark + wordmark ("adept."), linking home. */
export function BrandLogo({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className="a-brand" aria-label={label}>
      <BrandMark />
      <span>
        adept<span className="a-brand-dot">.</span>
      </span>
    </Link>
  );
}
