"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { safeReturn } from "@/lib/navigation";
import { DepthArt } from "./DepthArt";
export function AuthView({
  page,
}: {
  page: "login" | "signup" | "consent" | "join";
}) {
  const params = useSearchParams();
  const [mode, setMode] = useState<"individual" | "organisation">(
    params.get("mode") === "organisation" ||
      params.get("next")?.startsWith("/org")
      ? "organisation"
      : "individual",
  );
  const [consent, setConsent] = useState(false);
  const next = safeReturn(params.get("next"), mode);
  return (
    <main className="preview-page">
      <header>
        <Link className="workspace-brand" href="/">
          adept.
        </Link>
        <Link href="/try">Try a CV preview ↗</Link>
      </header>
      <span className="workspace-eyebrow">YOUR NEXT CHAPTER STARTS HERE</span>
      <h1>
        {page === "consent"
          ? "You stay in control."
          : "Find your space to grow."}
      </h1>
      <div className="preview-grid">
        <section className="preview-result">
          <h2>Choose your demo workspace</h2>
          <p>
            Use a synthetic persona to explore Adept. Account creation and
            organisation invitation codes are not connected yet.
          </p>
          <label>
            Workspace
            <select
              className="route-node"
              value={mode}
              onChange={(e) =>
                setMode(
                  e.target.value === "organisation"
                    ? "organisation"
                    : "individual",
                )
              }
            >
              <option value="individual">Individual · Aisyah</option>
              <option value="organisation">Organisation · Demo Bank HR</option>
            </select>
          </label>
          <label>
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />{" "}
            I understand this is a synthetic demo, projections are estimates,
            and I make the final decisions.
          </label>
          {consent ? (
            <a
              className="workspace-button"
              href={`/demo/${mode === "organisation" ? "org" : "learner"}?next=${encodeURIComponent(next)}`}
            >
              Enter demo workspace →
            </a>
          ) : (
            <button className="workspace-button" disabled>
              Confirm above to continue
            </button>
          )}
          <Link href="/about">Read about our sources and AI use ↗</Link>
        </section>
        <section className="preview-result">
          <DepthArt variant={mode === "organisation" ? "people" : "steps"} />
          <h2>
            {mode === "organisation"
              ? "Help your people take the next step."
              : "Build a learning journey around you."}
          </h2>
          <p>
            {mode === "organisation"
              ? "Explore team skills, group learning plans, and evidence review."
              : "Compare roles, build a pathway, and follow your learning progress."}
          </p>
        </section>
      </div>
    </main>
  );
}
