"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { useRouter } from "@/i18n/navigation";
import { api, errorText } from "@/lib/api";

type Kind = "text" | "number" | "money" | "decimal" | "boolean" | "choice" | "secret" | "phone" | "email" | "url";
type Setting = {
  key: string;
  kind: Kind;
  label: string;
  help: string;
  value: string | number | boolean;
  configured: boolean;
  is_example: boolean;
  public: boolean;
  choices: string[];
  min: number | null;
  max: number | null;
};
type Group = { id: string; label: string; settings: Setting[] };
type View = { groups: Group[] };
type Draft = Record<string, string | number | boolean | null>;

const field =
  "min-h-[48px] w-full rounded-sm border border-line bg-paper-raised px-3.5 text-body text-ink outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-100";

export function AdminSettings() {
  const t = useTranslations("admin");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [view, setView] = useState<View | null>(null);
  const [state, setState] = useState<"loading" | "forbidden" | "ready">("loading");
  const [tab, setTab] = useState<string>("pricing");
  const [draft, setDraft] = useState<Draft>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string; field?: string } | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const res = await api<View>(`/api/admin/settings?lang=${locale}`);
      if (!alive) return;
      if (res.ok) {
        setView(res.data);
        setState("ready");
      } else if (res.status === 401) router.replace(`/login?next=${encodeURIComponent("/admin/settings")}`);
      else if (res.status === 403) setState("forbidden");
      else setMessage({ tone: "error", text: errorText(res.error, locale, te("network")) });
    })();
    return () => {
      alive = false;
    };
  }, [locale, router, te]);

  if (state === "forbidden")
    return (
      <div className="mx-auto mt-10 flex max-w-md flex-col gap-2 text-center">
        <h1 className="text-h2 text-night-900">{t("forbiddenTitle")}</h1>
        <p className="text-ink-muted">{t("forbiddenBody")}</p>
      </div>
    );
  if (!view)
    return (
      <div className="animate-pulse space-y-4" aria-busy="true">
        <div className="h-10 w-1/3 rounded-sm bg-paper-sunk" />
        <div className="h-64 rounded-xl bg-paper-sunk" />
        {message && <Alert>{message.text}</Alert>}
      </div>
    );

  const group = view.groups.find((g) => g.id === tab) ?? view.groups[0]!;
  const dirtyKeys = Object.keys(draft).filter((k) => group.settings.some((s) => s.key === k));

  async function save(values: Draft) {
    setSaving(true);
    setMessage(null);
    const res = await api<View>(`/api/admin/settings?lang=${locale}`, { method: "PUT", json: { values } });
    setSaving(false);
    if (res.ok) {
      setView(res.data);
      setDraft((d) => Object.fromEntries(Object.entries(d).filter(([k]) => !(k in values))));
      setMessage({ tone: "success", text: t("saved") });
      return;
    }
    const fieldKey = res.error?.details?.fields?.[0];
    setMessage({ tone: "error", text: errorText(res.error, locale, te("unknown")), field: fieldKey });
  }

  const set = (key: string, value: string | number | boolean | null) => setDraft((d) => ({ ...d, [key]: value }));

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-h2 text-night-900 md:text-h1">{t("title")}</h1>
        <p className="text-ink-muted">{t("lead")}</p>
      </header>

      <div role="tablist" className="flex flex-wrap gap-2">
        {view.groups.map((g) => (
          <button
            key={g.id}
            role="tab"
            type="button"
            aria-selected={g.id === group.id}
            onClick={() => {
              setTab(g.id);
              setMessage(null);
            }}
            className={`min-h-11 rounded-full border-[1.5px] px-4 text-[15px] ${g.id === group.id ? "border-night-900 bg-night-900 font-semibold text-paper" : "border-line bg-paper-raised hover:border-night-500"}`}
          >
            {g.label}
          </button>
        ))}
      </div>

      {message && <Alert tone={message.tone}>{message.text}</Alert>}

      <section className="flex flex-col divide-y divide-line rounded-xl border border-line bg-paper-raised">
        {group.settings.map((s) => {
          const current = s.key in draft ? draft[s.key] : s.value;
          const invalid = message?.field === s.key;
          const id = `setting-${s.key}`;
          return (
            <div key={s.key} className="grid gap-2 p-5 md:grid-cols-[1fr_1.2fr] md:items-start md:gap-6">
              <div className="flex flex-col gap-1">
                <label htmlFor={id} className="font-semibold text-ink">
                  {s.label}
                </label>
                <div className="flex flex-wrap gap-1.5 text-xs">
                  {s.is_example && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 font-bold text-amber-700">
                      {t("example")}
                    </span>
                  )}
                  {s.public && (
                    <span className="rounded-full bg-night-100 px-2 py-0.5 text-night-900">{t("publicHint")}</span>
                  )}
                  {s.kind === "secret" && (
                    <span
                      className={`rounded-full px-2 py-0.5 font-bold ${s.configured ? "bg-success-bg text-success" : "bg-paper-sunk text-ink-muted"}`}
                    >
                      {s.configured ? t("configured") : t("notSet")}
                    </span>
                  )}
                </div>
                {s.help && <p className="text-small text-ink-muted">{s.help}</p>}
              </div>
              <div className="flex flex-col gap-2">
                {s.kind === "boolean" ? (
                  <button
                    id={id}
                    type="button"
                    role="switch"
                    aria-checked={Boolean(current)}
                    onClick={() => set(s.key, !current)}
                    className={`flex h-9 w-16 items-center rounded-full p-1 transition ${current ? "bg-success" : "bg-line"}`}
                  >
                    <span
                      className={`size-7 rounded-full bg-white shadow-1 transition ${current ? "translate-x-0 ltr:translate-x-7 rtl:-translate-x-7" : ""}`}
                    />
                    <span className="sr-only">{current ? t("on") : t("off")}</span>
                  </button>
                ) : s.kind === "choice" ? (
                  <select
                    id={id}
                    value={String(current)}
                    onChange={(e) => set(s.key, e.target.value)}
                    className={field}
                    aria-invalid={invalid || undefined}
                  >
                    {s.choices.map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                ) : s.kind === "secret" ? (
                  <>
                    {s.configured && (
                      <span className="font-mono text-small text-ink-muted" dir="ltr">
                        {t("secretSaved", { mask: String(s.value) })}
                      </span>
                    )}
                    <input
                      id={id}
                      type="password"
                      autoComplete="off"
                      dir="ltr"
                      placeholder={t("secretPlaceholder")}
                      value={typeof draft[s.key] === "string" ? String(draft[s.key]) : ""}
                      onChange={(e) => set(s.key, e.target.value)}
                      className={`${field} rtl:text-right`}
                      aria-invalid={invalid || undefined}
                    />
                    {s.configured && (
                      <button
                        type="button"
                        className="self-start text-small font-semibold text-danger underline underline-offset-4"
                        onClick={() => {
                          if (window.confirm(t("clearConfirm"))) void save({ [s.key]: null });
                        }}
                      >
                        {t("clearSecret")}
                      </button>
                    )}
                  </>
                ) : (
                  <input
                    id={id}
                    type={
                      s.kind === "number" ? "number" : s.kind === "email" ? "email" : s.kind === "url" ? "url" : "text"
                    }
                    inputMode={
                      s.kind === "money" || s.kind === "decimal" ? "decimal" : s.kind === "phone" ? "tel" : undefined
                    }
                    dir={["phone", "email", "url", "money", "decimal", "number"].includes(s.kind) ? "ltr" : undefined}
                    min={s.min ?? undefined}
                    max={s.max ?? undefined}
                    value={String(current ?? "")}
                    onChange={(e) =>
                      set(
                        s.key,
                        s.kind === "number" ? (e.target.value === "" ? "" : Number(e.target.value)) : e.target.value,
                      )
                    }
                    className={`${field} ${["phone", "email", "url", "money", "decimal", "number"].includes(s.kind) ? "rtl:text-right" : ""} ${invalid ? "border-danger" : ""}`}
                    aria-invalid={invalid || undefined}
                  />
                )}
                {s.configured && s.kind !== "secret" && (
                  <button
                    type="button"
                    className="self-start text-small text-ink-muted underline underline-offset-4"
                    onClick={() => void save({ [s.key]: null })}
                  >
                    {t("reset")}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </section>

      <div className="sticky bottom-4 flex items-center justify-end gap-3">
        {dirtyKeys.length > 0 && (
          <span className="rounded-full bg-amber-100 px-3 py-1 text-small font-semibold text-amber-700">
            {t("unsaved")}
          </span>
        )}
        <Button
          variant="primary"
          disabled={dirtyKeys.length === 0}
          loading={saving}
          loadingLabel={t("saving")}
          onClick={() =>
            void save(
              Object.fromEntries(
                dirtyKeys.map((k) => [
                  k,
                  draft[k] === "" && group.settings.find((s) => s.key === k)?.kind === "secret"
                    ? null
                    : (draft[k] ?? null),
                ]),
              ),
            )
          }
        >
          {t("save")}
        </Button>
      </div>
    </div>
  );
}
