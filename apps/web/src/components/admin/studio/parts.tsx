"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, type ReactNode } from "react";
import { Link } from "@/i18n/navigation";
import { errorText, type ApiErrorBody } from "@/lib/api";
import { STATUS_TONE, type Option, type VersionStatus } from "@/lib/studio";

/** draft / in review / approved / live / retired, as a small colored pill. */
export function StatusBadge({ status, children }: { status: VersionStatus; children?: ReactNode }) {
  const t = useTranslations("studio.status");
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-caption font-bold ${STATUS_TONE[status]}`}
    >
      {t(status)}
      {children}
    </span>
  );
}

/** A quiet pill for flags and notes (warning tone when it needs attention). */
export function Pill({ warn, children }: { warn?: boolean; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-bold ${warn ? "bg-warning-bg text-warning" : "bg-paper-sunk text-ink-muted"}`}
    >
      {children}
    </span>
  );
}

/** Localized name of a theme or art style option. */
export function useOptionName(): (o: Option | undefined, fallback: string) => string {
  const locale = useLocale();
  return (o, fallback) => (o ? (locale === "ar" ? o.title_ar : o.title_en) : fallback);
}

/** A template's or page's flag in words: the studio's own flags, then the review queue's (the page checks). */
export function useFlagName(): (flag: string) => string {
  const ts = useTranslations("studio.flags");
  const tq = useTranslations("queue.flags");
  return (f) => (ts.has(f) ? ts(f) : tq.has(f) ? tq(f) : f);
}

/**
 * An API error in words: its own message, except two codes shared with books and orders, whose messages speak
 * of a book or an order; the studio says them about its own work.
 */
export function useStudioError(): (error: ApiErrorBody | null) => string {
  const t = useTranslations("studio.errors");
  const te = useTranslations("errors");
  const locale = useLocale();
  return useCallback(
    (error: ApiErrorBody | null) =>
      error?.code === "busy"
        ? t("busy")
        : error?.code === "invalid_transition"
          ? t("moved")
          : errorText(error, locale, te("unknown")),
    [t, te, locale],
  );
}

/** The template looks: girl, girl with hijab, boy. */
export function useVariantName(): (v: string) => string {
  const t = useTranslations("studio.variant");
  return (v) => (["girl", "girl_hijab", "boy"].includes(v) ? t(v) : v);
}

/** The studio's own tabs (themes · Classic templates), shown above each studio page. */
export function StudioTabs({ active }: { active: "templates" | "themes" }) {
  const t = useTranslations("studio.tabs");
  const tabs = [
    { id: "themes", href: "/admin/studio/themes" },
    { id: "templates", href: "/admin/studio" },
  ] as const;
  return (
    <nav aria-label={t("label")} className="flex gap-2 border-b border-line">
      {tabs.map((tab) => (
        <Link
          key={tab.id}
          href={tab.href}
          aria-current={active === tab.id ? "page" : undefined}
          className={`-mb-px flex min-h-11 items-center border-b-2 px-3 font-semibold ${active === tab.id ? "border-night-900 text-night-900" : "border-transparent text-ink-muted hover:text-night-900"}`}
        >
          {t(tab.id)}
        </Link>
      ))}
    </nav>
  );
}

/** A labelled select for the filters. */
export function Select({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  children: ReactNode;
}) {
  return (
    <label className="flex min-w-0 flex-col gap-1 text-small font-semibold text-ink">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="min-h-11 rounded-sm border border-line bg-white px-3 text-body font-normal outline-none focus:border-night-900 focus:ring-2 focus:ring-night-100"
      >
        {children}
      </select>
    </label>
  );
}

export const inputClass =
  "min-h-11 rounded-sm border border-line bg-white px-3 text-body outline-none focus:border-night-900 focus:ring-2 focus:ring-night-100";
