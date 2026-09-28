"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { catalogAdmin, ils, type ZoneRow } from "@/lib/catalogAdmin";
import { ActiveToggle, MoneyInput, changed } from "./parts";

const FIELDS = ["fee", "free_over", "cod_fee", "cost_ils"] as const;

function Row({ row, onSaved }: { row: ZoneRow; onSaved: (r: ZoneRow) => void }) {
  const t = useTranslations("catalogAdmin");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [draft, setDraft] = useState<Record<string, string>>(() =>
    Object.fromEntries(FIELDS.map((f) => [f, row[f] ?? ""])),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const diff = changed(draft, row);
  const clearFree = row.free_over !== null && draft.free_over.trim() === "";

  async function save(patch: Record<string, unknown>) {
    setBusy(true);
    setError(null);
    const r = await catalogAdmin.zone(row.slug, patch);
    setBusy(false);
    if (r.ok) onSaved(r.data);
    else setError(errorText(r.error, locale, te("unknown")));
  }

  const unit = row.currency === "JOD" ? "JD" : "₪";
  return (
    <tr className="border-b border-line/60 align-top">
      <td className="px-2 py-2">
        <div className="font-semibold">{locale === "ar" ? row.name_ar : row.name_en}</div>
        <div className="text-caption text-ink-muted">{unit}</div>
      </td>
      {FIELDS.map((f) => (
        <td key={f} className="px-1 py-2">
          <MoneyInput
            label={t(`zoneFields.${f}`)}
            value={draft[f]}
            placeholder={f === "free_over" ? t("noFreeDelivery") : undefined}
            onChange={(e) => setDraft((d) => ({ ...d, [f]: e.target.value }))}
          />
        </td>
      ))}
      <td className={`px-2 py-2 tabular-nums ${Number(row.fee_margin_ils) < 0 ? "font-bold text-danger" : ""}`}>
        {ils(row.fee_margin_ils)}
      </td>
      <td className="px-2 py-2">
        <ActiveToggle on={row.active} label={t("active")} onChange={(v) => void save({ active: v })} />
      </td>
      <td className="px-2 py-2">
        <Button
          size="sm"
          disabled={!Object.keys(diff).length && !clearFree}
          loading={busy}
          onClick={() => void save({ ...diff, ...(clearFree ? { clear_free_over: true } : {}) })}
        >
          {t("save")}
        </Button>
        {error && <p className="mt-1 text-caption text-danger">{error}</p>}
      </td>
    </tr>
  );
}

/** Delivery zones: what the customer pays, what a parcel costs us. */
export function ZonesTable({ rows, onRow }: { rows: ZoneRow[]; onRow: (r: ZoneRow) => void }) {
  const t = useTranslations("catalogAdmin");
  return (
    <div className="overflow-x-auto rounded-lg border border-line bg-paper-raised">
      <table className="w-full min-w-[820px] text-small">
        <thead className="bg-paper-sunk text-caption text-ink-muted">
          <tr>
            <th className="px-2 py-2 text-start">{t("zone")}</th>
            {FIELDS.map((f) => (
              <th key={f} className="px-1 py-2 text-start">
                {t(`zoneFields.${f}`)}
              </th>
            ))}
            <th className="px-2 py-2 text-start">{t("feeMargin")}</th>
            <th className="px-2 py-2 text-start">{t("active")}</th>
            <th className="px-2 py-2" />
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <Row key={`${r.slug}-${r.fee}-${r.free_over}-${r.cost_ils}-${r.active}`} row={r} onSaved={onRow} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
