"use client";

import { Check, Copy, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState, useTransition } from "react";

import { errorMessage } from "@/lib/api/error-message";

import { rotateCodeAction } from "../actions";

/** The organisation's join code with copy-link and rotate actions (managers only). */
export function JoinCodeCard({ code, orgId }: { code: string; orgId?: string }) {
  const t = useTranslations("ui.org");
  const te = useTranslations("ui.apiErrors");
  const [copied, setCopied] = useState(false);
  const [pending, start] = useTransition();
  const [error, setError] = useState("");

  async function copy() {
    const link = `${window.location.origin}/auth/join?code=${encodeURIComponent(code)}`;
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setError(link);
    }
  }

  return (
    <div className="a-stack" style={{ gap: 10 }}>
      <span className="a-eyebrow">{t("code")}</span>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <strong style={{ fontSize: 30, letterSpacing: 6, fontVariantNumeric: "tabular-nums" }}>{code}</strong>
        <button type="button" className="a-btn is-small" onClick={copy}>
          {copied ? <Check size={14} aria-hidden /> : <Copy size={14} aria-hidden />}
          {copied ? t("copied") : t("copy")}
        </button>
        <button
          type="button"
          className="a-btn is-ghost is-small"
          disabled={pending}
          onClick={() =>
            start(async () => {
              const result = await rotateCodeAction(orgId);
              if (result.error) setError(errorMessage(te, result.error));
            })
          }
        >
          <RefreshCw size={14} aria-hidden /> {t("newCode")}
        </button>
      </div>
      {error ? <p className="a-small a-muted" style={{ margin: 0, wordBreak: "break-all" }}>{error}</p> : null}
    </div>
  );
}
