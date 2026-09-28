"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { catalogAdmin, ils, type AddOnRow } from "@/lib/catalogAdmin";
import { ActiveToggle, MarginBadge, MoneyInput, changed } from "./parts";

function Row({ row, floor, onSaved }: { row: AddOnRow; floor: number; onSaved: (r: AddOnRow) => void }) {
  const t = useTranslations("catalogAdmin");
  const te = useTranslations("errors");
  const locale = useLocale();
  const fixed = row.pricing === "fixed";
  const fields = fixed
    ? (["price_ils", "price_jod", "cost_ils", "cost_ai_usd"] as const)
    : (["cost_ils", "cost_ai_usd"] as const);
  const [draft, setDraft] = useState<Record<string, string>>(() =>
    Object.fromEntries(fields.map((f) => [f, row[f] ?? ""])),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const diff = changed(draft, row);

  async function save(patch: Record<string, unknown>) {
    setBusy(true);
    setError(null);
    const r = await catalogAdmin.addon(row.slug, patch);
    setBusy(false);
    if (r.ok) onSaved(r.data);
    else setError(errorText(r.error, locale, te("unknown")));
  }

  return (
    <tr className="border-b border-line/60 align-top">
      <td className="px-2 py-2">
        <div className="font-semibold">{locale === "ar" ? row.name_ar : row.name_en}</div>
        <div className="text-caption text-ink-muted">
          {row.lines.map((l) => t(`lines.${l}`)).join("، ")}
          {row.included_lines.length > 0 &&
            ` · ${t("includedIn", { lines: row.included_lines.map((l) => t(`lines.${l}`)).join("، ") })}`}
        </div>
      </td>
      {fixed ? (
        (["price_ils", "price_jod"] as const).map((f) => (
          <td key={f} className="px-1 py-2">
            <MoneyInput
              label={t(`fields.${f}`)}
              value={draft[f]}
              onChange={(e) => setDraft((d) => ({ ...d, [f]: e.target.value }))}
            />
          </td>
        ))
      ) : (
        <td colSpan={2} className="px-2 py-2 text-small text-ink-muted">
          {t("percentOfItem", { n: Number(row.percent) })}
        </td>
      )}
      {(["cost_ils", "cost_ai_usd"] as const).map((f) => (
        <td key={f} className="px-1 py-2">
          <MoneyInput
            label={t(`fields.${f}`)}
            value={draft[f]}
            onChange={(e) => setDraft((d) => ({ ...d, [f]: e.target.value }))}
          />
        </td>
      ))}
      <td className="px-2 py-2 tabular-nums">{ils(row.unit_cost_ils)}</td>
      <td className="px-2 py-2">
        <MarginBadge value={row.margin_pct} low={row.margin_pct !== null && Number(row.margin_pct) < floor} />
      </td>
      <td className="px-2 py-2">
        <ActiveToggle on={row.active} label={t("active")} onChange={(v) => void save({ active: v })} />
      </td>
      <td className="px-2 py-2">
        <Button size="sm" disabled={!Object.keys(diff).length} loading={busy} onClick={() => void save(diff)}>
          {t("save")}
        </Button>
        {error && <p className="mt-1 text-caption text-danger">{error}</p>}
      </td>
    </tr>
  );
}

/** Extras: price, what one costs us, and its margin. */
export function AddOnsTable({ rows, floor, onRow }: { rows: AddOnRow[]; floor: number; onRow: (r: AddOnRow) => void }) {
  const t = useTranslations("catalogAdmin");
  return (
    <div className="overflow-x-auto rounded-lg border border-line bg-paper-raised">
      <table className="w-full min-w-[960px] text-small">
        <thead className="bg-paper-sunk text-caption text-ink-muted">
          <tr>
            <th className="px-2 py-2 text-start">{t("addon")}</th>
            <th className="px-1 py-2 text-start">{t("fields.price_ils")}</th>
            <th className="px-1 py-2 text-start">{t("fields.price_jod")}</th>
            <th className="px-1 py-2 text-start">{t("fields.cost_ils")}</th>
            <th className="px-1 py-2 text-start">{t("fields.cost_ai_usd")}</th>
            <th className="px-2 py-2 text-start">{t("unitCost")}</th>
            <th className="px-2 py-2 text-start">{t("marginPct")}</th>
            <th className="px-2 py-2 text-start">{t("active")}</th>
            <th className="px-2 py-2" />
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <Row key={`${r.slug}-${r.price_ils}-${r.cost_ils}-${r.active}`} row={r} floor={floor} onSaved={onRow} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
