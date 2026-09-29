"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Link, useRouter } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { portalApi, portalFiles, type Preview } from "@/lib/portal";
import { usePortal } from "./PortalShell";
import { Chip } from "./parts";

/** The school's children list (design PortalImport): upload the CSV, check every row, then import. */
export function ImportView({ classId }: { classId: string }) {
  const t = useTranslations("portal.import");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const { reload } = usePortal();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<string | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [onlyProblems, setOnlyProblems] = useState(false);
  const [busy, setBusy] = useState<"check" | "import" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const msg = (m: { ar: string; en: string }) => (locale === "ar" ? m.ar : m.en);

  async function choose(picked: File | undefined) {
    if (!picked) return;
    setFile(picked.name);
    setBusy("check");
    setError(null);
    const r = await portalApi.preview(classId, picked);
    setBusy(null);
    if (r.ok) setPreview(r.data);
    else {
      setPreview(null);
      setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
    }
  }

  async function submit() {
    if (!preview) return;
    setBusy("import");
    setError(null);
    const r = await portalApi.importRows(
      classId,
      preview.rows.filter((row) => row.ok),
    );
    setBusy(null);
    if (r.ok) {
      await reload();
      router.push(`/portal/classes/${classId}`);
    } else setError(errorText(r.error, locale, te("unknown")));
  }

  const rows = preview?.rows.filter((r) => !onlyProblems || !r.ok || r.warnings.length) ?? [];
  const importable = preview?.rows.filter((r) => r.ok).length ?? 0;
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-h2 text-night-900">{t("title")}</h1>
        <a
          href={portalFiles.template(classId)}
          className="min-h-11 content-center text-small font-semibold text-night-900 underline underline-offset-4"
        >
          {t("template")}
        </a>
      </div>
      <p className="text-body text-ink-muted">{t("lead")}</p>
      <input
        ref={input}
        type="file"
        accept=".csv,text/csv"
        className="sr-only"
        aria-label={t("pick")}
        onChange={(e) => {
          void choose(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-dashed border-line bg-paper-raised p-4">
        <Button
          variant={preview ? "secondary" : "solid"}
          onClick={() => input.current?.click()}
          loading={busy === "check"}
        >
          {preview ? t("another") : t("pick")}
        </Button>
        {file && (
          <span className="text-small text-ink-muted" dir="ltr">
            {file}
          </span>
        )}
        <span className="text-caption text-ink-muted">{t("xlsxNote")}</span>
      </div>
      {error && <Alert>{error}</Alert>}
      {preview && (
        <>
          <div className="grid grid-cols-3 gap-3">
            {(["ok", "warnings", "errors"] as const).map((k) => (
              <div key={k} className="flex flex-col rounded-lg border border-line bg-paper-raised p-3">
                <strong
                  className={`font-display text-h3 ${k === "errors" ? "text-danger" : k === "warnings" ? "text-amber-700" : "text-success"}`}
                >
                  {preview[k]}
                </strong>
                <span className="text-caption text-ink-muted">{t(`count.${k}`)}</span>
              </div>
            ))}
          </div>
          <label className="flex min-h-11 items-center gap-2 text-small">
            <input
              type="checkbox"
              checked={onlyProblems}
              onChange={(e) => setOnlyProblems(e.target.checked)}
              className="size-5 accent-night-900"
            />
            {t("onlyProblems")}
          </label>
          <div className="overflow-x-auto rounded-lg border border-line bg-paper-raised">
            <table className="w-full min-w-[640px] text-start text-small">
              <thead className="bg-paper-sunk text-ink-muted">
                <tr>
                  {(["row", "name", "gender", "year", "parent", "contact", "check"] as const).map((h) => (
                    <th key={h} className="px-3 py-2.5 text-start font-semibold">
                      {t(`cols.${h}`)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr
                    key={r.row}
                    className={`border-t border-line ${!r.ok ? "bg-danger-bg/40" : r.warnings.length ? "bg-amber-100/40" : ""}`}
                  >
                    <td className="px-3 py-2.5 text-ink-muted">{r.row}</td>
                    <td className="px-3 py-2.5 font-semibold">{r.name || "—"}</td>
                    <td className="px-3 py-2.5">{r.gender ? t(`gender.${r.gender}`) : "—"}</td>
                    <td className="px-3 py-2.5">{r.birth_year ?? "—"}</td>
                    <td className="px-3 py-2.5">{r.parent_name ?? "—"}</td>
                    <td className="px-3 py-2.5" dir="ltr">
                      {r.phone ?? r.email ?? "—"}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-col items-start gap-1">
                        {!r.errors.length && !r.warnings.length && <Chip tone="approved">{t("fine")}</Chip>}
                        {r.errors.map((m, i) => (
                          <Chip key={`e${i}`} tone="failed">
                            {msg(m)}
                          </Chip>
                        ))}
                        {r.warnings.map((m, i) => (
                          <Chip key={`w${i}`} tone="ready">
                            {msg(m)}
                          </Chip>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Link
              href={`/portal/classes/${classId}`}
              className="min-h-11 content-center text-small font-semibold underline"
            >
              {t("cancel")}
            </Link>
            <div className="flex flex-wrap items-center gap-3">
              {preview.errors > 0 && (
                <span className="text-caption text-danger">{t("skipped", { n: preview.errors })}</span>
              )}
              <Button onClick={submit} loading={busy === "import"} disabled={!importable}>
                {t("cta", { n: importable })}
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
