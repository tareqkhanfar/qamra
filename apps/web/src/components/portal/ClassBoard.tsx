"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { errorText, type ApiResult } from "@/lib/api";
import { portalApi, portalFiles, type ChildRow, type ClassDetail, type Stage } from "@/lib/portal";
import { usePortal } from "./PortalShell";
import { Chip, Steps } from "./parts";

type Filter = "all" | "waiting" | "consent" | "photo" | "approved";
const FILTERS: Filter[] = ["all", "waiting", "consent", "photo", "approved"];
const matches = (f: Filter, s: Stage) =>
  f === "all" || (f === "waiting" ? s === "not_invited" || s === "invited" : s === f);

/** Parents' invites and progress for one class (design PortalInvite, ClassReady): states only, never a photo. */
export function ClassBoard({ classId }: { classId: string }) {
  const t = useTranslations("portal.board");
  const tp = useTranslations("portal");
  const te = useTranslations("errors");
  const locale = useLocale();
  const { me, reload } = usePortal();
  const [detail, setDetail] = useState<ClassDetail | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const load = useCallback(async () => {
    const r = await portalApi.classDetail(classId);
    if (r.ok) setDetail(r.data);
    else setError(errorText(r.error, locale, te("unknown")));
  }, [classId, locale, te]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  if (!detail) return error ? <Alert>{error}</Alert> : <div className="h-64 animate-pulse rounded-xl bg-paper-sunk" />;

  const link = (c: ChildRow) => (c.invite.path ? `${window.location.origin}/ar${c.invite.path}` : "");
  const message = (c: ChildRow) => t("message", { school: me.org.name, name: c.name, link: link(c) });

  async function sent(c: ChildRow) {
    const r = await portalApi.markSent(classId, [c.id]);
    if (r.ok) setDetail(r.data);
  }
  async function copy(c: ChildRow) {
    try {
      await navigator.clipboard.writeText(message(c));
    } catch {
      window.prompt(t("copy"), message(c)); // no clipboard (e.g. plain http): let the school copy it by hand
    }
    setCopied(c.id);
    await sent(c);
  }
  async function act(run: () => Promise<ApiResult<ClassDetail>>) {
    setError(null);
    const r = await run();
    if (r.ok) {
      setDetail(r.data);
      await reload();
    } else setError(errorText(r.error, locale, te("unknown")));
  }

  const rows = detail.children.filter((c) => matches(filter, c.stage));
  const count = (f: Filter) => detail.children.filter((c) => matches(f, c.stage)).length;
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <span className="text-small text-ink-muted">
            {t("crumb", { name: detail.name, n: detail.children.length })}
          </span>
          <h1 className="text-h2 text-night-900">{t("title")}</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/portal/classes/${classId}/import`} className={buttonClasses("secondary", "sm")}>
            {t("import")}
          </Link>
          <Link href={`/portal/classes/${classId}/book`} className={buttonClasses("solid", "sm")}>
            {t("book")}
          </Link>
        </div>
      </div>
      <p className="rounded-md bg-info-bg px-4 py-3 text-small text-info">{t("privacy")}</p>
      {error && <Alert>{error}</Alert>}
      <div role="tablist" className="flex gap-2 overflow-x-auto">
        {FILTERS.map((f) => (
          <button
            key={f}
            role="tab"
            aria-selected={filter === f}
            onClick={() => setFilter(f)}
            className={`flex min-h-11 items-center gap-2 rounded-full px-4 text-small whitespace-nowrap ${filter === f ? "bg-night-900 font-bold text-paper" : "border-[1.5px] border-line bg-paper-raised"}`}
          >
            {t(`filters.${f}`)}
            <span
              className={`rounded-full px-2 text-caption font-bold ${filter === f ? "bg-amber-500 text-night-950" : "bg-paper-sunk"}`}
            >
              {count(f)}
            </span>
          </button>
        ))}
      </div>
      {detail.children.length === 0 && (
        <p className="text-body text-ink-muted">
          {t("empty")}{" "}
          <Link href={`/portal/classes/${classId}/import`} className="font-semibold underline">
            {t("import")}
          </Link>
        </p>
      )}
      <ul className="flex flex-col gap-2.5">
        {rows.map((c) => (
          <li
            key={c.id}
            className="grid gap-3 rounded-lg border border-line bg-paper-raised p-4 md:grid-cols-[1.4fr_1fr_1.2fr_auto] md:items-center"
          >
            <div className="flex items-center gap-3">
              {c.character_id ? (
                // eslint-disable-next-line @next/next/no-img-element -- the approved drawing (never the photo), private
                <img
                  src={portalFiles.character(classId, c.id)}
                  alt={t("drawingOf", { name: c.name })}
                  className="size-12 rounded-full bg-amber-100 object-cover object-left"
                />
              ) : (
                <span className="flex size-12 items-center justify-center rounded-full bg-paper-sunk font-display font-bold text-night-900">
                  {c.name.slice(0, 1)}
                </span>
              )}
              <div className="flex flex-col">
                <strong className="text-body">{c.name}</strong>
                <span className="text-caption text-ink-muted" dir="ltr">
                  {c.parent_name ?? ""} {c.phone ?? c.email ?? ""}
                </span>
              </div>
            </div>
            <Steps
              on={[c.steps.invited, c.steps.consent, c.steps.photo, c.steps.approved]}
              label={t("stepsLabel", { name: c.name })}
            />
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone={c.stage}>{tp(`stage.${c.stage}`)}</Chip>
              {c.drawn && c.stage !== "approved" && (
                <span className="text-caption text-ink-muted">{t("waitingParent")}</span>
              )}
              {c.steps.drawing && <span className="text-caption text-ink-muted">{t("drawing")}</span>}
            </div>
            <div className="flex flex-wrap gap-2">
              {c.invite.path && c.stage !== "approved" && (
                <>
                  <button type="button" onClick={() => void copy(c)} className={buttonClasses("secondary", "sm")}>
                    {copied === c.id ? t("copied") : t("copy")}
                  </button>
                  <a
                    href={`https://wa.me/?text=${encodeURIComponent(message(c))}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() => void sent(c)}
                    className={buttonClasses("ghost", "sm")}
                  >
                    {t("whatsapp")}
                  </a>
                </>
              )}
              {c.invite.state === "expired" && (
                <button
                  type="button"
                  onClick={() => void act(() => portalApi.renewInvite(classId, c.id))}
                  className={buttonClasses("secondary", "sm")}
                >
                  {t("renew")}
                </button>
              )}
              <button
                type="button"
                onClick={() => {
                  if (window.confirm(t("removeConfirm", { name: c.name })))
                    void act(() => portalApi.removeChild(classId, c.id));
                }}
                className="min-h-11 px-2 text-small text-danger underline underline-offset-4"
              >
                {t("remove")}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
