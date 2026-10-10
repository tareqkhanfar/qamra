"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { api, errorText, type ApiErrorBody } from "@/lib/api";
import { usd, type Box, type TemplateDetail, type TemplateStatus, type TemplateTexts, type Words } from "@/lib/studio";
import { HeroBoxCanvas } from "./HeroBoxCanvas";
import { PagePreview } from "./PagePreview";
import { PageTextEditor } from "./PageTextEditor";
import { Pill, StatusBadge, useFlagName, useStudioError, useVariantName } from "./parts";

type Notice = { ok: boolean; text: string } | null;
const MOVES: Record<TemplateStatus, TemplateStatus[]> = {
  draft: ["in_review"],
  in_review: ["approved", "draft"],
  approved: ["live", "in_review"],
  live: ["approved", "in_review"],
};
const DEFAULT_BOX: Box = { x: 0.35, y: 0.3, w: 0.3, h: 0.5 };

/**
 * The template page editor (Addendum 4 §3.2–§3.4): every page's art with its hero box (drag or resize, then
 * save), lock and redraw; the page's words from the theme with a live preview in the book's layout; and the
 * template's review steps. Anything that calls a paid model asks first.
 */
export function TemplateEditor({ id }: { id: string }) {
  const t = useTranslations("studio.editor");
  const te = useTranslations("errors");
  const locale = useLocale();
  const variantName = useVariantName();
  const flagName = useFlagName();
  const studioError = useStudioError();
  const [detail, setDetail] = useState<TemplateDetail | null>(null);
  const [texts, setTexts] = useState<TemplateTexts | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [beat, setBeat] = useState(1);
  const [box, setBox] = useState<Box | null>(null); // unsaved hero box
  const [words, setWords] = useState<Words | null>(null); // unsaved words
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const base = `/api/admin/classic/templates/${id}`;

  const load = useCallback(async () => {
    const [d, x] = await Promise.all([
      api<TemplateDetail>(base),
      api<TemplateTexts>(`/api/admin/studio/templates/${id}/texts`),
    ]);
    if (!d.ok || !x.ok) {
      setFailed(errorText(!d.ok ? d.error : !x.ok ? x.error : null, locale, te("unknown")));
      return;
    }
    setDetail(d.data);
    setTexts(x.data);
  }, [base, id, locale, te]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  const working = detail?.job === "queued" || detail?.job === "running";
  useEffect(() => {
    if (!working) return;
    const timer = setInterval(() => void load(), 5000);
    return () => clearInterval(timer);
  }, [working, load]);

  function explain(error: ApiErrorBody | null): string {
    const d = error?.details as Record<string, unknown> | undefined;
    if (error?.code === "template_incomplete" && d) {
      const yes = (v: unknown) => (v ? "✓" : "✗");
      return t("incomplete", {
        drawn: String(d.drawn),
        total: String(d.total),
        boxes: yes(d.hero_boxes),
        texts: yes(d.texts),
      });
    }
    return studioError(error);
  }

  async function run(key: string, path: string, init: { method?: string; json?: unknown }, ask?: string) {
    if (ask && !window.confirm(ask)) return false;
    setBusy(key);
    setNotice(null);
    const r = await api<unknown>(path, init);
    setBusy(null);
    if (!r.ok) {
      setNotice({ ok: false, text: explain(r.error) });
      return false;
    }
    await load();
    return true;
  }

  if (failed) return <Alert>{failed}</Alert>;
  if (!detail || !texts) return <div className="h-64 animate-pulse rounded-xl bg-paper-sunk" aria-busy="true" />;

  const page = detail.pages.find((p) => p.beat === beat) ?? null;
  const textPage = texts.pages.find((p) => p.beat === beat) ?? texts.pages[0];
  const shownBox = box ?? page?.hero_box ?? null;
  const shownWords = words ?? textPage.current;
  const image = (b: number, regen = 0) => `${base}/pages/${b}/image?v=preview&r=${regen}`;
  const title = `${texts.theme_title[locale === "ar" ? "ar" : "en"]} · ${texts.style_title[locale === "ar" ? "ar" : "en"]} · ${variantName(texts.variant)}`;
  const select = (b: number) => {
    setBeat(b);
    setBox(null);
    setWords(null);
  };
  const patch = (key: string, json: object) => run(key, `${base}/pages/${beat}`, { method: "PATCH", json });

  return (
    <div className="flex flex-col gap-5">
      <Link href="/admin/studio" className="text-small text-night-700 underline">
        {t("back")}
      </Link>
      <header className="flex flex-col gap-2">
        <h1 className="text-h2 text-night-900">{title}</h1>
        <div className="flex flex-wrap items-center gap-2 text-small">
          <StatusBadge status={detail.status} />
          {working && <Pill>{t(`job.${detail.job}`)}</Pill>}
          {detail.job === "failed" && <Pill warn>{t("job.failed")}</Pill>}
          <span>{t("pages", { drawn: detail.pages_drawn, total: detail.pages_total })}</span>
          <span dir="ltr">{usd(detail.cost_usd)}</span>
          <span className={detail.texts.vowelized ? "text-success" : "text-ink-muted"}>
            {detail.texts.vowelized ? `✓ ${t("vowelized")}` : `✗ ${t("notVowelized")}`}
          </span>
          {detail.flags.map((f) => (
            <Pill key={f} warn>
              {flagName(f)}
            </Pill>
          ))}
        </div>
        {detail.error && <p className="text-caption text-danger">{detail.error}</p>}
      </header>
      <div className="flex flex-wrap gap-2">
        {MOVES[detail.status].map((to) => (
          <Button
            key={to}
            size="sm"
            variant={to === "live" || to === "approved" ? "solid" : "secondary"}
            disabled={working}
            loading={busy === `status:${to}`}
            onClick={() => void run(`status:${to}`, `${base}/status`, { json: { to } })}
          >
            {detail.status === "live" && to === "approved" ? t("move.unpublish") : t(`move.${to}`)}
          </Button>
        ))}
        {detail.pages_drawn < detail.pages_total && (
          <Button
            size="sm"
            variant="secondary"
            disabled={working}
            loading={busy === "generate"}
            onClick={() => void run("generate", `${base}/generate`, { json: {} }, t("confirmGenerate"))}
          >
            {t("generate")}
          </Button>
        )}
        {(texts.texts_stale || !detail.texts.vowelized) && (
          <Button
            size="sm"
            variant="secondary"
            disabled={working || texts.story_changed}
            loading={busy === "texts"}
            onClick={() =>
              void run("texts", `${base}/texts`, { json: { refresh: texts.texts_stale } }, t("confirmTexts"))
            }
          >
            {texts.texts_stale ? t("refreshTexts") : t("vowelize")}
          </Button>
        )}
      </div>
      {texts.texts_stale && (
        <Alert tone="info">{t("stale", { pinned: texts.pinned_version, live: texts.live_version })}</Alert>
      )}
      {texts.story_changed && <Alert>{t("storyChanged")}</Alert>}
      {notice && <Alert tone={notice.ok ? "success" : "error"}>{notice.text}</Alert>}
      <div className="grid gap-5 lg:grid-cols-[112px_minmax(0,1fr)] xl:grid-cols-[112px_minmax(0,1fr)_minmax(300px,400px)]">
        <nav
          aria-label={t("pagesNav")}
          className="flex gap-2 overflow-x-auto pb-1 lg:max-h-[80vh] lg:flex-col lg:overflow-y-auto"
        >
          {texts.pages.map((tp) => {
            const row = detail.pages.find((p) => p.beat === tp.beat);
            return (
              <button
                key={tp.beat}
                type="button"
                onClick={() => select(tp.beat)}
                aria-current={tp.beat === beat ? "page" : undefined}
                className={`relative flex w-20 shrink-0 flex-col items-center gap-1 rounded-md border p-1 text-caption lg:w-full ${tp.beat === beat ? "border-night-900 bg-night-100" : "border-line bg-paper-raised"}`}
              >
                {row?.has_image ? (
                  // eslint-disable-next-line @next/next/no-img-element -- streamed from the admin API, private
                  <img
                    src={image(tp.beat, row.regen_count)}
                    alt=""
                    loading="lazy"
                    className="aspect-square w-full rounded object-cover"
                  />
                ) : (
                  <span className="flex aspect-square w-full items-center justify-center rounded bg-paper-sunk">—</span>
                )}
                <span>
                  {tp.beat === 0 ? t("cover") : t("page", { n: tp.beat })} {row?.locked ? "🔒" : ""}
                </span>
                {!!row?.flags.length && (
                  <span
                    className="absolute end-1 top-1 size-2.5 rounded-full bg-warning"
                    title={row.flags.map(flagName).join("، ")}
                  />
                )}
              </button>
            );
          })}
        </nav>
        <section className="flex min-w-0 flex-col gap-4" aria-label={t("pageSection")}>
          <h2 className="text-h3 text-night-900">
            {beat === 0 ? t("cover") : t("page", { n: beat })}
            {page?.layout && (
              <span className="ms-2 text-small font-normal text-ink-muted">{t(`layout.${page.layout}`)}</span>
            )}
          </h2>
          {page && (page.status === "needs_review" || page.status === "failed" || page.flags.length > 0) && (
            <div className="flex flex-wrap gap-1.5">
              {(page.status === "needs_review" || page.status === "failed") && (
                <Pill warn>{t(`pageStatus.${page.status}`)}</Pill>
              )}
              {page.flags.map((f) => (
                <Pill key={f} warn>
                  {flagName(f)}
                </Pill>
              ))}
            </div>
          )}
          <HeroBoxCanvas
            src={page?.has_image ? image(beat, page.regen_count) : null}
            alt={t("pageImage", { n: beat })}
            box={page?.has_hero ? shownBox : null}
            textBox={page?.text_box ?? null}
            editable={!!page && !page.locked}
            onChange={setBox}
            labels={{ hero: t("heroBox"), text: t("textBox"), missing: t("notDrawn"), help: t("boxHelp") }}
          />
          {page && (
            <div className="flex flex-wrap items-center gap-2">
              {page.has_hero && !page.hero_box && !box && (
                <Button size="sm" variant="secondary" disabled={page.locked} onClick={() => setBox(DEFAULT_BOX)}>
                  {t("addBox")}
                </Button>
              )}
              <Button
                size="sm"
                disabled={!box || page.locked}
                loading={busy === "box"}
                onClick={async () => {
                  if (await patch("box", { hero_box: box })) setBox(null);
                }}
              >
                {t("saveBox")}
              </Button>
              <Button size="sm" variant="ghost" disabled={!box} onClick={() => setBox(null)}>
                {t("resetBox")}
              </Button>
              <label className="flex min-h-11 items-center gap-2 text-small">
                <input
                  type="checkbox"
                  checked={page.has_hero}
                  disabled={page.locked || busy !== null}
                  onChange={() => void patch("hero", { has_hero: !page.has_hero })}
                  className="size-5 accent-night-900"
                />
                {t("hasHero")}
              </label>
              <Button
                size="sm"
                variant="secondary"
                loading={busy === "lock"}
                onClick={() => void patch("lock", { locked: !page.locked })}
              >
                {page.locked ? t("unlock") : t("lock")}
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={page.locked || working}
                loading={busy === "redraw"}
                onClick={() => void run("redraw", `${base}/pages/${beat}/regenerate`, { json: {} }, t("confirmRedraw"))}
              >
                {t("redraw")}
              </Button>
              <span className="text-caption text-ink-muted">
                {t("pageCost", { cost: usd(page.cost_usd), redraws: page.regen_count })}
              </span>
            </div>
          )}
          <PageTextEditor
            key={textPage.beat}
            texts={texts}
            page={textPage}
            words={shownWords}
            setWords={setWords}
            onSaved={load}
          />
        </section>
        <aside className="flex min-w-0 flex-col gap-3 lg:col-start-2 xl:col-start-auto" aria-labelledby="preview-title">
          <h2 id="preview-title" className="text-h3 text-night-900">
            {t("preview")}
          </h2>
          <PagePreview
            src={page?.has_image ? image(beat, page.regen_count) : null}
            page={textPage}
            ar={shownWords.ar}
            en={shownWords.en}
            texts={texts}
          />
        </aside>
      </div>
    </div>
  );
}
