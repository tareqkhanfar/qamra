"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { Link, useRouter } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { portalApi, type ClassSummary } from "@/lib/portal";
import { usePortal } from "./PortalShell";
import { StageBar } from "./parts";

/** The teacher's status board across classes (design PortalDashboard): totals, classes, what to do next. */
export function Dashboard() {
  const t = useTranslations("portal");
  const { me } = usePortal();
  const k = me.kpis;
  const kpis = [
    { key: "children", value: k.children, of: t("dash.inClasses", { n: me.classes.length }), pct: 100, color: "bg-night-900" },
    { key: "consent", value: k.consent, of: t("dash.of", { n: k.children }), pct: k.children ? (k.consent / k.children) * 100 : 0, color: "bg-night-500" },
    { key: "approved", value: k.approved, of: t("dash.of", { n: k.children }), pct: k.children ? (k.approved / k.children) * 100 : 0, color: "bg-success" },
    { key: "books_ready", value: k.books_ready, of: t("dash.of", { n: k.children }), pct: k.children ? (k.books_ready / k.children) * 100 : 0, color: "bg-amber-500" },
  ]; // prettier-ignore
  const todo = me.classes.flatMap((c) => nextSteps(c)).slice(0, 4);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-h2 text-night-900 md:text-h1">{t("dash.hello", { name: me.name })}</h1>
          <p className="text-body text-ink-muted">{t("dash.lead")}</p>
        </div>
        <a
          href="#new-class"
          className="inline-flex min-h-12 items-center gap-2 rounded-full bg-night-900 px-5 font-display font-bold text-paper"
        >
          + {t("dash.newClass")}
        </a>
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {kpis.map((x) => (
          <div key={x.key} className="flex flex-col gap-2 rounded-lg border border-line bg-paper-raised p-4">
            <span className="text-small font-semibold text-ink-muted">{t(`dash.kpi.${x.key}`)}</span>
            <div className="flex items-baseline gap-1.5">
              <strong className="font-display text-[32px] text-night-900">{x.value}</strong>
              <span className="text-small text-ink-muted">{x.of}</span>
            </div>
            <div className="flex h-1.5 rounded-full bg-paper-sunk">
              <div className={`rounded-full ${x.color}`} style={{ width: `${Math.round(x.pct)}%` }} />
            </div>
          </div>
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="flex flex-col gap-3" aria-labelledby="classes">
          <h2 id="classes" className="text-h3 text-night-900">
            {t("dash.classes")}
          </h2>
          {me.classes.length === 0 && <p className="text-body text-ink-muted">{t("dash.noClasses")}</p>}
          {me.classes.map((c) => (
            <Link
              key={c.id}
              href={`/portal/classes/${c.id}`}
              className="grid gap-3 rounded-lg border border-line bg-paper-raised p-4 md:grid-cols-[1.2fr_2fr_auto] md:items-center"
            >
              <div className="flex flex-col">
                <strong className="text-body-l">{c.name}</strong>
                <span className="text-caption text-ink-muted">
                  {t("dash.classMeta", { n: c.children, teacher: c.teacher_name ?? "—" })}
                </span>
              </div>
              <StageBar stages={c.stages} />
              <span className="justify-self-start rounded-full bg-paper-sunk px-3 py-1 text-caption font-bold">
                {t(`bookStatus.${c.book_status ?? "none"}`)}
              </span>
            </Link>
          ))}
          <NewClass />
        </section>
        <section className="flex flex-col gap-3 self-start rounded-xl bg-night-900 p-5 text-paper">
          <h2 className="text-h3">{t("dash.todo")}</h2>
          {todo.length === 0 && <p className="text-small text-ink-dark-muted">{t("dash.allDone")}</p>}
          {todo.map((s) => (
            <Link
              key={s.href + s.key}
              href={s.href}
              className="flex min-h-14 items-center justify-between gap-2 rounded-md bg-night-800 px-4"
            >
              <span className="text-small">{t(`dash.next.${s.key}`, { n: s.n, name: s.name })}</span>
              <span className="text-amber-300" aria-hidden="true">
                ←
              </span>
            </Link>
          ))}
        </section>
      </div>
    </div>
  );
}

function nextSteps(c: ClassSummary): { key: string; n: number; name: string; href: string }[] {
  const base = `/portal/classes/${c.id}`;
  const out = [];
  if (c.children === 0) out.push({ key: "import", n: 0, name: c.name, href: `${base}/import` });
  if (c.stages.not_invited) out.push({ key: "invite", n: c.stages.not_invited, name: c.name, href: base });
  if (!c.book_status) out.push({ key: "book", n: 0, name: c.name, href: `${base}/book` });
  if (c.book_status === "review") out.push({ key: "review", n: 0, name: c.name, href: `${base}/review` });
  if (c.book_status === "approved") out.push({ key: "order", n: 0, name: c.name, href: `${base}/order` });
  return out;
}

function NewClass() {
  const t = useTranslations("portal");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [name, setName] = useState("");
  const [teacher, setTeacher] = useState("");
  const [year, setYear] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const r = await portalApi.createClass({ name, teacher_name: teacher || undefined, school_year: year || undefined });
    setBusy(false);
    if (r.ok) router.push(`/portal/classes/${r.data.id}/import`);
    else setError(errorText(r.error, locale, te("unknown")));
  }

  return (
    <form
      id="new-class"
      onSubmit={submit}
      className="flex flex-col gap-3 rounded-lg border border-dashed border-line p-4"
    >
      <strong className="text-body">{t("dash.newClass")}</strong>
      <div className="grid gap-3 md:grid-cols-3">
        <TextField
          label={t("dash.className")}
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={120}
        />
        <TextField
          label={t("dash.teacher")}
          value={teacher}
          onChange={(e) => setTeacher(e.target.value)}
          maxLength={120}
        />
        <TextField
          label={t("dash.year")}
          value={year}
          onChange={(e) => setYear(e.target.value)}
          placeholder="2026-2027"
          maxLength={16}
          ltr
        />
      </div>
      {error && <Alert>{error}</Alert>}
      <Button type="submit" loading={busy} className="self-start">
        {t("dash.create")}
      </Button>
    </form>
  );
}
