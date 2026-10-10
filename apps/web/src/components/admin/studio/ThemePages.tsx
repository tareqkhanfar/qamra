"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { api, errorText } from "@/lib/api";
import type { ThemeTexts, Words } from "@/lib/studio";
import { PagePreview } from "./PagePreview";
import { PageTextEditor } from "./PageTextEditor";

/**
 * A theme's own pages (Addendum 4 §3.3), with or without Classic templates: pick a page, edit its words (the
 * Arabic with its boy/girl forms, and the English) into the theme's open draft, and preview it for a sample
 * boy or girl in the book's text panel. A «قريبًا» story has no pages yet: it says so. `stamp` changes when a
 * version moves (published, discarded…), and the words are read again.
 */
export function ThemePages({ slug, stamp, onSaved }: { slug: string; stamp: string; onSaved: () => Promise<void> }) {
  const t = useTranslations("studio.themePages");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [data, setData] = useState<ThemeTexts | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [beat, setBeat] = useState(1);
  const [words, setWords] = useState<Words | null>(null); // unsaved words of the selected page

  const load = useCallback(async () => {
    const r = await api<ThemeTexts>(`/api/admin/studio/themes/${slug}/texts`);
    if (!r.ok) return setError(errorText(r.error, locale, te("unknown")));
    setError(null);
    setData(r.data);
  }, [slug, locale, te]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load, stamp]);

  if (error) return <Alert>{error}</Alert>;
  if (!data) return <div className="h-40 animate-pulse rounded-xl bg-paper-sunk" aria-busy="true" />;
  if (!data.available || data.pages.length === 0) {
    return (
      <Alert tone="info">
        <span className="font-semibold">{t("comingSoonTitle")}</span> {t("comingSoon")}
      </Alert>
    );
  }

  const page = data.pages.find((p) => p.beat === beat) ?? data.pages[0];
  const shown = words ?? page.current;
  const select = (b: number) => {
    setBeat(b);
    setWords(null);
  };
  return (
    <section aria-labelledby="theme-pages" className="flex flex-col gap-3">
      <h3 id="theme-pages" className="text-h3 text-night-900">
        {t("title")}
      </h3>
      <p className="text-small text-ink-muted">{t("lead")}</p>
      <nav aria-label={t("nav")} className="flex gap-2 overflow-x-auto pb-1">
        {data.pages.map((p) => {
          const edited = p.current.ar !== p.pinned.ar || p.current.en !== p.pinned.en;
          return (
            <button
              key={p.beat}
              type="button"
              onClick={() => select(p.beat)}
              aria-current={p.beat === page.beat ? "page" : undefined}
              className={`flex min-h-11 shrink-0 items-center gap-1 rounded-full border px-3 text-small whitespace-nowrap ${p.beat === page.beat ? "border-night-900 bg-night-900 font-semibold text-paper" : "border-line bg-paper-raised"}`}
            >
              {p.beat === 0 ? t("cover") : t("page", { n: p.beat })}
              {edited && <span className="size-2 rounded-full bg-amber-500" role="img" aria-label={t("edited")} />}
            </button>
          );
        })}
      </nav>
      <div className="grid grid-cols-1 gap-4 2xl:grid-cols-[minmax(0,1fr)_minmax(300px,380px)]">
        <PageTextEditor
          key={page.beat}
          texts={data}
          page={page}
          words={shown}
          setWords={setWords}
          onThemePage
          onSaved={async () => {
            setWords(null);
            await Promise.all([load(), onSaved()]);
          }}
        />
        <div className="flex w-full max-w-md min-w-0 flex-col gap-2">
          <h4 className="font-semibold text-night-900">{t("preview")}</h4>
          <PagePreview src={null} page={page} ar={shown.ar} en={shown.en} texts={data} />
        </div>
      </div>
    </section>
  );
}
