"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button, buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { errorText, type ApiResult } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import { portalApi, type Plan, type PlanKid } from "@/lib/portal";

type Held = { kid: PlanKid; from: number | null }; // from = page index, null = the class list

/** The page planner (design ClassPlanner): who appears on which shared page. Tap a child, then a page (phones),
 * or drag it there (desktop). Every child should reach the target number of appearances. */
export function Planner({ classId }: { classId: string }) {
  const t = useTranslations("portal.planner");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [held, setHeld] = useState<Held | null>(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState<"auto" | "save" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const r = await portalApi.plan(classId);
      if (r.ok) setPlan(r.data);
      else setError(errorText(r.error, locale, te("unknown")));
    })();
  }, [classId, locale, te]);

  const counts = useMemo(() => {
    const c = new Map<string, number>();
    plan?.pages.forEach((p) => p.children.forEach((k) => c.set(k.id, (c.get(k.id) ?? 0) + 1)));
    return c;
  }, [plan]);

  if (!plan) return error ? <Alert>{error}</Alert> : <div className="h-64 animate-pulse rounded-xl bg-paper-sunk" />;
  const target = plan.min_appearances;
  const low = plan.members.filter((m) => (counts.get(m.id) ?? 0) < target);

  function drop(to: number) {
    if (!held || !plan) return;
    const page = plan.pages.find((p) => p.index === to);
    if (!page || page.children.some((k) => k.id === held.kid.id) || page.children.length >= page.slots) {
      setHeld(null);
      return;
    }
    setPlan({
      ...plan,
      pages: plan.pages.map((p) =>
        p.index === to
          ? { ...p, children: [...p.children, held.kid] }
          : p.index === held.from
            ? { ...p, children: p.children.filter((k) => k.id !== held.kid.id) }
            : p,
      ),
    });
    setHeld(null);
    setDirty(true);
  }

  function takeOff(from: number, kid: PlanKid) {
    if (!plan) return;
    setPlan({
      ...plan,
      pages: plan.pages.map((p) =>
        p.index === from ? { ...p, children: p.children.filter((k) => k.id !== kid.id) } : p,
      ),
    });
    setHeld(null);
    setDirty(true);
  }

  async function call(label: "auto" | "save", run: () => Promise<ApiResult<Plan>>) {
    setBusy(label);
    setError(null);
    const r = await run();
    setBusy(null);
    if (r.ok) {
      setPlan(r.data);
      setDirty(false);
    } else setError(errorText(r.error, locale, te("unknown")));
  }

  const chip = (kid: PlanKid, from: number | null) => {
    const on = held?.kid.id === kid.id && held.from === from;
    return (
      <button
        key={`${from}-${kid.id}`}
        type="button"
        draggable
        onDragStart={() => setHeld({ kid, from })}
        onClick={() => setHeld(on ? null : { kid, from })}
        aria-pressed={on}
        className={`flex min-h-10 items-center gap-1.5 rounded-full px-3 text-small font-semibold ${on ? "bg-night-900 text-paper shadow-2" : "bg-night-100 text-night-900"}`}
      >
        {kid.name}
      </button>
    );
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[300px_1fr]">
      <aside
        className="flex flex-col gap-3 self-start rounded-xl border border-line bg-paper-raised p-4 xl:sticky xl:top-6"
        aria-label={t("coverage")}
      >
        <h2 className="text-h3 text-night-900">{t("coverage")}</h2>
        <p className="text-small text-ink-muted">{t("target", { n: target })}</p>
        {low.length > 0 ? (
          <Alert tone="info">{t("low", { n: low.length })}</Alert>
        ) : (
          <Alert tone="success">{t("allGood")}</Alert>
        )}
        <ul className="flex max-h-[50vh] flex-col gap-1 overflow-y-auto">
          {[...plan.members]
            .sort((a, b) => (counts.get(a.id) ?? 0) - (counts.get(b.id) ?? 0))
            .map((m) => {
              const n = counts.get(m.id) ?? 0;
              return (
                <li
                  key={m.id}
                  className={`flex items-center gap-2 rounded-sm px-2 py-1 ${n < target ? "bg-amber-100/60" : ""}`}
                >
                  {chip(m, null)}
                  <span className={`ms-auto text-caption font-bold ${n < target ? "text-amber-700" : "text-success"}`}>
                    {t("times", { n })}
                  </span>
                </li>
              );
            })}
        </ul>
      </aside>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex flex-col gap-1">
            <span className="text-small text-ink-muted">{t("crumb")}</span>
            <h1 className="text-h2 text-night-900">{t("title")}</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              size="sm"
              loading={busy === "auto"}
              onClick={() => void call("auto", () => portalApi.autoPlan(classId))}
            >
              {t("auto")}
            </Button>
            <Button
              size="sm"
              loading={busy === "save"}
              disabled={!dirty}
              onClick={() =>
                void call("save", () =>
                  portalApi.savePlan(
                    classId,
                    plan.pages.map((p) => ({ index: p.index, children: p.children.map((k) => k.id) })),
                  ),
                )
              }
            >
              {t("save")}
            </Button>
            <Link href={`/portal/classes/${classId}/book`} className={buttonClasses("ghost", "sm")}>
              {t("back")}
            </Link>
          </div>
        </div>
        {plan.line === "classic" && <Alert tone="info">{t("classic")}</Alert>}
        {plan.outdated && <Alert tone="info">{t("outdated")}</Alert>}
        {held && (
          <p className="text-small font-semibold text-night-900" role="status">
            {t("holding", nameCases(held.kid.name))}
          </p>
        )}
        {error && <Alert>{error}</Alert>}
        <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
          {plan.pages.map((p) => {
            const open = p.children.length < p.slots;
            return (
              <section
                key={p.index}
                onDragOver={(e) => open && e.preventDefault()}
                onDrop={() => drop(p.index)}
                onClick={(e) => {
                  if (e.target === e.currentTarget && held) drop(p.index);
                }}
                className={`flex flex-col gap-2 rounded-lg border bg-paper-raised p-3 ${held && open ? "border-2 border-dashed border-amber-500" : "border-line"}`}
              >
                <div className="flex items-center justify-between">
                  <strong className="text-small">{t("page", { n: p.index })}</strong>
                  <span className="text-caption text-ink-muted">
                    {t("places", { n: p.children.length, of: p.slots })}
                  </span>
                </div>
                <p className="text-caption leading-relaxed text-ink-muted">{p.text}</p>
                <div className="flex flex-wrap gap-1.5">
                  {p.children.map((k) => (
                    <span key={k.id} className="flex items-center gap-0.5">
                      {chip(k, p.index)}
                      <button
                        type="button"
                        aria-label={t("remove", nameCases(k.name))}
                        onClick={() => takeOff(p.index, k)}
                        className="size-9 text-ink-muted"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  {open && (
                    <button
                      type="button"
                      onClick={() => drop(p.index)}
                      disabled={!held}
                      className="min-h-10 rounded-full border border-dashed border-line px-3 text-caption text-ink-muted disabled:opacity-60"
                    >
                      {held ? t("putHere", nameCases(held.kid.name)) : t("dropHere")}
                    </button>
                  )}
                </div>
              </section>
            );
          })}
        </div>
      </div>
    </div>
  );
}
