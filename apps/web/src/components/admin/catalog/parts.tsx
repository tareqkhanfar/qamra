"use client";

import { useTranslations } from "next-intl";
import type { InputHTMLAttributes } from "react";
import { pct } from "@/lib/catalogAdmin";

/** A compact number field for prices and costs (Latin digits, left-to-right). */
export function MoneyInput({ label, ...rest }: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <input
      {...rest}
      inputMode="decimal"
      dir="ltr"
      aria-label={label}
      className="min-h-10 w-24 rounded-sm border border-line bg-white px-2 text-small tabular-nums outline-none focus:border-night-900 focus:ring-2 focus:ring-night-100"
    />
  );
}

/** The margin in %, red under the floor. */
export function MarginBadge({ value, low }: { value: string | null; low: boolean }) {
  const t = useTranslations("catalogAdmin");
  if (value === null) return <span className="text-ink-faint">—</span>;
  return (
    <span
      title={low ? t("belowFloor") : undefined}
      className={`inline-flex rounded-full px-2 py-0.5 text-caption font-bold tabular-nums ${low ? "bg-danger-bg text-danger" : "bg-success-bg text-success"}`}
    >
      {low && "⚠ "}
      {pct(value)}
    </span>
  );
}

/** On/off switch for "active". */
export function ActiveToggle({ on, onChange, label }: { on: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={() => onChange(!on)}
      className={`relative h-6 w-11 shrink-0 rounded-full transition ${on ? "bg-success" : "bg-line"}`}
    >
      <span
        className={`absolute top-0.5 size-5 rounded-full bg-white shadow transition-all ${on ? "start-[1.375rem]" : "start-0.5"}`}
      />
    </button>
  );
}

/** Only the fields whose text changed, as the API wants them. */
export function changed(draft: Record<string, string>, row: Record<string, unknown>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(draft)) {
    const before = row[k] === null || row[k] === undefined ? "" : String(row[k]);
    if (v.trim() !== "" && Number(v) !== Number(before)) out[k] = v.trim();
  }
  return out;
}
