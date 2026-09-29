"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { api, errorText } from "@/lib/api";
import { catalogAdmin, type AddOnRow, type OfferRow } from "@/lib/catalogAdmin";
import { ActiveToggle, MoneyInput } from "./parts";

/** Addendum 9 in the catalog admin: gift cards, the bundle rules (e.g. «الكتاب الثاني −15%») and the add-ons
 * step's rules (dependencies, the open list, badges). Everything the order path reads is edited here. */

const input =
  "min-h-10 rounded-sm border border-line bg-white px-2 text-small outline-none focus:border-night-900 focus:ring-2 focus:ring-night-100";

type GiftCard = {
  id: string;
  code: string;
  currency: "ILS" | "JOD";
  amount: string;
  balance: string;
  expires_at: string | null;
  active: boolean;
  status: "active" | "used" | "expired" | "disabled";
  note: string | null;
  uses: number;
  created_at: string;
};

const cards = {
  list: () => api<GiftCard[]>("/api/admin/gift-cards"),
  issue: (body: Record<string, unknown>) => api<GiftCard>("/api/admin/gift-cards", { json: body }),
  edit: (id: string, patch: Record<string, unknown>) =>
    api<GiftCard>(`/api/admin/gift-cards/${id}`, { method: "PATCH", json: patch }),
};

export function GiftCardsPanel() {
  const t = useTranslations("orderPath.admin");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [rows, setRows] = useState<GiftCard[] | null>(null);
  const [form, setForm] = useState({ amount: "", currency: "ILS", expires: "", note: "" });
  const [issued, setIssued] = useState<GiftCard | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const r = await cards.list();
      if (r.ok) setRows(r.data);
      else setError(errorText(r.error, locale, te("unknown")));
    })();
  }, [locale, te]);

  async function issue() {
    setBusy(true);
    setError(null);
    const r = await cards.issue({
      amount: form.amount.trim(),
      currency: form.currency,
      expires_at: form.expires ? new Date(`${form.expires}T23:59:00`).toISOString() : null,
      note: form.note.trim() || null,
    });
    setBusy(false);
    if (!r.ok) return setError(errorText(r.error, locale, te("unknown")));
    setIssued(r.data);
    setRows((list) => [r.data, ...(list ?? [])]);
    setForm({ amount: "", currency: form.currency, expires: "", note: "" });
  }

  const money = (v: string, c: string) => `${Number(v)} ${c === "JOD" ? "JD" : "₪"}`;
  return (
    <section className="flex flex-col gap-3">
      <p className="max-w-3xl text-small text-ink-muted">{t("cardsIntro")}</p>
      {error && <Alert>{error}</Alert>}
      <form
        className="flex flex-wrap items-end gap-2 rounded-lg border border-line bg-paper-raised p-3"
        onSubmit={(e) => {
          e.preventDefault();
          void issue();
        }}
      >
        <MoneyInput
          label={t("amount")}
          placeholder={t("amount")}
          value={form.amount}
          onChange={(e) => setForm({ ...form, amount: e.target.value })}
        />
        <select
          aria-label={t("currency")}
          value={form.currency}
          onChange={(e) => setForm({ ...form, currency: e.target.value })}
          className={input}
        >
          <option value="ILS">₪</option>
          <option value="JOD">JD</option>
        </select>
        <input
          type="date"
          aria-label={t("expires")}
          title={t("expires")}
          value={form.expires}
          onChange={(e) => setForm({ ...form, expires: e.target.value })}
          className={input}
        />
        <input
          aria-label={t("note")}
          placeholder={t("note")}
          maxLength={200}
          value={form.note}
          onChange={(e) => setForm({ ...form, note: e.target.value })}
          className={`${input} w-56`}
        />
        <Button size="sm" type="submit" loading={busy} disabled={!form.amount.trim()}>
          {t("issue")}
        </Button>
      </form>
      {issued && (
        <Alert tone="info">
          {t("issued")}{" "}
          <code dir="ltr" className="font-bold select-all">
            {issued.code}
          </code>
        </Alert>
      )}
      <ul className="flex flex-col divide-y divide-line rounded-lg border border-line bg-paper-raised">
        {(rows ?? []).map((c) => (
          <li key={c.id} className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 text-small">
            <span className="flex flex-wrap items-center gap-2">
              <code dir="ltr" className="font-bold">
                {c.code}
              </code>
              <span>
                {t("balance", { balance: money(c.balance, c.currency), amount: money(c.amount, c.currency) })}
              </span>
              <span className="rounded-full bg-paper-sunk px-2 py-0.5 text-caption font-bold">
                {t(`statuses.${c.status}`)}
              </span>
              <span className="text-caption text-ink-muted">
                {t("uses", { n: c.uses })}
                {c.expires_at && ` · ${t("until", { date: c.expires_at.slice(0, 10) })}`}
                {c.note && ` · ${c.note}`}
              </span>
            </span>
            <ActiveToggle
              on={c.active}
              label={t("active")}
              onChange={async (v) => {
                const r = await cards.edit(c.id, { active: v });
                if (r.ok) setRows((list) => (list ?? []).map((x) => (x.id === c.id ? r.data : x)));
              }}
            />
          </li>
        ))}
        {rows && !rows.length && <li className="px-3 py-3 text-small text-ink-muted">{t("noCards")}</li>}
      </ul>
    </section>
  );
}

type Bundle = OfferRow & { min_items?: number | null };
const KINDS = ["cheapest", "min_items", "siblings"] as const;

/** Bundle rules: the kind (discount the cheaper book in every N, every book, or siblings), N and the %. */
export function BundleRules({ rows, onRow }: { rows: Bundle[]; onRow: (row: OfferRow) => void }) {
  const t = useTranslations("orderPath.admin");
  const tc = useTranslations("catalogAdmin");
  const locale = useLocale();
  const [draft, setDraft] = useState<Record<string, { kind: string; min: string; pct: string }>>({});
  const [error, setError] = useState<string | null>(null);

  async function save(b: Bundle, patch: Record<string, unknown>) {
    const r = await catalogAdmin.bundle(b.id, patch);
    if (!r.ok) return setError(errorText(r.error, locale, "—"));
    setError(null);
    setDraft((all) => Object.fromEntries(Object.entries(all).filter(([id]) => id !== b.id)));
    onRow(r.data);
  }

  return (
    <div className="flex flex-col gap-2">
      {error && <Alert>{error}</Alert>}
      <ul className="flex flex-col divide-y divide-line rounded-lg border border-line bg-paper-raised">
        {rows.map((b) => {
          const d = draft[b.id] ?? { kind: b.kind, min: String(b.min_items ?? 2), pct: String(Number(b.discount_pct)) };
          const changed = !!draft[b.id];
          const edit = (patch: Partial<typeof d>) => setDraft((all) => ({ ...all, [b.id]: { ...d, ...patch } }));
          return (
            <li key={b.id} className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 text-small">
              <span className="flex flex-wrap items-center gap-2">
                <strong>{locale === "ar" ? b.name_ar : b.name_en}</strong>
                <select
                  aria-label={t("bundleKind")}
                  value={d.kind}
                  onChange={(e) => edit({ kind: e.target.value })}
                  className={input}
                >
                  {KINDS.map((k) => (
                    <option key={k} value={k}>
                      {t(`kinds.${k}`, { n: d.min })}
                    </option>
                  ))}
                </select>
                <MoneyInput label={t("bundleMin")} value={d.min} onChange={(e) => edit({ min: e.target.value })} />
                <MoneyInput label={t("bundlePct")} value={d.pct} onChange={(e) => edit({ pct: e.target.value })} />
                <span className="text-caption text-ink-muted">
                  % · {b.lines.length ? b.lines.map((l) => tc(`lines.${l}`)).join("، ") : tc("allLines")}
                </span>
                {changed && (
                  <Button
                    size="sm"
                    onClick={() => void save(b, { kind: d.kind, min_items: Number(d.min), discount_pct: d.pct })}
                  >
                    {t("save")}
                  </Button>
                )}
              </span>
              <ActiveToggle on={b.active} label={tc("active")} onChange={(v) => void save(b, { active: v })} />
            </li>
          );
        })}
      </ul>
    </div>
  );
}

type AddOnRules = AddOnRow & {
  step?: string;
  needs?: string[];
  featured?: boolean;
  badge_ar?: string | null;
  badge_en?: string | null;
};

/** The add-ons step's rules: what each add-on needs (turned on with it), the open list, and its badge. */
export function AddOnRules({ rows, onRow }: { rows: AddOnRules[]; onRow: (row: AddOnRow) => void }) {
  const t = useTranslations("orderPath.admin");
  const locale = useLocale();
  const [error, setError] = useState<string | null>(null);
  const name = (a: AddOnRow) => (locale === "ar" ? a.name_ar : a.name_en);

  async function save(a: AddOnRules, patch: Record<string, unknown>) {
    const r = await catalogAdmin.addon(a.slug, patch);
    if (r.ok) onRow(r.data);
    setError(r.ok ? null : errorText(r.error, locale, "—"));
  }

  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-h3 text-night-900">{t("rulesTitle")}</h3>
      <p className="max-w-3xl text-small text-ink-muted">{t("rulesIntro")}</p>
      {error && <Alert>{error}</Alert>}
      <div className="overflow-x-auto rounded-lg border border-line bg-paper-raised">
        <table className="w-full min-w-[720px] text-small">
          <thead className="bg-paper-sunk text-caption text-ink-muted">
            <tr>
              <th className="px-3 py-2 text-start">{t("addon")}</th>
              <th className="px-3 py-2 text-start">{t("step")}</th>
              <th className="px-3 py-2 text-start">{t("featured")}</th>
              <th className="px-3 py-2 text-start">{t("badge")}</th>
              <th className="px-3 py-2 text-start">{t("needs")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.slug} className="border-t border-line align-top">
                <td className="px-3 py-2 font-semibold">{name(a)}</td>
                <td className="px-3 py-2 text-ink-muted">{t(`steps.${a.step ?? "format"}`)}</td>
                <td className="px-3 py-2">
                  <input
                    type="checkbox"
                    aria-label={t("featured")}
                    className="size-5 accent-night-900"
                    checked={!!a.featured}
                    onChange={(e) => void save(a, { featured: e.target.checked })}
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    aria-label={t("badge")}
                    defaultValue={(locale === "ar" ? a.badge_ar : a.badge_en) ?? ""}
                    maxLength={40}
                    onBlur={(e) => void save(a, { [locale === "ar" ? "badge_ar" : "badge_en"]: e.target.value })}
                    className={`${input} w-36`}
                  />
                </td>
                <td className="px-3 py-2">
                  <select
                    multiple
                    aria-label={t("needs")}
                    value={a.needs ?? []}
                    onChange={(e) => void save(a, { needs: [...e.target.selectedOptions].map((o) => o.value) })}
                    className={`${input} h-20 w-48`}
                  >
                    {rows
                      .filter((x) => x.slug !== a.slug)
                      .map((x) => (
                        <option key={x.slug} value={x.slug}>
                          {name(x)}
                        </option>
                      ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
