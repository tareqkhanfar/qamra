"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { api, errorText } from "@/lib/api";
import {
  brokenPlaceholders,
  renderText,
  type TextContext,
  type TextPage,
  type VersionDetail,
  type Words,
} from "@/lib/studio";
import { inputClass } from "./parts";

type Message = { ok: boolean; text: string; problems?: string[] } | null;
const TOKENS = { ar: ["{name}", "{companion}", "{مذكر/مؤنث}"], en: ["{name}", "{companion}", "{he/she}"] };

/**
 * A page's words (Addendum 4 §3.3): the Arabic with its {boy/girl} variants and the English, from the theme.
 * Saving lands in the theme's open draft (a new version, made from the live one when needed, and audited);
 * a template's own words change only after that version goes live and its texts are refreshed. Each form is
 * shown with a sample child of its gender. `onThemePage`: the editor sits on the theme's versions page.
 */
export function PageTextEditor({
  texts,
  page,
  words,
  setWords,
  onSaved,
  onThemePage = false,
}: {
  texts: TextContext;
  page: TextPage;
  words: Words;
  setWords: (w: Words) => void;
  onSaved: () => Promise<void>;
  onThemePage?: boolean;
}) {
  const t = useTranslations("studio.text");
  const te = useTranslations("errors");
  const locale = useLocale();
  const fields = { ar: useRef<HTMLTextAreaElement>(null), en: useRef<HTMLTextAreaElement>(null) };
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<Message>(null);
  const dirty = words.ar !== page.current.ar || words.en !== page.current.en;
  const broken = brokenPlaceholders(words.ar) || brokenPlaceholders(words.en);
  const pending = !!texts.editing && texts.editing.status !== "draft"; // in review or approved: read-only

  if (page.beat === 0) {
    return (
      <section className="flex flex-col gap-2 rounded-xl border border-line bg-paper-raised p-4">
        <h3 className="text-h3 text-night-900">{t("coverTitle")}</h3>
        <p dir="rtl">{page.current.ar}</p>
        <p dir="ltr">{page.current.en}</p>
        <p className="text-caption text-ink-muted">{t("coverNote")}</p>
      </section>
    );
  }

  function insert(lang: "ar" | "en", token: string) {
    const el = fields[lang].current;
    if (!el) return;
    const start = el.selectionStart ?? el.value.length;
    const end = el.selectionEnd ?? start;
    setWords({ ...words, [lang]: el.value.slice(0, start) + token + el.value.slice(end) });
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(start + token.length, start + token.length);
    });
  }

  async function save() {
    setBusy(true);
    setMessage(null);
    const body = {
      ...(words.ar !== page.current.ar ? { text_ar: words.ar } : {}),
      ...(words.en !== page.current.en ? { text_en: words.en } : {}),
      ...(note.trim() ? { note: note.trim() } : {}),
    };
    const r = await api<VersionDetail>(`/api/admin/themes/${texts.theme}/pages/${page.beat}/text`, {
      method: "PUT",
      json: body,
    });
    setBusy(false);
    if (!r.ok) {
      const problems = r.error?.details?.problems as string[] | undefined;
      setMessage({ ok: false, text: errorText(r.error, locale, te("unknown")), problems });
      return;
    }
    setNote("");
    setMessage({ ok: true, text: t(onThemePage ? "savedTheme" : "saved", { version: r.data.version }) });
    await onSaved();
  }

  const companion = texts.sample.companion_ar;
  const editing = texts.editing ? t("editing", { version: texts.editing.version }) : t("newDraft");
  return (
    <section
      className="flex flex-col gap-3 rounded-xl border border-line bg-paper-raised p-4"
      aria-labelledby="page-words"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id="page-words" className="text-h3 text-night-900">
          {t("title")}
        </h3>
        {onThemePage ? (
          <span className="text-small text-ink-muted">{editing}</span>
        ) : (
          <Link href={`/admin/studio/themes?theme=${texts.theme}`} className="text-small text-night-700 underline">
            {editing}
          </Link>
        )}
      </div>
      {pending && texts.editing && <Alert tone="info">{t("pending", { version: texts.editing.version })}</Alert>}
      {(["ar", "en"] as const).map((lang) => (
        <div key={lang} className="flex flex-col gap-1.5">
          <label htmlFor={`words-${lang}`} className="text-small font-semibold">
            {t(`label.${lang}`)}
          </label>
          <textarea
            id={`words-${lang}`}
            ref={fields[lang]}
            dir={lang === "ar" ? "rtl" : "ltr"}
            rows={lang === "ar" ? 4 : 3}
            value={words[lang]}
            onChange={(e) => setWords({ ...words, [lang]: e.target.value })}
            className={`${inputClass} py-2 leading-relaxed`}
          />
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-caption text-ink-muted">{t("insert")}</span>
            {TOKENS[lang].map((token) => (
              <button
                key={token}
                type="button"
                onClick={() => insert(lang, token)}
                className="min-h-9 rounded-full border border-line bg-paper-sunk px-3 text-caption"
                dir="ltr"
              >
                {token}
              </button>
            ))}
          </div>
          {lang === "ar" && (
            <dl className="grid gap-1 rounded-md bg-paper-sunk p-2 text-small">
              {(["m", "f"] as const).map((g) => (
                <div key={g} className="flex gap-2">
                  <dt className="shrink-0 font-semibold text-ink-muted">{t(`gender.${g}`)}</dt>
                  <dd dir="rtl">{renderText(words.ar, g, texts.names[g].ar, companion)}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      ))}
      <label className="flex flex-col gap-1 text-small font-semibold">
        {t("note")}
        <input value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} className={inputClass} />
      </label>
      {broken && <Alert>{t("broken")}</Alert>}
      {message && (
        <Alert tone={message.ok ? "success" : "error"}>
          {message.text}
          {message.problems && (
            <ul className="mt-1 list-disc ps-5">
              {message.problems.map((p) => (
                <li key={p} dir="ltr">
                  {p}
                </li>
              ))}
            </ul>
          )}
        </Alert>
      )}
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={() => void save()} disabled={!dirty || broken || pending} loading={busy}>
          {t("save")}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setWords(page.current)} disabled={!dirty}>
          {t("reset")}
        </Button>
      </div>
    </section>
  );
}
