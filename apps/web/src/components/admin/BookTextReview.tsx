"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { naskh } from "@/components/book/fonts";
import { Button } from "@/components/ui/Button";
import { api, errorText } from "@/lib/api";

/**
 * «نصوص الكتاب»: staff read and edit every word of a story book before «تأكيد» (API: routers/admin_books.py,
 * docs/plans/admin-story-text-review.md). Each text saves on its own and at once (with its history: who, when,
 * before and after); the print files follow with «إعادة إخراج الملفات», and «تأكيد» waits for them.
 */

export type StoryField = "title" | "dedication" | "parent_message" | "parents_lesson" | "parents_questions" | "blurb";

export type TextEdit = {
  id: string;
  field: string; // "page" or a story field
  beat: number | null;
  kind: "edit" | "revert";
  old_text: string | null;
  new_text: string | null;
  note: string | null;
  screen: string[];
  actor: string | null;
  created_at: string;
};

export type TextReviewBook = {
  id: string;
  status: string;
  language: string;
  flags: string[];
  child: { name: string; gender: string; age: number };
  story: {
    title?: string | null;
    dedication?: string | null;
    parents_lesson?: string | null;
    parents_questions?: string[] | null;
    blurb?: string | null;
  };
  parent_message: string | null;
  pages: {
    beat: number;
    pages: number[];
    text: string | null;
    original_text: string | null;
    has_image: boolean;
    flags: string[];
  }[];
  text_editable: boolean;
  text_originals: Partial<Record<StoryField, string | null>>;
  text_edits: TextEdit[];
  class_pages: { index: number; text: string | null }[];
};

type Row = {
  key: string;
  label: string;
  value: string;
  original: string | null;
  max: number;
  lines: number;
  field: StoryField | null; // null = a story page
  beat: number | null;
  image: boolean;
  byFamily: boolean; // the parent reworded it on the preview (before ordering)
};

const REASONS = new Set(["link", "phone", "unsafe_word"]);

/** The server folds runs of spaces (and, except in the questions, line breaks) the same way. */
function normalize(text: string, multiline: boolean): string {
  if (!multiline) return text.split(/\s+/).join(" ").trim();
  return text
    .split("\n")
    .map((line) => line.split(/\s+/).join(" ").trim())
    .filter(Boolean)
    .join("\n");
}

export function BookTextReview({
  book,
  thumb,
  busy,
  onSaved,
  onRerender,
  onError,
}: {
  book: TextReviewBook;
  thumb: (beat: number) => string;
  busy: boolean;
  onSaved: () => Promise<void>;
  onRerender: () => Promise<void>;
  onError: (text: string) => void;
}) {
  const t = useTranslations("queue");
  const locale = useLocale();
  const num = (n: number) => n.toLocaleString(locale === "ar" ? "ar-EG" : "en-US");
  const lang = book.language === "en" ? "en" : "ar";
  const generating = book.status === "generating";
  const editable = book.text_editable && !generating;
  const story = book.story;
  const originals = book.text_originals;
  const field = (key: StoryField, value: string, max: number, lines = 3): Row => ({
    key,
    label: t(`words.fields.${key}`),
    value,
    original: originals[key] ?? null,
    max,
    lines,
    field: key,
    beat: null,
    image: false,
    byFamily: false,
  });
  const rows: Row[] = [
    field("title", story.title ?? "", 200, 2),
    field("dedication", story.dedication ?? "", 1200, 2),
    field("parent_message", book.parent_message ?? "", 120, 2),
    ...book.pages
      .filter((p) => p.beat > 0)
      .map((p) => ({
        key: `page-${p.beat}`,
        label: p.pages.length
          ? p.pages.map((n) => t("page", { n: num(n) })).join(" – ")
          : t("beat", { n: num(p.beat) }),
        value: p.text ?? "",
        original: p.original_text,
        max: 600,
        lines: 3,
        field: null,
        beat: p.beat,
        image: p.has_image,
        byFamily: p.flags.includes("parent_edited"),
      })),
    field("parents_lesson", story.parents_lesson ?? "", 1200),
    field("parents_questions", (story.parents_questions ?? []).join("\n"), 1200),
    field("blurb", story.blurb ?? "", 1200),
  ];
  const historyOf = (row: Row) =>
    book.text_edits.filter((e) => (row.field ? e.field === row.field : e.field === "page" && e.beat === row.beat));

  return (
    <section
      className="flex flex-col gap-4 rounded-xl border border-line bg-paper-raised p-4"
      aria-labelledby="book-words"
    >
      <div className="flex flex-col gap-1">
        <h3 id="book-words" className="text-h3 text-night-900">
          {t("words.title")}
        </h3>
        <p className="text-small text-ink-muted">{t("words.intro")}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2 rounded-md bg-night-100 px-3 py-2 text-small">
        <strong className="text-night-900">{book.child.name}</strong>
        <span>·</span>
        <span>{t(`words.gender.${book.child.gender === "f" ? "f" : "m"}`)}</span>
        <span>·</span>
        <span>{t("words.age", { age: book.child.age })}</span>
        <span className="basis-full text-ink-muted">
          {t("words.grammar", { gender: book.child.gender === "f" ? "f" : "m" })}
        </span>
      </div>

      {book.flags.includes("text_changed") && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-warning/30 bg-warning-bg px-4 py-3 text-small text-warning">
          <span className="font-semibold">{t("words.changed")}</span>
          <Button size="sm" variant="solid" disabled={busy || generating} onClick={() => void onRerender()}>
            {t("rerender")}
          </Button>
        </div>
      )}
      {generating && <p className="text-small text-info">{t("words.locked")}</p>}

      {book.class_pages.length > 0 ? (
        <div className="flex flex-col gap-3">
          <p className="text-small text-ink-muted">{t("words.classReadOnly")}</p>
          <ol className="flex flex-col gap-2">
            {book.class_pages.map((p) => (
              <li key={p.index} className="flex flex-col gap-1 rounded-md border border-line p-3">
                <span className="text-caption font-semibold text-night-900">{t("beat", { n: num(p.index) })}</span>
                <p
                  dir={lang === "ar" ? "rtl" : "ltr"}
                  lang={lang}
                  className={`${lang === "ar" ? naskh.className : "font-body"} text-body-l leading-[1.9]`}
                >
                  {p.text || "—"}
                </p>
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <ul className="flex flex-col gap-4">
          {rows.map((row) => (
            <TextRow
              key={`${row.key}:${row.value}`}
              row={row}
              bookId={book.id}
              lang={lang}
              editable={editable}
              busy={busy}
              thumb={thumb}
              edits={historyOf(row)}
              onSaved={onSaved}
              onError={onError}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

function TextRow({
  row,
  bookId,
  lang,
  editable,
  busy,
  thumb,
  edits,
  onSaved,
  onError,
}: {
  row: Row;
  bookId: string;
  lang: "ar" | "en";
  editable: boolean;
  busy: boolean;
  thumb: (beat: number) => string;
  edits: TextEdit[];
  onSaved: () => Promise<void>;
  onError: (text: string) => void;
}) {
  const t = useTranslations("queue");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [value, setValue] = useState(row.value);
  const [saving, setSaving] = useState(false);
  const [flagged, setFlagged] = useState<string[] | null>(null);
  const [note, setNote] = useState("");
  const [history, setHistory] = useState(false);
  const multiline = row.field === "parents_questions";
  const dirty = normalize(value, multiline) !== normalize(row.value, multiline);
  const edited = row.original !== null && row.value !== row.original;
  const id = `words-${row.key}`;
  const textClass = `${lang === "ar" ? naskh.className : "font-body"} text-body-l leading-[1.9]`;
  const when = (iso: string) =>
    new Date(iso).toLocaleString(locale === "ar" ? "ar-EG" : "en-GB", { dateStyle: "medium", timeStyle: "short" });
  const base = `/api/admin/books/${bookId}`;

  async function save(withNote?: string) {
    setSaving(true);
    const json = { text: value, ...(withNote ? { note: withNote } : {}) };
    const res = row.field
      ? await api<unknown>(`${base}/story`, { method: "PATCH", json: { ...json, field: row.field } })
      : await api<unknown>(`${base}/pages/${row.beat}`, { method: "PATCH", json });
    setSaving(false);
    if (!res.ok && res.error?.code === "text_unsafe") {
      const reasons = res.error.details?.reasons;
      setFlagged(Array.isArray(reasons) ? reasons.map(String) : []);
      return;
    }
    if (!res.ok) return onError(errorText(res.error, locale, te("unknown")));
    await onSaved();
  }

  async function revert() {
    setSaving(true);
    const res = await api<unknown>(
      row.field ? `${base}/story/${row.field}/revert` : `${base}/pages/${row.beat}/revert`,
      {
        method: "POST",
        json: {},
      },
    );
    setSaving(false);
    if (!res.ok) return onError(errorText(res.error, locale, te("unknown")));
    await onSaved();
  }

  return (
    <li
      className={`grid gap-3 border-b border-line pb-4 last:border-0 ${row.beat !== null ? "md:grid-cols-[120px_1fr]" : ""}`}
    >
      {row.beat !== null && (
        <div className="aspect-square w-28 overflow-hidden rounded-md bg-night-100 md:w-full">
          {row.image && (
            // eslint-disable-next-line @next/next/no-img-element -- private image streamed by the admin API
            <img src={thumb(row.beat)} alt="" loading="lazy" className="h-full w-full object-cover" />
          )}
        </div>
      )}
      <div className="flex min-w-0 flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor={id} className="text-small font-semibold text-night-900">
            {row.label}
          </label>
          {edited && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-700">
              {t("words.edited")}
            </span>
          )}
          {row.byFamily && (
            <span className="rounded-full bg-lav-300/40 px-2 py-0.5 text-[11px] font-bold text-lav-700">
              {t("flags.parent_edited")}
            </span>
          )}
        </div>
        <textarea
          id={id}
          dir={lang === "ar" ? "rtl" : "ltr"}
          lang={lang}
          rows={row.lines}
          maxLength={row.max}
          value={value}
          readOnly={!editable}
          onChange={(e) => {
            setValue(e.target.value);
            setFlagged(null);
          }}
          className={`${textClass} rounded-sm border border-line bg-paper p-3 read-only:bg-paper-sunk`}
        />
        {flagged && (
          <div className="flex flex-col gap-2 rounded-md border border-danger/30 bg-danger-bg p-3 text-small text-danger">
            <span className="font-semibold">
              {t("words.flagged", {
                reasons: flagged
                  .filter((r) => REASONS.has(r))
                  .map((r) => t(`words.reasons.${r}`))
                  .join(locale === "ar" ? "، " : ", "),
              })}
            </span>
            <label htmlFor={`${id}-note`} className="text-ink">
              {t("words.note")}
            </label>
            <input
              id={`${id}-note`}
              value={note}
              maxLength={300}
              onChange={(e) => setNote(e.target.value)}
              className="min-h-11 rounded-sm border border-line bg-paper px-3 text-ink"
            />
            <div>
              <Button
                size="sm"
                variant="danger"
                disabled={saving || busy || !note.trim()}
                onClick={() => void save(note)}
              >
                {t("words.saveAnyway")}
              </Button>
            </div>
          </div>
        )}
        <div className="flex flex-wrap items-center gap-2">
          {editable && (
            <Button
              size="sm"
              variant="solid"
              disabled={saving || busy || !dirty || (!value.trim() && row.field !== "parent_message")}
              onClick={() => void save()}
            >
              {t("words.save")}
            </Button>
          )}
          {editable && edited && (
            <Button size="sm" variant="ghost" disabled={saving || busy} onClick={() => void revert()}>
              {t("words.revert")}
            </Button>
          )}
          {edits.length > 0 && (
            <button
              type="button"
              aria-expanded={history}
              onClick={() => setHistory((h) => !h)}
              className="min-h-11 text-small text-night-700 underline underline-offset-4"
            >
              {t("words.history", { n: edits.length })}
            </button>
          )}
        </div>
        {history && (
          <ol className="flex flex-col gap-2">
            {edits.map((e) => (
              <li key={e.id} className="flex flex-col gap-1 rounded-md bg-paper-sunk p-3 text-small">
                <span className="text-caption text-ink-muted">
                  {t(`words.kind.${e.kind}`)} · {e.actor ?? "—"} · {when(e.created_at)}
                </span>
                <span className="text-caption font-semibold">{t("words.before")}</span>
                <p dir={lang === "ar" ? "rtl" : "ltr"} lang={lang} className={`${textClass} whitespace-pre-line`}>
                  {e.old_text || "—"}
                </p>
                <span className="text-caption font-semibold">{t("words.after")}</span>
                <p dir={lang === "ar" ? "rtl" : "ltr"} lang={lang} className={`${textClass} whitespace-pre-line`}>
                  {e.new_text || "—"}
                </p>
                {e.note && <span className="text-caption text-warning">{t("words.noteKept", { note: e.note })}</span>}
              </li>
            ))}
          </ol>
        )}
      </div>
    </li>
  );
}
