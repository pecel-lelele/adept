"use client";

import { CircleAlert, RotateCw } from "lucide-react";
import Link from "next/link";

/** Also works outside the root layout, without router or translation providers. */
export function RouteErrorState({ title, description, home, retryLabel, retry }: {
  title: string;
  description: string;
  home: string;
  retryLabel?: string;
  retry?: () => void;
}) {
  return (
    <main className="a-page a-route-error">
      <section className="a-card">
        <div className="a-empty" role="alert">
          <span className="a-empty-icon"><CircleAlert size={24} aria-hidden /></span>
          <h1 className="a-h2">{title}</h1>
          <p>{description}</p>
          <div className="a-chips">
            {retry ? <button className="a-btn is-ghost is-small" type="button" onClick={retry}><RotateCw size={14} aria-hidden /> {retryLabel}</button> : null}
            {/* Link retains its native href when the global fallback has no router. */}
            <Link className="a-btn is-small" href="/" prefetch={false}>{home}</Link>
          </div>
        </div>
      </section>
    </main>
  );
}
