import type { ReactNode } from "react";

import { AuthView } from "@/features/core";

/**
 * Sign in and Create account share this layout, so the auth panel stays mounted when switching
 * between them: the tab pill slides and the form cross-fades instead of the page reloading.
 */
export default function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <AuthView />
      {children}
    </>
  );
}
