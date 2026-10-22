"use client";

import { ArrowUp, ShieldCheck, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import type { components } from "@/lib/api/types";

import { Adi3D } from "./Adi3D";
import type { AdiMood } from "./AdiMascot";

type Reply = components["schemas"]["AssistantReply"];
type Part = components["schemas"]["AnswerPart"];
type Turn = { role: "user"; text: string } | { role: "assistant"; reply: Reply } | { role: "error"; text: string };

/** Saved chats are kept per account, so a different person in the same tab never sees them. */
const STORE_PREFIX = "adept.adi.chat.";
const SEEN = "adept.adi.seen";
const MAX_CHARS = 600;

function load<T>(key: string, fallback: T): T {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function save(key: string, value: unknown): void {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* private mode or full storage: the chat still works for this page */
  }
}

/** Plain text of a reply, sent back as conversation history. */
function asText(reply: Reply): string {
  return reply.parts.map((p) => p.text).join("");
}

/**
 * Adi, the Adept guide: docked bottom-right on the landing page and in every workspace.
 * Answers come from the person's own Adept data (or public figures for visitors) and are
 * checked by the API: every role, skill, course and page Adi names is a real catalogue entry.
 */
export function AdiAssistant({
  placement = "workspace",
  who,
}: {
  placement?: "workspace" | "landing";
  /** Signed-in account id; omitted for visitors. */
  who?: string;
}) {
  const store = STORE_PREFIX + (who ?? "visitor");
  const t = useTranslations("ui.adi");
  const locale = useLocale();
  const path = usePathname();
  const params = useSearchParams();
  const scenario = params.get("scenario") === "fast" ? "fast" : "moderate";
  const [open, setOpen] = useState(false);
  const [bubble, setBubble] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [mood, setMood] = useState<AdiMood>("wave");
  const list = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // Drop chats saved for anyone else in this tab (after sign-out or an account switch).
    try {
      for (const key of Object.keys(sessionStorage)) {
        if ((key.startsWith(STORE_PREFIX) || key === "adept.adi.chat") && key !== store) {
          sessionStorage.removeItem(key);
        }
      }
    } catch {
      /* storage unavailable: nothing was saved either */
    }
  }, [store]);

  useEffect(() => {
    const seen = load<boolean>(SEEN, false);
    const show = window.setTimeout(() => setBubble(!seen), 1400);
    const calm = window.setTimeout(() => setMood("idle"), 3600);
    return () => {
      window.clearTimeout(show);
      window.clearTimeout(calm);
    };
  }, []);

  useEffect(() => {
    if (turns.length) save(store, turns.slice(-12));
  }, [turns, store]);
  useEffect(() => {
    list.current?.scrollTo({ top: list.current.scrollHeight, behavior: "smooth" });
  }, [turns, busy]);
  useEffect(() => {
    if (!open) return;
    input.current?.focus();
    const onKey = (e: globalThis.KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  function openPanel() {
    // Earlier questions from this browser tab come back when the panel opens.
    if (!turns.length) setTurns(load<Turn[]>(store, []));
    setOpen(true);
    setBubble(false);
    save(SEEN, true);
  }

  async function ask(question: string) {
    const text = question.trim().slice(0, MAX_CHARS);
    if (!text || busy) return;
    const history = [...turns, { role: "user", text } as Turn];
    setTurns(history);
    setDraft("");
    setBusy(true);
    setMood("think");
    const messages = history
      .filter((turn): turn is Exclude<Turn, { role: "error" }> => turn.role !== "error")
      .slice(-8)
      .map((turn) =>
        turn.role === "user" ? { role: "user", content: turn.text } : { role: "assistant", content: asText(turn.reply).slice(0, 1200) },
      );
    try {
      const response = await fetch("/api/assistant", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ messages, page: path, scenario, locale }),
      });
      const json: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        const message = (json as { error?: { message?: string } } | null)?.error?.message ?? t("error");
        setTurns((prev) => [...prev, { role: "error", text: response.status === 429 ? t("slowDown") : message }]);
        setMood("idle");
      } else {
        setTurns((prev) => [...prev, { role: "assistant", reply: json as Reply }]);
        setMood("talk");
        window.setTimeout(() => setMood("idle"), 1800);
      }
    } catch {
      setTurns((prev) => [...prev, { role: "error", text: t("error") }]);
      setMood("idle");
    } finally {
      setBusy(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    void ask(draft);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void ask(draft);
    }
  }

  // Intake is a focused form: Adi stays out of the way there.
  if (path.startsWith("/app/onboarding")) return null;

  const lastReply = [...turns].reverse().find((turn) => turn.role === "assistant") as { reply: Reply } | undefined;
  const suggestions = lastReply?.reply.suggestions ?? [t("s1"), t("s2"), t("s3")];

  return (
    <div className="adi-dock" data-placement={placement} data-open={open}>
      {open ? (
        <section className="adi-panel" role="dialog" aria-modal="false" aria-label={t("title")}>
          <header className="adi-head">
            <Adi3D size={58} mood={busy ? "think" : mood === "wave" ? "idle" : mood} follow={false} />
            <div>
              <strong>{t("title")}</strong>
              <span>{busy ? t("thinking") : t("subtitle")}</span>
            </div>
            <button type="button" className="adi-icon" onClick={() => setOpen(false)} aria-label={t("close")}>
              <X size={18} aria-hidden />
            </button>
          </header>
          <div className="adi-log" ref={list} aria-live="polite">
            <div className="adi-msg is-adi">
              <p>{t("greet")}</p>
            </div>
            {turns.map((turn, i) =>
              turn.role === "user" ? (
                <div key={i} className="adi-msg is-me">
                  <p>{turn.text}</p>
                </div>
              ) : turn.role === "error" ? (
                <div key={i} className="adi-msg is-adi is-error" role="alert">
                  <p>{turn.text}</p>
                </div>
              ) : (
                <Answer key={i} reply={turn.reply} scenario={scenario} />
              ),
            )}
            {busy ? (
              <div className="adi-msg is-adi is-typing" aria-label={t("thinking")}>
                <span />
                <span />
                <span />
              </div>
            ) : null}
          </div>
          <div className="adi-suggest">
            {suggestions.map((s) => (
              <button key={s} type="button" onClick={() => void ask(s)} disabled={busy}>
                {s}
              </button>
            ))}
          </div>
          <form className="adi-form" onSubmit={submit}>
            <textarea
              ref={input}
              value={draft}
              onChange={(e) => setDraft(e.target.value.slice(0, MAX_CHARS))}
              onKeyDown={onKeyDown}
              placeholder={t("placeholder")}
              rows={1}
              aria-label={t("placeholder")}
            />
            <button type="submit" className="adi-send" disabled={busy || !draft.trim()} aria-label={t("send")}>
              <ArrowUp size={18} aria-hidden />
            </button>
          </form>
          <p className="adi-foot">
            <ShieldCheck size={12} aria-hidden /> {t("disclaimer")}
          </p>
        </section>
      ) : (
        <>
          {bubble ? (
            <div className="adi-callout">
              <button type="button" className="adi-bubble" data-tail="right" onClick={openPanel}>
                {placement === "landing" ? t("askVisitor") : t("ask")}
              </button>
              <button
                type="button"
                className="adi-dismiss"
                aria-label={t("dismiss")}
                onClick={() => {
                  setBubble(false);
                  save(SEEN, true);
                }}
              >
                <X size={12} aria-hidden />
              </button>
            </div>
          ) : null}
          <button type="button" className="adi-launch" onClick={openPanel} aria-label={t("open")}>
            <Adi3D size={86} mood={mood} />
          </button>
        </>
      )}
    </div>
  );
}

function Answer({ reply, scenario }: { reply: Reply; scenario: "moderate" | "fast" }) {
  const t = useTranslations("ui.adi");
  const meta = reply.meta;
  const unchecked = reply.unchecked_figures ?? [];
  const grounded = reply.grounded_on ?? [];
  return (
    <div className="adi-msg is-adi">
      <p>
        {reply.parts.map((part, i) => (
          <PartView key={i} part={part} scenario={scenario} />
        ))}
      </p>
      {unchecked.length ? (
        <small className="adi-warn">{t("unchecked", { figures: unchecked.join(", ") })}</small>
      ) : null}
      <small className="adi-meta">
        {reply.used_llm ? t("byModel", { model: reply.model }) : t("byGuide")}
        {grounded.length ? ` · ${t("basedOn", { what: grounded.join(", ") })}` : ""}
        {meta ? ` · ${t("snapshot", { date: meta.snapshot_date })}` : ""}
      </small>
    </div>
  );
}

function PartView({ part, scenario }: { part: Part; scenario: "moderate" | "fast" }) {
  if (part.kind === "text") {
    // Models emphasise with **bold**; render it as <strong> and keep the rest plain text.
    const pieces = part.text.replace(/^[-*] /gm, "• ").split(/\*\*(.+?)\*\*/g);
    return <>{pieces.map((piece, i) => (i % 2 ? <strong key={i}>{piece}</strong> : piece))}</>;
  }
  const label = <span className={`adi-ref is-${part.kind}`}>{part.text}</span>;
  if (!part.href) return label;
  if (part.href.startsWith("/")) {
    // Adi answered with this scenario's data; the link must open the same scenario.
    const href = scenario === "fast" && /^\/(app|org)(\/|$)/.test(part.href) ? `${part.href}?scenario=fast` : part.href;
    return (
      <Link href={href} className="adi-reflink">
        {label}
      </Link>
    );
  }
  return (
    <a href={part.href} target="_blank" rel="noopener noreferrer" className="adi-reflink">
      {label}
    </a>
  );
}
