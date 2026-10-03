"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText, type ApiResult } from "@/lib/api";
import {
  islamicReviewApi,
  type ReviewMe,
  type ReviewOverview,
  type ReviewPoint,
  type ReviewStatus,
  type ReviewUnit,
  type ReviewVolume,
} from "@/lib/islamicReview";

const STATUS_TONE: Record<ReviewStatus, string> = {
  draft: "bg-paper-sunk text-ink-muted",
  scholar_review: "bg-info-bg text-info",
  changes_requested: "bg-amber-100 text-amber-700",
  approved: "bg-success-bg text-success",
};

type Notice = { tone: "error" | "success" | "info"; text: string } | null;

/**
 * «قلبي يعرف الله» (Addendum 10 §3.3): the scholar reviews every unit page by page. Staff send units to the
 * scholar and render the review pages; only the scholar approves, sends back with notes and answers the
 * `scholar_decision` points. A volume is sold and printed only once every unit of it is approved.
 */
export function AdminIslamicReview() {
  const t = useTranslations("islamicReview");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [overview, setOverview] = useState<ReviewOverview | null>(null);
  const [volumeId, setVolumeId] = useState<string | null>(null);
  const [volume, setVolume] = useState<ReviewVolume | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const num = (n: number) => n.toLocaleString(locale === "ar" ? "ar-EG" : "en-US");
  const day = (iso: string | null) =>
    iso ? new Date(iso).toLocaleDateString(locale === "ar" ? "ar-EG" : "en-GB", { dateStyle: "medium" }) : "";
  const fail = useCallback(
    (r: ApiResult<unknown>) => {
      if (!r.ok) setNotice({ tone: "error", text: errorText(r.error, locale, te("unknown")) });
    },
    [locale, te],
  );

  const loadOverview = useCallback(async () => {
    const r = await islamicReviewApi.overview();
    if (!r.ok) {
      setError(errorText(r.error, locale, te("unknown")));
      return;
    }
    setOverview(r.data);
    setVolumeId((v) => v ?? r.data.volumes[0]?.id ?? null);
  }, [locale, te]);
  const loadVolume = useCallback(
    async (id: string) => {
      const r = await islamicReviewApi.volume(id);
      if (r.ok) setVolume(r.data);
      else fail(r);
    },
    [fail],
  );

  useEffect(() => {
    void (async () => {
      await loadOverview();
    })();
  }, [loadOverview]);
  useEffect(() => {
    void (async () => {
      if (volumeId) await loadVolume(volumeId);
    })();
  }, [loadVolume, volumeId]);

  /** Run an action, then show its result and reload what it changed. */
  async function run(key: string, action: () => Promise<ApiResult<unknown>>, done: string) {
    setBusy(key);
    setNotice(null);
    const r = await action();
    setBusy(null);
    if (!r.ok) {
      fail(r);
      return false;
    }
    setNotice({ tone: "success", text: done });
    await Promise.all([loadOverview(), volumeId ? loadVolume(volumeId) : Promise.resolve()]);
    return true;
  }

  if (error) return <Alert>{error}</Alert>;
  if (!overview) return <p className="text-ink-muted">{t("loading")}</p>;
  const me = overview.me;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-h2 text-night-900 md:text-h1">{t("title")}</h1>
        <p className="max-w-3xl text-body text-ink-muted">{t("intro")}</p>
        <a
          href={islamicReviewApi.exportUrl}
          className="self-start text-small font-semibold text-night-800 underline underline-offset-4"
          download="review-status.json"
        >
          {t("export")}
        </a>
      </header>

      {notice && <Alert tone={notice.tone}>{notice.text}</Alert>}
      {me.scholar && (
        <ScholarProfile
          me={me}
          busy={busy === "me"}
          onSave={(n, ok) => run("me", () => islamicReviewApi.saveMe(n, ok), t("profile.saved"))}
        />
      )}

      <div role="tablist" aria-label={t("volumes")} className="flex flex-wrap gap-2">
        {overview.volumes.map((v) => (
          <button
            key={v.id}
            type="button"
            role="tab"
            aria-selected={v.id === volumeId}
            onClick={() => setVolumeId(v.id)}
            className={`flex min-h-12 flex-col items-start justify-center rounded-xl border px-4 py-1.5 text-start ${v.id === volumeId ? "border-night-900 bg-night-900 text-paper" : "border-line bg-paper-raised text-night-900"}`}
          >
            <span className="font-semibold">{v.name_ar}</span>
            <span className={`text-caption ${v.id === volumeId ? "text-night-100" : "text-ink-muted"}`}>
              {v.all_approved ? t("allApproved") : t("progress", { approved: num(v.approved), units: num(v.units) })}
            </span>
          </button>
        ))}
      </div>

      {volume && volume.id === volumeId && (
        <VolumePanel
          volume={volume}
          me={me}
          busy={busy}
          num={num}
          day={day}
          onRender={() => run("previews", () => islamicReviewApi.renderPreviews(volume.id), t("done.previewsQueued"))}
          onAct={run}
        />
      )}

      {overview.general_points.length > 0 && (
        <section aria-labelledby="general-title" className="flex flex-col gap-3">
          <h2 id="general-title" className="text-h3 text-night-900">
            {t("general.title")}
          </h2>
          <p className="max-w-3xl text-small text-ink-muted">{t("general.intro")}</p>
          <ul className="flex flex-col gap-3">
            {overview.general_points.map((p) => (
              <li key={p.source_id}>
                <PointCard point={p} scholar={me.scholar} busy={busy} day={day} onAct={run} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

type Run = (key: string, action: () => Promise<ApiResult<unknown>>, done: string) => Promise<boolean>;

function ScholarProfile({
  me,
  busy,
  onSave,
}: {
  me: ReviewMe;
  busy: boolean;
  onSave: (name: string, mayBeNamed: boolean) => Promise<boolean>;
}) {
  const t = useTranslations("islamicReview.profile");
  const [name, setName] = useState(me.name_ar ?? "");
  const [named, setNamed] = useState(me.may_be_named);
  return (
    <section
      className="flex flex-col gap-3 rounded-xl border border-line bg-paper-raised p-4"
      aria-labelledby="profile-title"
    >
      <h2 id="profile-title" className="text-body font-bold text-night-900">
        {t("title")}
      </h2>
      <label className="flex flex-col gap-1 text-small font-semibold text-night-900">
        {t("name")}
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={120}
          className="min-h-11 max-w-md rounded-sm border border-line bg-paper px-3 font-normal"
        />
      </label>
      <label className="flex items-start gap-2 text-small text-night-900">
        <input
          type="checkbox"
          checked={named}
          onChange={(e) => setNamed(e.target.checked)}
          className="mt-1 size-4 accent-night-900"
        />
        <span>{t("consent", { name: name.trim() || t("yourName") })}</span>
      </label>
      <Button
        size="sm"
        className="self-start"
        disabled={busy || name.trim().length < 2}
        onClick={() => void onSave(name, named)}
      >
        {t("save")}
      </Button>
    </section>
  );
}

function VolumePanel({
  volume,
  me,
  busy,
  num,
  day,
  onRender,
  onAct,
}: {
  volume: ReviewVolume;
  me: ReviewMe;
  busy: string | null;
  num: (n: number) => string;
  day: (iso: string | null) => string;
  onRender: () => Promise<boolean>;
  onAct: Run;
}) {
  const t = useTranslations("islamicReview");
  const p = volume.previews;
  return (
    <section className="flex flex-col gap-4" aria-labelledby="volume-title">
      <div className="flex flex-col gap-1">
        <h2 id="volume-title" className="text-h3 text-night-900">
          {volume.name_ar}: {volume.title_ar}
        </h2>
        <Alert tone={volume.all_approved ? "success" : "info"}>
          {volume.all_approved ? t("onSale") : t("notOnSale")}
        </Alert>
      </div>
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-paper-raised p-4 text-small">
        <span className="font-semibold text-night-900">{t("previews.title")}</span>
        <span className="text-ink-muted">
          {p.status === "ready"
            ? t("previews.ready", { pages: num(p.pages), date: day(p.rendered_at) })
            : t(`previews.${p.status}`)}
        </span>
        {me.can_edit && (
          <Button
            size="sm"
            variant="secondary"
            disabled={busy !== null || p.status === "queued"}
            onClick={() => void onRender()}
          >
            {p.status === "none" ? t("previews.render") : t("previews.again")}
          </Button>
        )}
        {volume.pages_mismatch && <span className="font-semibold text-warning">{t("previews.mismatch")}</span>}
        {p.error && (
          <span className="text-danger" dir="ltr">
            {p.error}
          </span>
        )}
      </div>
      <ul className="flex flex-col gap-3">
        {volume.units.map((u) => (
          <li key={u.id}>
            <UnitCard unit={u} me={me} busy={busy} num={num} day={day} onAct={onAct} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function UnitCard({
  unit,
  me,
  busy,
  num,
  day,
  onAct,
}: {
  unit: ReviewUnit;
  me: ReviewMe;
  busy: string | null;
  num: (n: number) => string;
  day: (iso: string | null) => string;
  onAct: Run;
}) {
  const t = useTranslations("islamicReview");
  const [text, setText] = useState("");
  const [page, setPage] = useState("");
  const [zoom, setZoom] = useState<string | null>(null);
  const key = (a: string) => `${a}:${unit.id}`;
  const body = () => ({ text, page: page ? Number(page) : null });
  const after = (ok: boolean) => {
    if (ok) {
      setText("");
      setPage("");
    }
  };
  const canSubmit = me.can_edit && unit.status !== "scholar_review";
  const reopen = unit.status === "approved";
  const points = unit.sources.filter((s) => s.question);
  return (
    <details className="group rounded-xl border border-line bg-paper-raised" open={unit.status === "scholar_review"}>
      <summary className="flex min-h-14 cursor-pointer list-none flex-wrap items-center gap-3 px-4 py-3">
        <span className={`rounded-full px-2.5 py-0.5 text-caption font-bold ${STATUS_TONE[unit.status]}`}>
          {t(`status.${unit.status}`)}
        </span>
        <span className="font-semibold text-night-900">{unit.matter ? t("matter") : unit.title_ar}</span>
        <span className="text-caption text-ink-muted">
          {t("pagesCount", { n: unit.pages.length })}
          {unit.pending_points > 0 && ` · ${t("pendingPoints", { n: unit.pending_points })}`}
          {unit.approved_at && ` · ${t("approvedBy", { name: unit.reviewer_name ?? "", date: day(unit.approved_at) })}`}
        </span>
      </summary>
      <div className="flex flex-col gap-4 border-t border-line p-4">
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-6">
          {unit.pages.map((pg) => (
            <figure key={pg.n} className="flex flex-col gap-1">
              {pg.preview ? (
                <button
                  type="button"
                  onClick={() => setZoom(pg.preview)}
                  aria-label={t("pageN", { n: num(pg.n) })}
                  className="overflow-hidden rounded-md border border-line bg-white"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element -- private image streamed by the admin API */}
                  <img src={pg.preview} alt="" loading="lazy" className="aspect-[3/4] w-full object-cover" />
                </button>
              ) : (
                <div className="flex aspect-[3/4] items-center justify-center rounded-md border border-dashed border-line bg-paper-sunk p-1 text-center text-caption text-ink-muted">
                  {t("noPreview")}
                </div>
              )}
              <figcaption className="text-caption leading-snug">
                <span className="font-semibold text-night-900">{t("pageN", { n: num(pg.n) })}</span>
                <span className="block text-ink-muted">
                  {t.has(`kinds.${pg.kind}`) ? t(`kinds.${pg.kind}`) : pg.kind}
                </span>
                {pg.title && <span className="line-clamp-2 block text-ink-muted">{pg.title}</span>}
              </figcaption>
            </figure>
          ))}
        </div>

        {unit.sources.length > 0 && (
          <div className="flex flex-col gap-2">
            <h3 className="text-small font-bold text-night-900">{t("sources.title")}</h3>
            <ul className="flex flex-wrap gap-1.5">
              {unit.sources.map((s) => (
                <li
                  key={s.id}
                  className={`rounded-full border px-2.5 py-1 text-caption ${s.status === "scholar_approved" ? "border-success/40 text-success" : "border-line text-night-900"}`}
                >
                  {t.has(`kindsOfSource.${s.kind}`) ? t(`kindsOfSource.${s.kind}`) : s.kind}: {s.title_ar}
                  <span className="text-ink-muted">
                    {" "}
                    · {t.has(`sourceStatus.${s.status}`) ? t(`sourceStatus.${s.status}`) : s.status}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {points.length > 0 && (
          <div className="flex flex-col gap-2">
            <h3 className="text-small font-bold text-night-900">{t("points")}</h3>
            {points.map((s) => (
              <PointCard
                key={s.id}
                point={{
                  source_id: s.id,
                  title_ar: s.title_ar,
                  question: s.question ?? "",
                  decision: s.decision,
                  decided_by: s.decided_by,
                  decided_at: s.decided_at,
                }}
                scholar={me.scholar}
                busy={busy}
                day={day}
                onAct={onAct}
              />
            ))}
          </div>
        )}

        {unit.events.length > 0 && (
          <div className="flex flex-col gap-2">
            <h3 className="text-small font-bold text-night-900">{t("history")}</h3>
            <ol className="flex flex-col gap-1.5 text-small">
              {unit.events.map((e, i) => (
                <li key={i} className={`rounded-sm px-3 py-2 ${e.scholar ? "bg-night-100" : "bg-paper-sunk"}`}>
                  <span className="font-semibold text-night-900">{t(`events.${e.kind}`)}</span>
                  <span className="text-ink-muted">
                    {" "}
                    · {e.author_name} · {day(e.created_at)}
                    {e.page !== null && ` · ${t("pageN", { n: num(e.page) })}`}
                  </span>
                  {e.text && <p className="mt-1 whitespace-pre-line text-ink">{e.text}</p>}
                </li>
              ))}
            </ol>
          </div>
        )}

        {(me.can_edit || me.scholar) && (
          <div className="flex flex-col gap-2">
            <label className="flex flex-col gap-1 text-small font-semibold text-night-900">
              {reopen && me.can_edit ? t("form.whatChanged") : t("form.note")}
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={3}
                maxLength={4000}
                className="rounded-sm border border-line bg-paper p-3 font-normal"
              />
            </label>
            <label className="flex items-center gap-2 text-small text-night-900">
              {t("form.page")}
              <input
                value={page}
                onChange={(e) => setPage(e.target.value.replace(/\D/g, "").slice(0, 3))}
                inputMode="numeric"
                dir="ltr"
                className="min-h-11 w-20 rounded-sm border border-line bg-paper px-3"
              />
            </label>
            <div className="flex flex-wrap gap-2">
              {canSubmit && (
                <Button
                  size="sm"
                  disabled={busy !== null || (reopen && !text.trim())}
                  onClick={async () =>
                    after(
                      await onAct(
                        key("submit"),
                        () => islamicReviewApi.submit(unit.id, body()),
                        reopen ? t("done.reopened") : t("done.submitted"),
                      ),
                    )
                  }
                >
                  {reopen ? t("actions.reopen") : t("actions.submit")}
                </Button>
              )}
              {me.scholar && unit.status === "scholar_review" && (
                <Button
                  size="sm"
                  variant="primary"
                  disabled={busy !== null || unit.pending_points > 0}
                  onClick={async () =>
                    after(
                      await onAct(key("approve"), () => islamicReviewApi.approve(unit.id, body()), t("done.approved")),
                    )
                  }
                >
                  {t("actions.approve")}
                </Button>
              )}
              {me.scholar && (unit.status === "scholar_review" || unit.status === "approved") && (
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy !== null || !text.trim()}
                  onClick={async () =>
                    after(
                      await onAct(
                        key("changes"),
                        () => islamicReviewApi.requestChanges(unit.id, body()),
                        t("done.changesRequested"),
                      ),
                    )
                  }
                >
                  {t("actions.requestChanges")}
                </Button>
              )}
              <Button
                size="sm"
                variant="ghost"
                disabled={busy !== null || !text.trim()}
                onClick={async () =>
                  after(await onAct(key("note"), () => islamicReviewApi.note(unit.id, body()), t("done.noted")))
                }
              >
                {t("actions.note")}
              </Button>
            </div>
            {me.scholar && unit.status === "scholar_review" && unit.pending_points > 0 && (
              <p className="text-caption text-ink-muted">{t("form.pointsFirst")}</p>
            )}
          </div>
        )}
      </div>
      {zoom && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={t("zoom")}
          className="fixed inset-0 z-50 flex items-center justify-center bg-night-950/80 p-4"
          onClick={() => setZoom(null)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- private image streamed by the admin API */}
          <img src={zoom} alt="" className="max-h-full max-w-full rounded-md bg-white" />
          <button
            type="button"
            onClick={() => setZoom(null)}
            className="absolute top-4 min-h-11 rounded-full bg-paper-raised px-4 font-semibold ltr:right-4 rtl:left-4"
          >
            {t("close")}
          </button>
        </div>
      )}
    </details>
  );
}

function PointCard({
  point,
  scholar,
  busy,
  day,
  onAct,
}: {
  point: ReviewPoint;
  scholar: boolean;
  busy: string | null;
  day: (iso: string | null) => string;
  onAct: Run;
}) {
  const t = useTranslations("islamicReview");
  const [draft, setDraft] = useState(point.decision ?? "");
  return (
    <div
      className={`flex flex-col gap-2 rounded-md border p-3 text-small ${point.decision ? "border-line" : "border-amber-500"}`}
    >
      <p className="font-semibold text-night-900">{point.title_ar}</p>
      <p className="text-ink">
        <span className="font-semibold">{t("question")}: </span>
        {point.question}
      </p>
      {point.decision ? (
        <p className="text-success">
          <span className="font-semibold">{t("decision")}: </span>
          {point.decision}
          <span className="text-ink-muted">
            {" "}
            · {point.decided_by} · {day(point.decided_at)}
          </span>
        </p>
      ) : (
        <p className="font-semibold text-amber-700">{t("noDecision")}</p>
      )}
      {scholar && (
        <>
          <label className="sr-only" htmlFor={`decision-${point.source_id}`}>
            {t("decision")}
          </label>
          <textarea
            id={`decision-${point.source_id}`}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={2}
            maxLength={4000}
            className="rounded-sm border border-line bg-paper p-2"
          />
          <Button
            size="sm"
            variant="secondary"
            className="self-start"
            disabled={busy !== null || !draft.trim() || draft.trim() === point.decision}
            onClick={() =>
              void onAct(
                `decide:${point.source_id}`,
                () => islamicReviewApi.decide(point.source_id, draft),
                t("done.decided"),
              )
            }
          >
            {t("actions.decide")}
          </Button>
        </>
      )}
    </div>
  );
}
