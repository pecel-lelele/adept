import { Suspense, type ReactNode } from "react";
export default function Layout({ children }: { children: ReactNode }) {
  return (
    <Suspense
      fallback={<main className="preview-page">Opening your workspace…</main>}
    >
      {children}
    </Suspense>
  );
}
