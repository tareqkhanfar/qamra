"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import { createApi, type Child } from "@/lib/create";
import { ACTIVITY_LINES } from "@/lib/shop";
import { Frame } from "./Frame";

const POINTS = ["p1", "p2", "p3", "p4"] as const;

/**
 * Step 2 (design Create2): the guardian's consent, stored with the version of this exact text. Shown only when a
 * photo is needed; the line above the promises says what the photo is for in this product (a story's hero, or
 * the character on an activity book's cover and chosen pages). The promises and the box are the versioned text.
 */
export function ConsentStep({
  child,
  productLine = null,
  title,
  back,
  onDone,
}: {
  child: Child;
  productLine?: string | null; // classic|magic|workbook|journey|family|islamic (null: a story, type not chosen)
  title?: string; // the frame title; the wizard's FlowFrameContext wins when present
  back: () => void;
  onDone: (c: Child) => void;
}) {
  const t = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const who = { ...nameCases(child.name), gender: child.gender };
  const activity = (ACTIVITY_LINES as readonly string[]).includes(productLine ?? "");

  async function submit() {
    if (!accepted) {
      setError(t("consent.required"));
      return;
    }
    setBusy(true);
    setError(null);
    const r = await createApi.consent(child.id, t("consent.version"));
    setBusy(false);
    if (r.ok) onDone(r.data);
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  return (
    <Frame
      title={title ?? t("bookOf", who)}
      label={t("steps.consent")}
      back={back}
      footer={
        <Button onClick={submit} loading={busy} size="lg" className="grow">
          {t("consent.cta")}
        </Button>
      }
    >
      <div className="flex items-center gap-3.5">
        <div className="flex size-16 shrink-0 items-center justify-center rounded-[20px] bg-success-bg">
          <svg className="size-8 text-success" viewBox="0 0 24 24" aria-hidden="true">
            <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" />
              <path d="M9 12l2 2 4-4" />
            </g>
          </svg>
        </div>
        <h1 className="text-[26px] leading-snug text-night-900">{t("consent.title", who)}</h1>
      </div>
      <p className="text-body text-ink-muted">
        {t(activity ? "consent.why.activity" : "consent.why.story", who)} {t("consent.next")}
      </p>

      <ol className="flex flex-col gap-3">
        {POINTS.map((p, i) => (
          <li key={p} className="flex gap-3 rounded-2xl border border-line bg-paper-raised p-4">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-[10px] bg-night-100 font-bold text-night-900">
              {i + 1}
            </span>
            <div className="flex flex-col gap-0.5">
              <strong className="text-body">{t(`consent.${p}.title`)}</strong>
              <span className="text-small text-ink-muted">{t(`consent.${p}.body`, who)}</span>
            </div>
          </li>
        ))}
      </ol>
      <Link
        href="/privacy"
        target="_blank"
        className="flex min-h-11 items-center text-body font-semibold text-night-900 underline underline-offset-4"
      >
        {t("consent.privacy")}
      </Link>

      <label
        className={`flex cursor-pointer items-start gap-3 rounded-2xl p-4 text-body ${accepted ? "border-2 border-night-900 bg-night-100" : "border-[1.5px] border-line bg-paper-raised"}`}
      >
        <input
          type="checkbox"
          checked={accepted}
          onChange={(e) => setAccepted(e.target.checked)}
          className="mt-0.5 size-6 shrink-0 accent-night-900"
        />
        <span>{t.rich("consent.accept", { ...who, b: (chunks) => <strong>{chunks}</strong> })}</span>
      </label>

      {error && <Alert>{error}</Alert>}
    </Frame>
  );
}
