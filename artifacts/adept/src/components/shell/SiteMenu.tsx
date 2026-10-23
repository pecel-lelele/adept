"use client";

import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type ReactNode } from "react";

/** Phone menu for the public header: an animated hamburger that opens a panel of links. */
export function SiteMenu({ children }: { children: ReactNode }) {
  const t = useTranslations("ui.nav");
  const pathname = usePathname();
  const [openedAt, setOpenedAt] = useState<string | null>(null);
  const open = openedAt === pathname;
  const button = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    panel.current?.querySelector<HTMLElement>("a, button")?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpenedAt(null);
        button.current?.focus();
      }
    };
    const onDown = (e: PointerEvent) => {
      const target = e.target as Node;
      if (!panel.current?.contains(target) && !button.current?.contains(target)) setOpenedAt(null);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [open]);

  return (
    <div className="a-menu">
      <button
        ref={button}
        type="button"
        className="a-burger"
        aria-expanded={open}
        aria-controls="a-site-menu"
        aria-label={open ? t("close") : t("menu")}
        onClick={() => setOpenedAt(open ? null : pathname)}
      >
        <span aria-hidden />
        <span aria-hidden />
        <span aria-hidden />
      </button>
      <div
        ref={panel}
        id="a-site-menu"
        className="a-menu-panel"
        data-open={open}
        hidden={!open}
        onClick={(e) => {
          if ((e.target as HTMLElement).closest("a")) setOpenedAt(null);
        }}
      >
        {children}
      </div>
    </div>
  );
}
