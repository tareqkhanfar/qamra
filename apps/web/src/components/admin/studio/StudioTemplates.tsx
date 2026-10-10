"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Link, useRouter } from "@/i18n/navigation";
import { api } from "@/lib/api";
import {
  TEMPLATE_STATUSES,
  usd,
  when,
  type BulkResult,
  type StudioList,
  type StudioTemplate,
  type TemplateDetail,
} from "@/lib/studio";
import {
  Pill,
  Select,
  StatusBadge,
  StudioTabs,
  inputClass,
  useFlagName,
  useOptionName,
  useStudioError,
  useVariantName,
} from "./parts";

type Notice = { ok: boolean; text: string } | null;

/**
 * The template studio's list (Addendum 4 §3.2): every Classic template per theme × art style × look, with its
 * status, pages, flags, one-time cost and texts; filters by theme and status; bulk copy, publish, schedule;
 * and «قالب جديد», which starts drawing a template for a story × style × look (or a free dry run).
 */
export function StudioTemplates() {
  const t = useTranslations("studio");
  const locale = useLocale();
  const studioError = useStudioError();
  const optionName = useOptionName();
  const [data, setData] = useState<StudioList | null>(null);
  const [theme, setTheme] = useState("");
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const [copyStyle, setCopyStyle] = useState("");
  const [date, setDate] = useState("");
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
    const q = new URLSearchParams();
    if (theme) q.set("theme", theme);
    if (status) q.set("status", status);
    const r = await api<StudioList>(`/api/admin/studio/templates?${q}`);
    if (!r.ok) {
      setNotice({ ok: false, text: studioError(r.error) });
      return;
    }
    setData(r.data);
    setSelected((ids) => ids.filter((id) => r.data.templates.some((x) => x.id === id)));
  }, [theme, status, studioError]);

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
      setNotice({ ok: false, text: studioError(r.error) });
      return;
    }
    const reasons = [...new Set(r.data.skipped.map((s) => t(`skip.${s.reason.split(":")[0]}`)))].join("، ");
    const text = t("bulkResult", { done: r.data.done.length, skipped: r.data.skipped.length });
    setNotice({ ok: r.data.skipped.length === 0, text: reasons ? `${text} (${reasons})` : text });
    await load();
  }

  const none = !!data && data.templates.length === 0 && !theme && !status; // no template yet: the form is open
  const toggle = (id: string) => setSelected((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));

  return (
    <div className="flex flex-col gap-5 pb-40 lg:pb-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-h2 text-night-900">{t("title")}</h1>
        <p className="text-ink-muted">{t("lead")}</p>
      </header>
      <StudioTabs active="templates" />
      {data && (adding || none) ? (
        <NewTemplate data={data} onCancel={none ? undefined : () => setAdding(false)} />
      ) : (
        <Button size="sm" variant="secondary" className="self-start" onClick={() => setAdding(true)}>
          {t("new.open")}
        </Button>
      )}
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
      {!data && !notice && <div className="h-48 animate-pulse rounded-xl bg-paper-sunk" aria-busy="true" />}
      {data && groups.length === 0 && <p className="text-ink-muted">{t(theme || status ? "empty" : "emptyAll")}</p>}
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
  const flagName = useFlagName();
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
                {flagName(f)}
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

const DEFAULT_BUDGET = "3"; // US dollars per drawing run, like a book's default cap (admin settings)

/**
 * «قالب جديد»: a story × art style × look, drawn once by the image model up to a cost cap (a real cost, asked
 * again before it starts), or a dry run with placeholder pictures and no model call. The new template opens in
 * its editor while its pages are drawn.
 */
function NewTemplate({ data, onCancel }: { data: StudioList; onCancel?: () => void }) {
  const t = useTranslations("studio.new");
  const router = useRouter();
  const studioError = useStudioError();
  const optionName = useOptionName();
  const variantName = useVariantName();
  const [theme, setTheme] = useState(data.themes[0]?.slug ?? "");
  const [style, setStyle] = useState(data.styles[0]?.slug ?? "");
  const [variant, setVariant] = useState(data.variants[0] ?? "girl");
  const [budget, setBudget] = useState(DEFAULT_BUDGET);
  const [offline, setOffline] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cap = Number(budget);
  const capOk = Number.isFinite(cap) && cap >= 0.5 && cap <= 20;

  async function start() {
    if (!offline && !window.confirm(t("confirm", { usd: usd(cap) }))) return;
    setBusy(true);
    setError(null);
    const r = await api<TemplateDetail>("/api/admin/classic/templates", {
      json: { theme, style, variant, offline, ...(offline ? {} : { budget_usd: cap.toFixed(2) }) },
    });
    setBusy(false);
    if (!r.ok) return setError(studioError(r.error));
    router.push(`/admin/studio/templates/${r.data.id}`);
  }

  return (
    <section
      aria-labelledby="new-template"
      className="flex flex-col gap-3 rounded-xl border border-line bg-paper-raised p-4 md:max-w-3xl"
    >
      <h2 id="new-template" className="text-h3 text-night-900">
        {t("title")}
      </h2>
      <p className="text-small text-ink-muted">{t("lead")}</p>
      <div className="grid gap-3 sm:grid-cols-3">
        <Select label={t("theme")} value={theme} onChange={setTheme}>
          {data.themes.map((o) => (
            <option key={o.slug} value={o.slug}>
              {optionName(o, o.slug)}
            </option>
          ))}
        </Select>
        <Select label={t("style")} value={style} onChange={setStyle}>
          {data.styles.map((o) => (
            <option key={o.slug} value={o.slug}>
              {optionName(o, o.slug)}
            </option>
          ))}
        </Select>
        <Select label={t("variant")} value={variant} onChange={setVariant}>
          {data.variants.map((v) => (
            <option key={v} value={v}>
              {variantName(v)}
            </option>
          ))}
        </Select>
      </div>
      <label className="flex min-h-11 items-start gap-2 text-small">
        <input
          type="checkbox"
          checked={offline}
          onChange={(e) => setOffline(e.target.checked)}
          className="mt-1 size-5 shrink-0 accent-night-900"
        />
        <span>
          <span className="font-semibold">{t("offline")}</span>
          <span className="block text-ink-muted">{t("offlineNote")}</span>
        </span>
      </label>
      {!offline && (
        <label className="flex max-w-xs flex-col gap-1 text-small font-semibold">
          {t("budget")}
          <input
            type="number"
            inputMode="decimal"
            dir="ltr"
            min={0.5}
            max={20}
            step={0.5}
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            aria-invalid={!capOk}
            className={inputClass}
          />
        </label>
      )}
      <p
        className={`rounded-md p-3 text-small ${offline ? "bg-paper-sunk text-ink-muted" : "bg-warning-bg text-night-900"}`}
      >
        {offline ? t("offlineCost") : t("cost", { usd: usd(capOk ? cap : 0) })}
      </p>
      {error && <Alert>{error}</Alert>}
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          disabled={!theme || !style || (!offline && !capOk)}
          loading={busy}
          onClick={() => void start()}
        >
          {offline ? t("startOffline") : t("start")}
        </Button>
        {onCancel && (
          <Button size="sm" variant="ghost" onClick={onCancel}>
            {t("cancel")}
          </Button>
        )}
      </div>
    </section>
  );
}
