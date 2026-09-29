"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { api, errorText } from "@/lib/api";

type Org = {
  id: string;
  name: string;
  status: string;
  country: string;
  city: string | null;
  phone: string | null;
  address: string | null;
  created_at: string;
  contacts: { name: string; email: string; phone: string | null }[];
  classes: number;
  children: number;
  price_list: string | null;
};
type ClassBookRow = {
  id: string;
  school: string;
  classroom: string;
  status: string;
  line: string;
  copies: number;
  approved: number;
  in_review: number;
  order_code: string | null;
  order_status: string | null;
  print_batch: string | null;
  cost_usd: string;
  combined: boolean;
};
type Detail = {
  book: ClassBookRow;
  min_appearances: number;
  coverage: {
    child_id: string;
    name: string;
    status: string;
    appearances: number;
    recognized: number;
    unrecognized_pages: number[];
    flags: string[];
  }[];
  files: { name: string; path: string }[];
};
const STATUSES = ["pending", "approved", "rejected", ""] as const;

/** Kindergartens in the admin: sign-up approval, and every class book with per-child coverage and its bundle. */
export function AdminOrganizations() {
  const t = useTranslations("portal.admin");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [status, setStatus] = useState<(typeof STATUSES)[number]>("pending");
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [books, setBooks] = useState<ClassBookRow[]>([]);
  const [open, setOpen] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const load = useCallback(async () => {
    const q = status ? `?status=${status}` : "";
    const [o, b] = await Promise.all([
      api<Org[]>(`/api/admin/portal/organizations${q}`),
      api<ClassBookRow[]>("/api/admin/portal/class-books"),
    ]);
    if (o.ok) setOrgs(o.data);
    else setError(errorText(o.error, locale, te("unknown")));
    if (b.ok) setBooks(b.data);
  }, [locale, status, te]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  async function decide(org: Org, to: "approve" | "reject") {
    const reason = to === "reject" ? window.prompt(t("reason")) : null;
    if (to === "reject" && reason === null) return;
    const r = await api<Org>(`/api/admin/portal/organizations/${org.id}/${to}`, { json: { reason } });
    if (r.ok) await load();
    else setError(errorText(r.error, locale, te("unknown")));
  }

  async function show(id: string) {
    const r = await api<Detail>(`/api/admin/portal/class-books/${id}`);
    if (r.ok) setOpen(r.data);
  }

  async function approveAll(id: string) {
    const r = await api<{ approved: number; not_ready: string[]; detail: Detail }>(
      `/api/admin/portal/class-books/${id}/approve`,
      { method: "POST" },
    );
    if (r.ok) {
      setOpen(r.data.detail);
      setNote(t("approvedNote", { n: r.data.approved, waiting: r.data.not_ready.join("، ") || "—" }));
      await load();
    } else setError(errorText(r.error, locale, te("unknown")));
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-h2 text-night-900 md:text-h1">{t("title")}</h1>
      {error && <Alert>{error}</Alert>}
      <section className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-h3 text-night-900">{t("organizations")}</h2>
          {STATUSES.map((s) => (
            <button
              key={s || "all"}
              type="button"
              aria-pressed={status === s}
              onClick={() => setStatus(s)}
              className={`min-h-10 rounded-full px-3.5 text-small ${status === s ? "bg-night-900 text-paper" : "border border-line"}`}
            >
              {t(`orgStatus.${s || "all"}`)}
            </button>
          ))}
        </div>
        {orgs.length === 0 && <p className="text-ink-muted">{t("noOrgs")}</p>}
        {orgs.map((o) => (
          <article
            key={o.id}
            className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-line bg-paper-raised p-4"
          >
            <div className="flex flex-col gap-1 text-small">
              <strong className="text-body-l">{o.name}</strong>
              <span className="text-ink-muted">
                {[o.city, o.address].filter(Boolean).join("، ")} · {o.phone}
              </span>
              {o.contacts.map((c) => (
                <span key={c.email} dir="ltr" className="text-ink-muted">
                  {c.name} · {c.email}
                </span>
              ))}
              <span>{t("orgStats", { classes: o.classes, children: o.children, list: o.price_list ?? "—" })}</span>
            </div>
            <div className="flex gap-2">
              <span className="rounded-full bg-paper-sunk px-3 py-1 text-caption font-bold">
                {t(`orgStatus.${o.status}`)}
              </span>
              {o.status !== "approved" && (
                <Button size="sm" onClick={() => void decide(o, "approve")}>
                  {t("approve")}
                </Button>
              )}
              {o.status === "pending" && (
                <Button size="sm" variant="secondary" onClick={() => void decide(o, "reject")}>
                  {t("reject")}
                </Button>
              )}
            </div>
          </article>
        ))}
      </section>
      <section className="flex flex-col gap-3">
        <h2 className="text-h3 text-night-900">{t("classBooks")}</h2>
        {books.length === 0 && <p className="text-ink-muted">{t("noBooks")}</p>}
        <div className="overflow-x-auto rounded-lg border border-line bg-paper-raised">
          <table className="w-full min-w-[720px] text-small">
            <thead className="bg-paper-sunk text-start text-ink-muted">
              <tr>
                {(["school", "status", "copies", "order", "cost", ""] as const).map((h) => (
                  <th key={h} className="px-3 py-2 text-start">
                    {h ? t(`cols.${h}`) : ""}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {books.map((b) => (
                <tr key={b.id} className="border-t border-line">
                  <td className="px-3 py-2">
                    <strong>{b.school}</strong> · {b.classroom}{" "}
                    <span className="text-ink-muted">({t(`line.${b.line}`)})</span>
                  </td>
                  <td className="px-3 py-2">{t(`bookStatus.${b.status}`)}</td>
                  <td className="px-3 py-2">
                    {t("copiesCell", { n: b.copies, approved: b.approved, review: b.in_review })}
                  </td>
                  <td className="px-3 py-2" dir="ltr">
                    {b.order_code ? `${b.order_code} · ${b.order_status}` : "—"}
                  </td>
                  <td className="px-3 py-2" dir="ltr">
                    ${Number(b.cost_usd).toFixed(2)}
                  </td>
                  <td className="px-3 py-2">
                    <Button size="sm" variant="ghost" onClick={() => void show(b.id)}>
                      {t("open")}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {open && (
        <section className="flex flex-col gap-3 rounded-xl border border-line bg-paper-raised p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-h3 text-night-900">
              {open.book.school} · {open.book.classroom}
            </h2>
            <Button size="sm" disabled={!open.book.in_review} onClick={() => void approveAll(open.book.id)}>
              {t("approveCopies", { n: open.book.in_review })}
            </Button>
          </div>
          {note && <Alert tone="success">{note}</Alert>}
          <h3 className="text-body font-bold">{t("coverage", { n: open.min_appearances })}</h3>
          <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {open.coverage.map((c) => (
              <li
                key={c.child_id}
                className={`flex flex-col rounded-md border p-2 text-small ${c.recognized < open.min_appearances || c.flags.length ? "border-danger" : "border-line"}`}
              >
                <strong>{c.name}</strong>
                <span>
                  {t("appearances", { n: c.appearances, ok: c.recognized })}
                  {c.unrecognized_pages.length ? ` · ${t("missed", { pages: c.unrecognized_pages.join(", ") })}` : ""}
                </span>
                <span className="text-ink-muted">
                  {t(`copyStatus.${c.status}`)}
                  {c.flags.length ? ` · ${c.flags.join(", ")}` : ""}
                </span>
              </li>
            ))}
          </ul>
          <h3 className="text-body font-bold">{t("bundle")}</h3>
          <ul className="flex flex-col gap-1 text-small">
            {open.files.map((f) => (
              <li key={f.path}>
                <a href={f.path} className="font-semibold underline" dir="auto">
                  {f.name}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
