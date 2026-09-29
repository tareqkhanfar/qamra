"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { api, errorText } from "@/lib/api";
import {
  usd,
  when,
  type ThemeDetail,
  type ThemeSummary,
  type TranslateEstimate,
  type Version,
  type VersionDetail,
} from "@/lib/studio";
import { Pill, Select, StatusBadge, StudioTabs } from "./parts";

type Notice = { ok: boolean; text: string } | null;
type Action = {
  key: string;
  label: string;
  path: string;
  method?: string;
  json?: unknown;
  ask?: string;
  solid?: boolean;
};

/**
 * Theme versions (Addendum 4 §3.1): draft → in review → approved → live, with the history and rollback. Each
 * version shows what changed against the live one. «English draft» shows its estimate before any model call.
 */
export function ThemeVersions({ initialTheme }: { initialTheme: string | null }) {
  const t = useTranslations("studio.versions");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [themes, setThemes] = useState<ThemeSummary[] | null>(null);
  const [slug, setSlug] = useState<string | null>(initialTheme);
  const [detail, setDetail] = useState<ThemeDetail | null>(null);
  const [open, setOpen] = useState<VersionDetail | null>(null);
  const [estimate, setEstimate] = useState<{ version: number; value: TranslateEstimate } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const current = slug ?? themes?.[0]?.slug ?? null;
  const fail = useCallback(
    (error: Parameters<typeof errorText>[0]) => setNotice({ ok: false, text: errorText(error, locale, te("unknown")) }),
    [locale, te],
  );

  const load = useCallback(async () => {
    const list = await api<ThemeSummary[]>("/api/admin/themes");
    if (!list.ok) return fail(list.error);
    setThemes(list.data);
    const pick = current ?? list.data[0]?.slug;
    if (!pick) return;
    const r = await api<ThemeDetail>(`/api/admin/themes/${pick}`);
    if (r.ok) setDetail(r.data);
    else fail(r.error);
  }, [current, fail]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  async function show(version: number) {
    if (open?.version === version) return setOpen(null);
    const r = await api<VersionDetail>(`/api/admin/themes/${current}/versions/${version}`);
    if (r.ok) setOpen(r.data);
    else fail(r.error);
  }

  async function act(a: Action) {
    if (a.ask && !window.confirm(a.ask)) return;
    setBusy(a.key);
    setNotice(null);
    const r = await api<VersionDetail | undefined>(a.path, { method: a.method, json: a.json });
    setBusy(null);
    if (!r.ok) {
      const problems = (r.error?.details?.problems as string[] | undefined)?.join(" · ");
      return setNotice({
        ok: false,
        text: [errorText(r.error, locale, te("unknown")), problems].filter(Boolean).join(" — "),
      });
    }
    setEstimate(null);
    setOpen(null);
    setNotice({ ok: true, text: t("done") });
    await load();
  }

  async function askEstimate(version: number) {
    const r = await api<TranslateEstimate>(`/api/admin/themes/${current}/versions/${version}/translate`);
    if (r.ok) setEstimate({ version, value: r.data });
    else fail(r.error);
  }

  function actions(v: Version): Action[] {
    const base = `/api/admin/themes/${current}/versions/${v.version}`;
    const status = (to: string, solid = false): Action => ({
      key: `${v.version}:${to}`,
      label: t(`to.${to}`),
      path: `${base}/status`,
      json: { to },
      solid,
    });
    const translate: Action = { key: `${v.version}:estimate`, label: t("translate"), path: "" };
    const hasOpen = !!detail?.open;
    switch (v.status) {
      case "draft":
        return [
          status("in_review", true),
          translate,
          { key: `${v.version}:discard`, label: t("discard"), path: base, method: "DELETE", ask: t("confirmDiscard") },
        ];
      case "in_review":
        return [status("approved", true), status("draft")];
      case "approved":
        return [
          {
            key: `${v.version}:publish`,
            label: t("publish"),
            path: `${base}/publish`,
            json: {},
            solid: true,
            ask: t("confirmPublish"),
          },
          status("draft"),
        ];
      case "retired":
        return [
          {
            key: `${v.version}:rollback`,
            label: t("rollback"),
            path: `${base}/rollback`,
            json: {},
            ask: t("confirmRollback", { version: v.version }),
          },
        ];
      default:
        return hasOpen
          ? []
          : [{ key: "new", label: t("newDraft"), path: `/api/admin/themes/${current}/versions`, json: {} }, translate];
    }
  }

  const name = (th: ThemeSummary | ThemeDetail) => (locale === "ar" ? th.title_ar : th.title_en);
  const pick = (value: string) => {
    setSlug(value);
    setOpen(null);
    setEstimate(null);
  };
  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-1">
        <h1 className="text-h2 text-night-900">{t("title")}</h1>
        <p className="text-ink-muted">{t("lead")}</p>
      </header>
      <StudioTabs active="themes" />
      {notice && <Alert tone={notice.ok ? "success" : "error"}>{notice.text}</Alert>}
      {!themes && <div className="h-48 animate-pulse rounded-xl bg-paper-sunk" aria-busy="true" />}
      {themes && (
        <div className="grid gap-5 lg:grid-cols-[260px_minmax(0,1fr)]">
          <div className="lg:hidden">
            <Select label={t("theme")} value={current ?? ""} onChange={pick}>
              {themes.map((th) => (
                <option key={th.slug} value={th.slug}>
                  {name(th)}
                </option>
              ))}
            </Select>
          </div>
          <ul className="hidden flex-col divide-y divide-line self-start overflow-hidden rounded-xl border border-line bg-paper-raised lg:flex">
            {themes.map((th) => (
              <li key={th.slug}>
                <button
                  type="button"
                  onClick={() => pick(th.slug)}
                  aria-current={th.slug === current ? "true" : undefined}
                  className={`flex w-full flex-col gap-0.5 p-3 text-start ${th.slug === current ? "bg-night-100" : "hover:bg-paper-sunk"}`}
                >
                  <span className="font-semibold text-night-900">{name(th)}</span>
                  <span className="text-caption text-ink-muted">
                    {t("summary", { live: th.live_version, count: th.versions })}
                    {th.open && ` · ${t("openVersion", { version: th.open.version })}`}
                  </span>
                  {th.stale_templates > 0 && (
                    <span className="text-caption font-semibold text-warning">
                      {t("staleTemplates", { count: th.stale_templates })}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
          {detail && detail.slug === current && (
            <section className="flex min-w-0 flex-col gap-3" aria-labelledby="theme-title">
              <div className="flex flex-wrap items-center gap-2">
                <h2 id="theme-title" className="text-h3 text-night-900">
                  {name(detail)}
                </h2>
                <StatusBadge status="live">
                  <span dir="ltr">v{detail.live_version}</span>
                </StatusBadge>
                {detail.stale_templates > 0 && (
                  <Pill warn>{t("staleTemplates", { count: detail.stale_templates })}</Pill>
                )}
              </div>
              <ol className="flex flex-col gap-3">
                {detail.history.map((v) => (
                  <li key={v.version} className="flex flex-col gap-2 rounded-xl border border-line bg-paper-raised p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-display text-h3 text-night-900" dir="ltr">
                        v{v.version}
                      </span>
                      <StatusBadge status={v.status} />
                      <Pill>{t(`source.${v.source}`)}</Pill>
                      {v.base_version !== null && (
                        <span className="text-caption text-ink-muted">{t("basedOn", { version: v.base_version })}</span>
                      )}
                      {v.translate && (
                        <Pill warn={v.translate.state === "failed"}>
                          {t(`translateState.${v.translate.state}`, { cost: usd(v.translate.cost_usd ?? 0) })}
                        </Pill>
                      )}
                    </div>
                    {v.note && <p className="text-small">{v.note}</p>}
                    <p className="text-caption text-ink-muted">
                      {t("created", { who: v.created_by ?? t("files"), at: when(v.created_at, locale) })}
                      {v.published_at &&
                        ` · ${t("published", { who: v.published_by ?? t("files"), at: when(v.published_at, locale) })}`}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {actions(v).map((a) =>
                        a.key.endsWith(":estimate") ? (
                          <Button key={a.key} size="sm" variant="secondary" onClick={() => void askEstimate(v.version)}>
                            {a.label}
                          </Button>
                        ) : (
                          <Button
                            key={a.key}
                            size="sm"
                            variant={a.solid ? "solid" : "secondary"}
                            loading={busy === a.key}
                            onClick={() => void act(a)}
                          >
                            {a.label}
                          </Button>
                        ),
                      )}
                      <Button size="sm" variant="ghost" onClick={() => void show(v.version)}>
                        {open?.version === v.version ? t("hideChanges") : t("showChanges")}
                      </Button>
                    </div>
                    {estimate?.version === v.version && (
                      <div className="flex flex-col gap-2 rounded-md bg-amber-100 p-3 text-small text-night-900">
                        <p>
                          {t("estimate", {
                            usd: usd(estimate.value.usd),
                            pages: estimate.value.pages,
                            model: estimate.value.model,
                          })}
                        </p>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            loading={busy === "translate"}
                            onClick={() =>
                              void act({
                                key: "translate",
                                label: "",
                                path: `/api/admin/themes/${current}/versions/${v.version}/translate`,
                                json: { confirm: true },
                              })
                            }
                          >
                            {t("translateConfirm")}
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setEstimate(null)}>
                            {t("cancel")}
                          </Button>
                        </div>
                      </div>
                    )}
                    {open?.version === v.version && <Changes detail={open} />}
                  </li>
                ))}
              </ol>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

function Changes({ detail }: { detail: VersionDetail }) {
  const t = useTranslations("studio.versions");
  const label = (key: string) => {
    const [kind, a] = key.split(":");
    const lang = key.endsWith("_en") || key.endsWith(":en") ? "en" : "ar";
    if (kind === "page") return t("keys.page", { n: a, lang: t(`langs.${lang}`) });
    if (kind === "question") return t("keys.question", { n: a, lang: t(`langs.${lang}`) });
    return t(`keys.${kind.replace(/_(ar|en)$/, "")}`, { lang: t(`langs.${lang}`) });
  };
  if (!detail.changes.length)
    return <p className="text-small text-ink-muted">{t("noChanges", { live: detail.live_version })}</p>;
  return (
    <div className="flex flex-col gap-2 border-t border-dashed border-line pt-3">
      <p className="text-caption text-ink-muted">{t("changesAgainst", { live: detail.live_version })}</p>
      <ul className="flex flex-col gap-2">
        {detail.changes.map((c) => (
          <li key={c.key} className="rounded-md border border-line p-2 text-small">
            <div className="font-semibold text-night-900">{label(c.key)}</div>
            <del dir="auto" className="block text-danger">
              {c.before || "—"}
            </del>
            <ins dir="auto" className="block text-success no-underline">
              {c.after || "—"}
            </ins>
          </li>
        ))}
      </ul>
    </div>
  );
}
