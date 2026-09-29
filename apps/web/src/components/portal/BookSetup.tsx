"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Scene } from "@/components/art/Scene";
import { Alert } from "@/components/ui/Alert";
import { Button, buttonClasses } from "@/components/ui/Button";
import { Link, useRouter } from "@/i18n/navigation";
import { errorText, type ApiResult } from "@/lib/api";
import { portalApi, type ClassBook } from "@/lib/portal";
import { usePortal } from "./PortalShell";
import { SchoolPage } from "./SchoolPage";

/** «كتاب الصف» setup (design ClassSetup, PortalClass): one story and line for the class, the school page. */
export function BookSetup({ classId }: { classId: string }) {
  const t = useTranslations("portal.setup");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const { me, reload } = usePortal();
  const [book, setBook] = useState<ClassBook | null>(null);
  const [draft, setDraft] = useState({ theme: "", line: "magic", style: "", min: 2, message: "" });
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const take = useCallback((b: ClassBook) => {
    setBook(b);
    setDraft({
      theme: b.theme ?? b.themes[0]?.slug ?? "",
      line: b.line,
      style: b.style,
      min: b.min_appearances,
      message: b.teacher_message ?? "",
    });
  }, []);

  useEffect(() => {
    void (async () => {
      const r = await portalApi.book(classId);
      if (r.ok) take(r.data);
      else setError(errorText(r.error, locale, te("unknown")));
    })();
  }, [classId, locale, take, te]);

  async function run(label: string, call: () => Promise<ApiResult<ClassBook>>, then?: () => void) {
    setBusy(label);
    setError(null);
    setSaved(false);
    const r = await call();
    setBusy(null);
    if (r.ok) {
      take(r.data);
      then?.();
    } else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  const save = (then?: () => void) =>
    run(
      "save",
      () =>
        portalApi.setupBook(classId, {
          theme: draft.theme,
          line: draft.line,
          min_appearances: draft.min,
          teacher_message: draft.message,
          ...(book && draft.style !== book.style ? { style: draft.style } : {}),
        }),
      () => {
        setSaved(true);
        then?.();
      },
    );

  if (!book) return error ? <Alert>{error}</Alert> : <div className="h-64 animate-pulse rounded-xl bg-paper-sunk" />;
  const locked = book.status === "generating" || book.status === "ordered" || book.status === "printing";
  const styles = book.styles.filter((s) => s.lines.includes(draft.line));
  const name = (x: { name_ar: string; name_en: string }) => (locale === "ar" ? x.name_ar : x.name_en);

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_340px]">
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          <span className="text-small text-ink-muted">{t("crumb")}</span>
          <h1 className="text-h2 text-night-900">{t("title")}</h1>
        </div>
        {locked && <Alert tone="info">{t(`locked.${book.status}`)}</Alert>}
        <fieldset disabled={locked} className="flex flex-col gap-6">
          <section className="flex flex-col gap-3">
            <h2 className="text-h3 text-night-900">{t("story")}</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {book.themes.map((th) => (
                <label
                  key={th.slug}
                  className={`flex cursor-pointer flex-col gap-2 rounded-lg bg-paper-raised p-2 pb-3 ${draft.theme === th.slug ? "border-[3px] border-amber-500" : "border-[1.5px] border-line"}`}
                >
                  <input
                    type="radio"
                    name="theme"
                    className="sr-only"
                    checked={draft.theme === th.slug}
                    onChange={() => setDraft((d) => ({ ...d, theme: th.slug }))}
                  />
                  <Scene theme="grad" cap ratio={16 / 9} kidScale={0.8} className="rounded-md" />
                  <strong className="px-1 text-body">{name(th)}</strong>
                  <span className="px-1 text-caption text-ink-muted">{t("storyPages", { n: th.pages })}</span>
                </label>
              ))}
            </div>
          </section>
          <section className="grid gap-4 md:grid-cols-2">
            <div className="flex flex-col gap-2">
              <h2 className="text-h3 text-night-900">{t("line")}</h2>
              {(["magic", "classic"] as const).map((l) => (
                <label
                  key={l}
                  className={`flex cursor-pointer gap-3 rounded-md p-3 ${draft.line === l ? "border-2 border-night-900 bg-night-100" : "border-[1.5px] border-line bg-paper-raised"}`}
                >
                  <input
                    type="radio"
                    name="line"
                    checked={draft.line === l}
                    onChange={() => setDraft((d) => ({ ...d, line: l }))}
                    className="mt-1 size-5 accent-night-900"
                  />
                  <span className="flex flex-col">
                    <strong>{t(`lines.${l}`)}</strong>
                    <span className="text-small text-ink-muted">{t(`lines.${l}Body`)}</span>
                  </span>
                </label>
              ))}
            </div>
            <div className="flex flex-col gap-3">
              {draft.line === "magic" && (
                <div className="flex flex-col gap-2">
                  <h2 className="text-h3 text-night-900">{t("appearances")}</h2>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      aria-label={t("less")}
                      onClick={() => setDraft((d) => ({ ...d, min: Math.max(1, d.min - 1) }))}
                      className="size-11 rounded-full border-2 border-night-900 text-h3"
                    >
                      −
                    </button>
                    <output className="min-w-8 text-center font-display text-h2">{draft.min}</output>
                    <button
                      type="button"
                      aria-label={t("more")}
                      onClick={() => setDraft((d) => ({ ...d, min: Math.min(6, d.min + 1) }))}
                      className="size-11 rounded-full border-2 border-night-900 text-h3"
                    >
                      +
                    </button>
                    <span className="text-small text-ink-muted">{t("timesEach")}</span>
                  </div>
                  <p className="text-caption text-ink-muted">
                    {t("appearancesHint", { n: book.ready, total: book.ready * draft.min })}
                  </p>
                </div>
              )}
              <div className="flex flex-col gap-1.5">
                <label htmlFor="style" className="text-small font-semibold">
                  {t("style")}
                </label>
                <select
                  id="style"
                  value={draft.style}
                  onChange={(e) => setDraft((d) => ({ ...d, style: e.target.value }))}
                  disabled={book.ready > 0}
                  className="min-h-[52px] rounded-sm border border-line bg-paper-raised px-4"
                >
                  {styles.map((s) => (
                    <option key={s.slug} value={s.slug}>
                      {name(s)}
                    </option>
                  ))}
                </select>
                {book.ready > 0 && <span className="text-caption text-ink-muted">{t("styleLocked")}</span>}
              </div>
            </div>
          </section>
        </fieldset>
        <SchoolPage
          classId={classId}
          book={book}
          message={draft.message}
          setMessage={(message) => setDraft((d) => ({ ...d, message }))}
          locked={locked}
          hasLogo={me.org.has_logo}
          onBook={take}
          onLogo={reload}
        />
      </div>
      <aside className="flex flex-col gap-3 self-start rounded-xl border border-line bg-paper-raised p-5 xl:sticky xl:top-6">
        <h2 className="text-h3 text-night-900">{t("summary")}</h2>
        <dl className="flex flex-col gap-2 text-small">
          {[
            ["summaryReady", t("readyOf", { n: book.ready, total: book.children })],
            ["summaryPages", t("pagesPlus", { n: book.pages, portraits: book.ready })],
            ["summaryCovers", t("covers", { n: book.ready })],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between gap-2 border-b border-line pb-2">
              <dt className="text-ink-muted">{t(k)}</dt>
              <dd className="font-semibold">{v}</dd>
            </div>
          ))}
        </dl>
        {book.short.length > 0 && <Alert tone="info">{t("short", { names: book.short.join("، ") })}</Alert>}
        {book.plan_outdated && <Alert tone="info">{t("outdated")}</Alert>}
        {error && <Alert>{error}</Alert>}
        {saved && <Alert tone="success">{t("saved")}</Alert>}
        <Button onClick={() => void save()} loading={busy === "save"} disabled={locked} variant="secondary">
          {t("save")}
        </Button>
        <Link href={`/portal/classes/${classId}/planner`} className={buttonClasses("ghost", "sm")}>
          {t("planner")}
        </Link>
        <Button
          onClick={() =>
            void save(
              () =>
                void run(
                  "generate",
                  () => portalApi.generate(classId),
                  () => router.push(`/portal/classes/${classId}/review`),
                ),
            )
          }
          loading={busy === "generate"}
          disabled={locked || book.ready === 0}
          variant="primary"
        >
          {t("generate", { n: book.ready })}
        </Button>
        <p className="text-caption text-ink-muted">{t("generateHint")}</p>
      </aside>
    </div>
  );
}
