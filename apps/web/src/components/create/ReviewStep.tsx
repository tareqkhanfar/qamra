"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { createApi, pageImage, type Book, type Child } from "@/lib/create";
import { Frame } from "./Frame";

const SOFT_LIMIT = 180;

/** Step 9 (design Create7): the preview pages and every page's words, which the parent may reword. */
export function ReviewStep({
  child,
  book,
  back,
  onChange,
  onDone,
}: {
  child: Child;
  book: Book;
  back: () => void;
  onChange: (b: Book) => void;
  onDone: () => void;
}) {
  const t = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const pages = book.pages.filter((p) => p.beat === 0 || p.text);
  const [beat, setBeat] = useState(pages.find((p) => p.beat > 0)?.beat ?? 0);
  const [original] = useState(() => new Map(book.pages.map((p) => [p.beat, p.text ?? ""])));
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const page = book.pages.find((p) => p.beat === beat);
  const text = drafts[beat] ?? page?.text ?? "";
  const changed = text.trim() !== (page?.text ?? "").trim();

  async function save(value: string) {
    setBusy(true);
    setError(null);
    const r = await createApi.editPage(book.id, beat, value);
    setBusy(false);
    if (!r.ok) {
      setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
      return;
    }
    onChange(r.data);
    setDrafts((d) => {
      const next = { ...d };
      delete next[beat];
      return next;
    });
    setSaved(beat);
  }

  const label = (n: number) => (n === 0 ? t("review.cover") : t("review.page", { n }));
  return (
    <Frame
      title={book.title ?? t("bookOf", { name: child.name })}
      label={t("steps.review")}
      n={9}
      back={back}
      footer={
        <Button onClick={onDone} size="lg" className="grow" disabled={busy}>
          {t("review.cta")}
        </Button>
      }
    >
      <p className="flex items-start gap-2.5 rounded-2xl bg-night-100 p-3.5 text-small text-night-900">
        <svg className="mt-0.5 size-5 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
          <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 8h.01M11 12h1v4h1" />
          </g>
        </svg>
        {t("review.body")}
      </p>

      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
        {pages.map((p) => (
          <button
            key={p.beat}
            type="button"
            aria-label={label(p.beat)}
            aria-current={p.beat === beat}
            onClick={() => {
              setBeat(p.beat);
              setSaved(null);
            }}
            className={`flex w-[72px] shrink-0 flex-col items-center gap-1 rounded-xl bg-paper-raised p-1 ${p.beat === beat ? "border-2 border-night-900" : "border border-line"}`}
          >
            <div className="flex aspect-square w-full items-center justify-center overflow-hidden rounded-lg bg-paper-sunk">
              {p.image ? (
                // eslint-disable-next-line @next/next/no-img-element -- private preview through the API
                <img src={pageImage(book.id, p.beat)} alt="" className="size-full object-cover" loading="lazy" />
              ) : (
                <span className="text-caption text-ink-faint" aria-hidden="true">
                  ✎
                </span>
              )}
            </div>
            <span className="text-caption">{p.beat === 0 ? t("review.cover") : p.beat}</span>
          </button>
        ))}
      </div>

      <section
        aria-label={label(beat)}
        className="flex flex-col gap-3 rounded-3xl border border-line bg-paper-raised p-3"
      >
        <div className="relative flex aspect-[16/10] items-center justify-center overflow-hidden rounded-2xl bg-paper-sunk">
          {page?.image ? (
            // eslint-disable-next-line @next/next/no-img-element -- private preview through the API
            <img src={pageImage(book.id, beat)} alt="" className="size-full object-cover" />
          ) : (
            <span className="text-small text-ink-muted">{t("review.later")}</span>
          )}
          <span className="absolute start-2.5 top-2.5 rounded-full bg-night-950/80 px-2.5 py-1 text-caption font-semibold text-paper">
            {label(beat)} · {t("review.draft")}
          </span>
        </div>
        {beat > 0 && page && (
          <div className="flex flex-col gap-1.5 px-1 pb-1">
            <label htmlFor="page-text" className="text-small font-semibold">
              {t("review.text")}
            </label>
            <textarea
              id="page-text"
              rows={4}
              maxLength={280}
              value={text}
              onChange={(e) => {
                const value = e.target.value;
                setDrafts((d) => ({ ...d, [beat]: value }));
                setSaved(null);
              }}
              className="rounded-[14px] border-[1.5px] border-line bg-white px-3.5 py-3 text-body-l leading-loose outline-none focus:border-night-900 focus:ring-4 focus:ring-night-100"
            />
            <div className="flex justify-between text-caption text-ink-muted">
              <span>{t("review.limit")}</span>
              <span className={text.length > SOFT_LIMIT ? "font-bold text-amber-700" : ""} dir="ltr">
                {text.length} / {SOFT_LIMIT}
              </span>
            </div>
            <div className="flex flex-wrap gap-2 pt-1">
              <Button size="sm" onClick={() => save(text)} loading={busy} disabled={!changed || !text.trim()}>
                {t("review.save")}
              </Button>
              {(original.get(beat) ?? "") !== (page.text ?? "") && (
                <Button size="sm" variant="ghost" onClick={() => save(original.get(beat) ?? "")} disabled={busy}>
                  {t("review.restore")}
                </Button>
              )}
              {saved === beat && !changed && (
                <span role="status" className="flex items-center text-small font-semibold text-success">
                  ✓ {t("review.saved")}
                </span>
              )}
            </div>
          </div>
        )}
      </section>
      {error && <Alert>{error}</Alert>}
    </Frame>
  );
}
