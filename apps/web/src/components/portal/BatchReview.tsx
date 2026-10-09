"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button, buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import { portalApi, portalFiles, type Review } from "@/lib/portal";
import { usePortal } from "./PortalShell";
import { BatchProgress, Chip } from "./parts";

const POLL_MS = 4000;

/** The class batch (design PortalBatch, ClassReview, ClassCovers): progress while drawing, then every shared
 * page and every child's copy to check, redraw requests, and the school's bulk approval. */
export function BatchReview({ classId }: { classId: string }) {
  const t = useTranslations("portal.review");
  const tp = useTranslations("portal");
  const te = useTranslations("errors");
  const locale = useLocale();
  const { reload } = usePortal();
  const [review, setReview] = useState<Review | null>(null);
  const [pages, setPages] = useState<number[]>([]);
  const [covers, setCovers] = useState<string[]>([]);
  const [chosen, setChosen] = useState<string[]>([]);
  const [busy, setBusy] = useState<"approve" | "redraw" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const r = await portalApi.review(classId);
    if (r.ok) setReview(r.data);
    else setError(errorText(r.error, locale, te("unknown")));
  }, [classId, locale, te]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  const drawing = review?.status === "generating";
  useEffect(() => {
    if (!drawing) return;
    const timer = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(timer);
  }, [drawing, load]);

  if (!review) return error ? <Alert>{error}</Alert> : <div className="h-64 animate-pulse rounded-xl bg-paper-sunk" />;
  const ready = review.copies.filter((c) => c.status === "ready");
  const toggle = <T,>(list: T[], x: T) => (list.includes(x) ? list.filter((y) => y !== x) : [...list, x]);

  async function approve(children: string[] | null) {
    setBusy("approve");
    setError(null);
    const r = await portalApi.approve(classId, children);
    setBusy(null);
    if (r.ok) {
      setReview(r.data);
      setChosen([]);
      await reload();
    } else setError(errorText(r.error, locale, te("unknown")));
  }

  async function redraw() {
    setBusy("redraw");
    setError(null);
    const r = await portalApi.redraw(classId, pages, covers);
    setBusy(null);
    if (r.ok) {
      setPages([]);
      setCovers([]);
      await load();
    } else setError(errorText(r.error, locale, te("unknown")));
  }

  const flagged = review.pages.filter((p) => p.unrecognized.length || p.status !== "ok");
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <span className="text-small text-ink-muted">{t("crumb")}</span>
          <h1 className="text-h2 text-night-900">{t("title")}</h1>
        </div>
        {(review.status === "approved" || review.status === "ordered") && (
          <Link href={`/portal/classes/${classId}/order`} className={buttonClasses("primary")}>
            {t("toOrder")}
          </Link>
        )}
      </div>
      {(drawing || review.progress.stage) && review.status !== "review" && review.status !== "approved" && (
        <BatchProgress progress={review.progress} />
      )}
      {review.status === "failed" && <Alert>{t("failed")}</Alert>}
      {error && <Alert>{error}</Alert>}

      <section className="flex flex-col gap-3" aria-labelledby="copies">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="copies" className="text-h3 text-night-900">
            {t("copies", { n: review.copies.length })}
          </h2>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={!chosen.length}
              loading={busy === "approve"}
              onClick={() => void approve(chosen)}
            >
              {t("approveChosen", { n: chosen.length })}
            </Button>
            <Button size="sm" disabled={!ready.length} loading={busy === "approve"} onClick={() => void approve(null)}>
              {t("approveAll", { n: ready.length })}
            </Button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-6">
          {review.copies.map((c) => (
            <article
              key={c.child_id}
              className={`flex flex-col gap-2 rounded-lg bg-paper-raised p-2 ${chosen.includes(c.child_id) ? "border-2 border-night-900" : "border border-line"}`}
            >
              <div className="relative">
                {c.cover ? (
                  // eslint-disable-next-line @next/next/no-img-element -- private illustration through the API
                  <img
                    src={portalFiles.cover(classId, c.child_id)}
                    alt={t("coverOf", nameCases(c.name))}
                    className="aspect-square w-full rounded-md object-cover"
                  />
                ) : (
                  <div className="flex aspect-square w-full items-center justify-center rounded-md bg-paper-sunk text-small text-ink-muted">
                    {t(c.status === "drawing" ? "drawing" : "queued")}
                  </div>
                )}
                {c.status === "ready" && (
                  <input
                    type="checkbox"
                    aria-label={t("choose", nameCases(c.name))}
                    checked={chosen.includes(c.child_id)}
                    onChange={() => setChosen((l) => toggle(l, c.child_id))}
                    className="absolute end-2 top-2 size-6 accent-night-900"
                  />
                )}
              </div>
              <strong className="text-small">{c.name}</strong>
              <div className="flex flex-wrap items-center gap-1.5">
                <Chip tone={c.status}>{t(`status.${c.status}`)}</Chip>
                {c.flags.includes("class_face") && <Chip tone="failed">{t("faceFlag")}</Chip>}
              </div>
              <span className="text-caption text-ink-muted">
                {t("appears", { n: c.appearances, ok: c.recognized })}
              </span>
              <div className="flex flex-wrap gap-2 text-caption">
                {(c.status === "ready" || c.status === "approved") && (
                  <a
                    href={portalFiles.copyPdf(classId, c.child_id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold underline"
                  >
                    {t("read")}
                  </a>
                )}
                {c.cover && c.status === "ready" && (
                  <label className="flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={covers.includes(c.child_id)}
                      onChange={() => setCovers((l) => toggle(l, c.child_id))}
                      className="size-4 accent-night-900"
                    />
                    {t("redrawCover")}
                  </label>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-3" aria-labelledby="pages">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="pages" className="text-h3 text-night-900">
            {t("pages", { ok: review.pages.length - flagged.length, flagged: flagged.length })}
          </h2>
          <div className="flex items-center gap-3">
            <span className="text-caption text-ink-muted">{t("redrawsLeft", { n: review.redraws_left })}</span>
            <Button
              variant="secondary"
              size="sm"
              disabled={!pages.length && !covers.length}
              loading={busy === "redraw"}
              onClick={() => void redraw()}
            >
              {t("redraw", { n: pages.length + covers.length })}
            </Button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-6">
          {review.pages.map((p) => {
            const bad = p.unrecognized.length > 0 || p.status !== "ok";
            return (
              <figure
                key={p.index}
                className={`m-0 flex flex-col gap-1.5 rounded-lg bg-paper-raised p-2 ${bad ? "border-2 border-danger" : "border border-line"}`}
              >
                <div className="relative">
                  {p.image ? (
                    // eslint-disable-next-line @next/next/no-img-element -- private illustration through the API
                    <img
                      src={portalFiles.page(classId, p.index)}
                      alt={t("pageAlt", { n: p.index })}
                      className="aspect-square w-full rounded-md object-cover"
                    />
                  ) : (
                    <div className="aspect-square w-full rounded-md bg-paper-sunk" />
                  )}
                  {p.unrecognized.length > 0 && (
                    <span className="absolute inset-x-1.5 bottom-1.5 rounded-sm bg-danger px-2 py-1 text-center text-[11px] font-bold text-white">
                      {t("notRecognized", { names: p.unrecognized.join("، ") })}
                    </span>
                  )}
                </div>
                <figcaption className="flex flex-col gap-1">
                  <strong className="text-caption">
                    {t("page", { n: p.index })} · {p.children.join("، ") || tp("everyone")}
                  </strong>
                  <label className="flex items-center gap-1 text-caption">
                    <input
                      type="checkbox"
                      checked={pages.includes(p.index)}
                      onChange={() => setPages((l) => toggle(l, p.index))}
                      className="size-4 accent-night-900"
                      disabled={drawing}
                    />
                    {t("redrawPage")}
                  </label>
                </figcaption>
              </figure>
            );
          })}
        </div>
      </section>
    </div>
  );
}
