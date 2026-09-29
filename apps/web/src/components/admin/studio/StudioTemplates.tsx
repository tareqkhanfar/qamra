"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { api, errorText } from "@/lib/api";
import { TEMPLATE_STATUSES, usd, when, type BulkResult, type StudioList, type StudioTemplate } from "@/lib/studio";
import { Pill, Select, StatusBadge, StudioTabs, inputClass, useOptionName, useVariantName } from "./parts";

type Notice = { ok: boolean; text: string } | null;

/**
 * The template studio's list (Addendum 4 §3.2): every Classic template per theme × art style × look, with its
 * status, pages, flags, one-time cost and texts; filters by theme and status; bulk copy, publish, schedule.
 */
export function StudioTemplates() {
  const t = useTranslations("studio");
  const te = useTranslations("errors");
  const locale = useLocale();
  const optionName = useOptionName();
  const [data, setData] = useState<StudioList | null>(null);
  const [theme, setTheme] = useState("");
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const [copyStyle, setCopyStyle] = useState("");
  const [date, setDate] = useState("");

  const load = useCallback(async () => {
    const q = new URLSearchParams();
    if (theme) q.set("theme", theme);
    if (status) q.set("status", status);
    const r = await api<StudioList>(`/api/admin/studio/templates?${q}`);
    if (!r.ok) {
      setNotice({ ok: false, text: errorText(r.error, locale, te("unknown")) });
      return;
    }
    setData(r.data);
    setSelected((ids) => ids.filter((id) => r.data.templates.some((x) => x.id === id)));
  }, [theme, status, locale, te]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  const groups = useMemo(() => {
    const out = new Map<string, StudioTemplate[]>();
    for (const row of data?.templates ?? []) out.set(row.theme, [...(out.get(row.theme) ?? []), row]);
    return [...out.entries()];
  }, [data]);

  async function bulk(action: string, path: string, json: object) {
    setBusy(action);
    setNotice(null);
    const r = await api<BulkResult>(`/api/admin/studio/templates/${path}`, { json: { ids: selected, ...json } });
    setBusy(null);
    if (!r.ok) {
      setNotice({ ok: false, text: errorText(r.error, locale, te("unknown")) });
      return;
    }
    const reasons = [...new Set(r.data.skipped.map((s) => t(`skip.${s.reason.split(":")[0]}`)))].join("، ");
    const text = t("bulkResult", { done: r.data.done.length, skipped: r.data.skipped.length });
    setNotice({ ok: r.data.skipped.length === 0, text: reasons ? `${text} (${reasons})` : text });
    await load();
  }

  const toggle = (id: string) => setSelected((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));

  return (
    <div className="flex flex-col gap-5 pb-40 lg:pb-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-h2 text-night-900">{t("title")}</h1>
        <p className="text-ink-muted">{t("lead")}</p>
      </header>
      <StudioTabs active="templates" />
      <div className="grid grid-cols-2 gap-3 md:max-w-xl">
        <Select label={t("filters.theme")} value={theme} onChange={setTheme}>
          <option value="">{t("filters.all")}</option>
          {data?.themes.map((o) => (
            <option key={o.slug} value={o.slug}>
              {optionName(o, o.slug)}
            </option>
          ))}
        </Select>
        <Select label={t("filters.status")} value={status} onChange={setStatus}>
          <option value="">{t("filters.all")}</option>
          {TEMPLATE_STATUSES.map((s) => (
            <option key={s} value={s}>
              {t(`status.${s}`)}
            </option>
          ))}
        </Select>
      </div>
      {notice && <Alert tone={notice.ok ? "success" : "error"}>{notice.text}</Alert>}
      {!data && <div className="h-48 animate-pulse rounded-xl bg-paper-sunk" aria-busy="true" />}
      {data && groups.length === 0 && <p className="text-ink-muted">{t("empty")}</p>}
      {groups.map(([slug, rows]) => (
        <section key={slug} aria-labelledby={`theme-${slug}`} className="flex flex-col gap-2">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 id={`theme-${slug}`} className="text-h3 text-night-900">
              {locale === "ar" ? rows[0].theme_title_ar : rows[0].theme_title_en}
              <span className="ms-2 text-small font-normal text-ink-muted">
                {t("liveVersion", { version: rows[0].live_version })}
              </span>
            </h2>
            <Link
              href={`/admin/studio/themes?theme=${slug}`}
              className="text-small font-semibold text-night-700 underline"
            >
              {t("versionsLink")}
            </Link>
          </div>
          <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-xl border border-line bg-paper-raised">
            {rows.map((row) => (
              <TemplateRow
                key={row.id}
                row={row}
                styleName={optionName(
                  data?.styles.find((s) => s.slug === row.style),
                  row.style,
                )}
                checked={selected.includes(row.id)}
                onToggle={() => toggle(row.id)}
              />
            ))}
          </ul>
        </section>
      ))}
      {selected.length > 0 && data && (
        <BulkBar
          count={selected.length}
          busy={busy}
          styles={data.styles.map((s) => ({ value: s.slug, label: optionName(s, s.slug) }))}
          copyStyle={copyStyle}
          setCopyStyle={setCopyStyle}
          date={date}
          setDate={setDate}
          onBulk={bulk}
          onClear={() => setSelected([])}
        />
      )}
    </div>
  );
}

function TemplateRow({
  row,
  styleName,
  checked,
  onToggle,
}: {
  row: StudioTemplate;
  styleName: string;
  checked: boolean;
  onToggle: () => void;
}) {
  const t = useTranslations("studio");
  const locale = useLocale();
  const variantName = useVariantName();
  const name = `${styleName} · ${variantName(row.variant)}`;
  const pct = row.pages_total ? Math.round((row.pages_drawn / row.pages_total) * 100) : 0;
  return (
    <li className="flex items-start gap-3 p-3 md:items-center">
      <input
        type="checkbox"
        checked={checked}
        onChange={onToggle}
        aria-label={t("select", { name })}
        className="mt-1 size-5 shrink-0 accent-night-900 md:mt-0"
      />
      <div className="grid min-w-0 flex-1 gap-2 md:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)_6rem_6rem_4rem] md:items-center md:gap-4">
        <div className="min-w-0">
          <Link
            href={`/admin/studio/templates/${row.id}`}
            className="font-semibold text-night-900 underline-offset-4 hover:underline"
          >
            {name}
          </Link>
          <div className="mt-1 flex flex-wrap gap-1.5">
            <StatusBadge status={row.status} />
            {row.job !== "idle" && <Pill warn={row.job === "failed"}>{t(`job.${row.job}`)}</Pill>}
            {row.texts_stale && <Pill warn>{t("textsStale")}</Pill>}
            {row.story_changed && <Pill warn>{t("storyChanged")}</Pill>}
            {row.flags.map((f) => (
              <Pill key={f} warn>
                {f}
              </Pill>
            ))}
            {row.publish_at && <Pill>{t("scheduledFor", { date: when(row.publish_at, locale) })}</Pill>}
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-caption text-ink-muted">
            {t("pagesDrawn", { drawn: row.pages_drawn, total: row.pages_total })}
          </span>
          <span className="h-1.5 overflow-hidden rounded-full bg-paper-sunk" aria-hidden="true">
            <span className="block h-full rounded-full bg-sage-700" style={{ width: `${pct}%` }} />
          </span>
        </div>
        <div className="grid grid-cols-3 gap-2 text-small md:contents">
          <span title={t("oneTimeCost")}>
            <span className="block text-caption text-ink-muted md:hidden">{t("oneTimeCost")}</span>
            <span dir="ltr" className="font-semibold tabular-nums">
              {usd(row.cost_usd)}
            </span>
          </span>
          <span className={row.vowelized ? "text-success" : "text-ink-muted"}>
            <span className="block text-caption text-ink-muted md:hidden">{t("vowelizedLabel")}</span>
            {row.vowelized ? `✓ ${t("vowelized")}` : `✗ ${t("notVowelized")}`}
          </span>
          <span>
            <span className="block text-caption text-ink-muted md:hidden">{t("themeVersion")}</span>
            <span dir="ltr">v{row.theme_version}</span>
          </span>
        </div>
      </div>
    </li>
  );
}

function BulkBar({
  count,
  busy,
  styles,
  copyStyle,
  setCopyStyle,
  date,
  setDate,
  onBulk,
  onClear,
}: {
  count: number;
  busy: string | null;
  styles: { value: string; label: string }[];
  copyStyle: string;
  setCopyStyle: (v: string) => void;
  date: string;
  setDate: (v: string) => void;
  onBulk: (action: string, path: string, json: object) => Promise<void>;
  onClear: () => void;
}) {
  const t = useTranslations("studio.bulk");
  return (
    <div
      role="region"
      aria-label={t("label")}
      className="fixed inset-x-0 bottom-0 z-20 flex flex-col gap-2 border-t border-line bg-paper-raised/95 p-3 shadow-2 backdrop-blur lg:sticky lg:bottom-4 lg:rounded-xl lg:border"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-night-900">{t("selected", { count })}</span>
        <button type="button" onClick={onClear} className="min-h-11 px-2 text-small text-ink-muted underline">
          {t("clear")}
        </button>
        <Button
          size="sm"
          loading={busy === "publish"}
          onClick={() => void onBulk("publish", "publish", { to: "live" })}
        >
          {t("publish")}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          loading={busy === "unpublish"}
          onClick={() => void onBulk("unpublish", "publish", { to: "approved" })}
        >
          {t("unpublish")}
        </Button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="datetime-local"
          aria-label={t("date")}
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className={`${inputClass} min-w-0 flex-1 sm:flex-none`}
        />
        <Button
          size="sm"
          variant="secondary"
          disabled={!date}
          loading={busy === "schedule"}
          onClick={() => void onBulk("schedule", "schedule", { publish_at: new Date(date).toISOString() })}
        >
          {t("schedule")}
        </Button>
        <button
          type="button"
          onClick={() => void onBulk("unschedule", "schedule", { publish_at: null })}
          className="min-h-11 px-2 text-small text-night-700 underline"
        >
          {t("unschedule")}
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <select
          aria-label={t("style")}
          value={copyStyle}
          onChange={(e) => setCopyStyle(e.target.value)}
          className={`${inputClass} min-w-0 flex-1 sm:flex-none`}
        >
          <option value="">{t("style")}</option>
          {styles.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <Button
          size="sm"
          variant="secondary"
          disabled={!copyStyle}
          loading={busy === "copy"}
          onClick={() => void onBulk("copy", "copy", { style: copyStyle })}
        >
          {t("copy")}
        </Button>
        <span className="text-caption text-ink-muted">{t("copyNote")}</span>
      </div>
    </div>
  );
}
