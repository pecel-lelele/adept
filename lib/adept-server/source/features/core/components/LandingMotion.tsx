"use client";

import { useEffect } from "react";

/**
 * Small motion layer for the public home: sections fade up as they scroll in, numbers marked
 * `data-count` count up once, and `.a-tilt` figures lean toward the pointer. Content is fully
 * visible without JavaScript; everything is skipped for reduced-motion users.
 */
export function LandingMotion() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const root = document.documentElement;
    root.classList.add("a-motion");

    const countUp = (el: HTMLElement) => {
      const target = Number(el.dataset.count);
      if (!Number.isFinite(target) || el.dataset.counted) return;
      el.dataset.counted = "1";
      const start = performance.now();
      const tick = (now: number) => {
        const k = Math.min(1, (now - start) / 1100);
        el.textContent = String(Math.round(target * (1 - Math.pow(1 - k, 3))));
        if (k < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };

    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const el = entry.target as HTMLElement;
          el.dataset.shown = "true";
          el.querySelectorAll<HTMLElement>("[data-count]").forEach(countUp);
          if (el.dataset.count) countUp(el);
          io.unobserve(el);
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -8% 0px" },
    );
    const watch = () =>
      document.querySelectorAll<HTMLElement>("[data-reveal]:not([data-shown]), [data-count]:not([data-counted])").forEach((el) => io.observe(el));
    watch();
    // Steps and audience views swap content; pick up new numbers and reveals as they appear.
    const mo = new MutationObserver(watch);
    mo.observe(document.body, { childList: true, subtree: true });

    const tilts = Array.from(document.querySelectorAll<HTMLElement>(".a-tilt"));
    const onMove = (e: PointerEvent) => {
      for (const el of tilts) {
        const r = el.getBoundingClientRect();
        if (r.bottom < 0 || r.top > innerHeight) continue;
        const x = (e.clientX - (r.left + r.width / 2)) / innerWidth;
        const y = (e.clientY - (r.top + r.height / 2)) / innerHeight;
        el.style.setProperty("--ry", `${(x * 8).toFixed(2)}deg`);
        el.style.setProperty("--rx", `${(-y * 6).toFixed(2)}deg`);
      }
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      io.disconnect();
      mo.disconnect();
      window.removeEventListener("pointermove", onMove);
      root.classList.remove("a-motion");
    };
  }, []);
  return null;
}
