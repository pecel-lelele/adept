"use client";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { MetaBar } from "@/components/MetaBar";
import type { Schemas } from "@/lib/api";
import { DepthArt } from "./DepthArt";
type Preview = Schemas["GuestPreview"];
export function GuestPreviewView() {
  const [file, setFile] = useState<File | null>(null),
    [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [result, setResult] = useState<Preview | null>(null);
  function choose(next: File | undefined) {
    setResult(null);
    setError("");
    if (!next) return;
    if (
      next.size > 5 * 1024 * 1024 ||
      !["application/pdf", "text/plain"].includes(next.type)
    ) {
      setFile(null);
      setError("Choose a PDF or plain-text synthetic CV under 5 MB.");
      return;
    }
    setFile(next);
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose a synthetic CV first.");
      return;
    }
    const form = new FormData(event.currentTarget);
    form.set("file", file);
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch("/api/preview", {
        method: "POST",
        body: form,
      });
      if (!response.ok) {
        setError(
          "We could not analyse this file. Check the format or try again shortly.",
        );
        return;
      }
      setResult((await response.json()) as Preview);
    } catch {
      setError("Connection interrupted. Please try again.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="preview-page">
      <header>
        <Link className="workspace-brand" href="/">
          adept.
        </Link>
        <Link href="/auth/login?next=/app/profile">Open demo workspace ↗</Link>
      </header>
      <span className="workspace-eyebrow">EXPLORE BEFORE YOU COMMIT</span>
      <h1>Your skills have a next chapter.</h1>
      <p>
        Try a synthetic CV. Get one career preview before entering a workspace.
        No account, no saved document.
      </p>
      <div className="preview-grid">
        <form
          onSubmit={submit}
          className="preview-drop"
          data-dragging={drag}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            if (!busy) choose(e.dataTransfer.files[0]);
          }}
        >
          <DepthArt />
          <h2>Drop your synthetic CV here</h2>
          <label htmlFor="preview-file">PDF or plain text · up to 5 MB</label>
          <input
            id="preview-file"
            type="file"
            accept=".pdf,.txt"
            onChange={(e) => choose(e.target.files?.[0])}
            disabled={busy}
          />
          {file ? <p>Selected: {file.name}</p> : null}
          <label>
            <input
              type="checkbox"
              name="synthetic_consent"
              value="true"
              required
            />{" "}
            I confirm this is a synthetic CV with no real personal data.
          </label>
          <button disabled={busy} className="workspace-button">
            {busy ? "Reading your skills…" : "Preview my next step →"}
          </button>
          <p>
            Your upload is not added to a profile. Review extracted skills
            before using the result.
          </p>
        </form>
        <div className="preview-result" aria-live="polite" aria-busy={busy}>
          {error ? <p role="alert">{error}</p> : null}
          {result ? (
            <>
              <span className="workspace-eyebrow">PRELIMINARY PREVIEW</span>
              <h2>{result.top_role?.label ?? "No catalogue skills found"}</h2>
              {result.top_role ? (
                <p>
                  {Math.round(result.top_role.score * 100)}% estimated match ·{" "}
                  {Math.round(result.top_role.trend_coverage * 100)}% trend
                  coverage
                </p>
              ) : (
                <p>
                  Try a clearer synthetic CV or enter skills in the workspace.
                </p>
              )}
              <p>{result.skills.map((s) => s.label).join(" · ")}</p>
              {result.truncated ? (
                <p>The text was truncated. Review extracted skills.</p>
              ) : null}
              <MetaBar meta={result.meta} />
              <div className="preview-locked">
                {result.other_role_count} more options. Detailed skills gaps and
                learning plans open in a workspace. No hidden role details were
                sent to this page.
              </div>
              <Link
                className="workspace-button"
                href="/auth/login?next=/app/profile"
              >
                Review skills in a workspace →
              </Link>
              <p>
                Demo sign-in opens Aisyah’s synthetic profile. This upload is
                not copied into her account.
              </p>
            </>
          ) : (
            <>
              <span className="workspace-eyebrow">A SMALL FIRST STEP</span>
              <h2>Clarity before commitment.</h2>
              <p>
                See catalogue skills, one estimated role match, and dated
                sources. Confirm skills in a workspace before choosing a
                pathway.
              </p>
              <Link href="/app/courses">Browse courses ↗</Link>
            </>
          )}
        </div>
      </div>
      <p>
        <Link href="/">← Back to landing</Link> ·{" "}
        <Link href="/journey">Explore the full journey</Link>
      </p>
    </main>
  );
}
