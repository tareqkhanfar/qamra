"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { api, errorText } from "@/lib/api";
import { when, type AuditPage, type StaffList } from "@/lib/studio";
import { Select, inputClass } from "./parts";

type Filters = { actor: string; action: string; entity_type: string; entity_id: string; since: string; until: string };
const EMPTY: Filters = { actor: "", action: "", entity_type: "", entity_id: "", since: "", until: "" };

/** A local calendar day → the API's UTC instant (the day's start; `next` gives the following day's start). */
function dayStart(day: string, next = false): string {
  const d = new Date(`${day}T00:00`);
  if (next) d.setDate(d.getDate() + 1);
  return d.toISOString();
}

/**
 * The audit log (Addendum 4 §3.6: who, what, when): filter by actor, action, entity and date, newest first,
 * 50 per page. It shows what the log holds; staff actors are named from the staff list, others by a short id.
 */
export function AuditLog() {
  const t = useTranslations("studio.audit");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [facets, setFacets] = useState<{ actions: string[]; entity_types: string[] }>({
    actions: [],
    entity_types: [],
  });
  const [staff, setStaff] = useState<StaffList["staff"]>([]);
  const [draft, setDraft] = useState<Filters>(EMPTY);
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AuditPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const names = useMemo(() => new Map(staff.map((s) => [s.id, s.full_name])), [staff]);

  useEffect(() => {
    void (async () => {
      const [f, s] = await Promise.all([
        api<{ actions: string[]; entity_types: string[] }>("/api/admin/audit/facets"),
        api<StaffList>("/api/admin/staff"),
      ]);
      if (f.ok) setFacets(f.data);
      if (s.ok) setStaff(s.data.staff);
    })();
  }, []);

  const load = useCallback(async () => {
    const q = new URLSearchParams({ page: String(page), per_page: "50" });
    for (const key of ["actor", "action", "entity_type", "entity_id"] as const)
      if (filters[key]) q.set(key, filters[key].trim());
    if (filters.since) q.set("since", dayStart(filters.since));
    if (filters.until) q.set("until", dayStart(filters.until, true));
    const r = await api<AuditPage>(`/api/admin/audit?${q}`);
    if (!r.ok) return setError(errorText(r.error, locale, te("unknown")));
    setError(null);
    setData(r.data);
  }, [filters, page, locale, te]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  const set = (key: keyof Filters) => (value: string) => setDraft((d) => ({ ...d, [key]: value }));
  const actor = (id: string | null) => (id ? (names.get(id) ?? `#${id.slice(0, 8)}`) : t("system"));
  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-1">
        <h1 className="text-h2 text-night-900">{t("title")}</h1>
        <p className="text-ink-muted">{t("lead")}</p>
      </header>
      <form
        className="grid grid-cols-2 gap-3 rounded-xl border border-line bg-paper-raised p-4 lg:grid-cols-4"
        onSubmit={(e) => {
          e.preventDefault();
          setPage(1);
          setFilters(draft);
        }}
      >
        <Select label={t("actor")} value={draft.actor} onChange={set("actor")}>
          <option value="">{t("anyone")}</option>
          {staff.map((s) => (
            <option key={s.id} value={s.id}>
              {s.full_name}
            </option>
          ))}
        </Select>
        <label className="flex flex-col gap-1 text-small font-semibold">
          {t("action")}
          <input
            list="audit-actions"
            dir="ltr"
            value={draft.action}
            onChange={(e) => set("action")(e.target.value)}
            className={inputClass}
            placeholder="theme."
          />
          <datalist id="audit-actions">
            {facets.actions.map((a) => (
              <option key={a} value={a} />
            ))}
          </datalist>
        </label>
        <Select label={t("entityType")} value={draft.entity_type} onChange={set("entity_type")}>
          <option value="">{t("any")}</option>
          {facets.entity_types.map((e) => (
            <option key={e} value={e}>
              {e}
            </option>
          ))}
        </Select>
        <label className="flex flex-col gap-1 text-small font-semibold">
          {t("entityId")}
          <input
            dir="ltr"
            value={draft.entity_id}
            onChange={(e) => set("entity_id")(e.target.value)}
            className={inputClass}
          />
        </label>
        <label className="flex flex-col gap-1 text-small font-semibold">
          {t("since")}
          <input
            type="date"
            value={draft.since}
            onChange={(e) => set("since")(e.target.value)}
            className={inputClass}
          />
        </label>
        <label className="flex flex-col gap-1 text-small font-semibold">
          {t("until")}
          <input
            type="date"
            value={draft.until}
            onChange={(e) => set("until")(e.target.value)}
            className={inputClass}
          />
        </label>
        <div className="col-span-2 flex items-end gap-2">
          <Button size="sm" type="submit">
            {t("apply")}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            type="button"
            onClick={() => {
              setDraft(EMPTY);
              setFilters(EMPTY);
              setPage(1);
            }}
          >
            {t("clear")}
          </Button>
        </div>
      </form>
      {error && <Alert>{error}</Alert>}
      {data && (
        <>
          <p className="text-small text-ink-muted">
            {t("count", { total: data.total, page: data.page, pages: data.pages })}
          </p>
          <ol className="flex flex-col divide-y divide-line overflow-hidden rounded-xl border border-line bg-paper-raised">
            {data.items.length === 0 && <li className="p-4 text-ink-muted">{t("empty")}</li>}
            {data.items.map((item) => (
              <li
                key={item.id}
                className="grid gap-1 p-3 text-small md:grid-cols-[10rem_8rem_minmax(0,17rem)_minmax(0,1fr)] md:gap-3"
              >
                <time dateTime={item.at} className="text-ink-muted">
                  {when(item.at, locale)}
                </time>
                <span className="font-semibold text-night-900">{actor(item.actor)}</span>
                <span dir="ltr" className="font-mono text-caption break-all text-night-700 md:text-small">
                  {item.action}
                  <span className="block text-ink-muted">
                    {item.entity_type}
                    {item.entity_id ? ` · ${item.entity_id.slice(0, 13)}` : ""}
                  </span>
                </span>
                <code dir="ltr" className="font-mono text-caption break-all text-ink-muted">
                  {Object.keys(item.data).length ? JSON.stringify(item.data) : "—"}
                </code>
              </li>
            ))}
          </ol>
          <nav className="flex items-center justify-between gap-2" aria-label={t("pagination")}>
            <Button size="sm" variant="secondary" disabled={data.page <= 1} onClick={() => setPage((p) => p - 1)}>
              {t("newer")}
            </Button>
            <span className="text-small text-ink-muted">{t("pageOf", { page: data.page, pages: data.pages })}</span>
            <Button
              size="sm"
              variant="secondary"
              disabled={data.page >= data.pages}
              onClick={() => setPage((p) => p + 1)}
            >
              {t("older")}
            </Button>
          </nav>
        </>
      )}
    </div>
  );
}
