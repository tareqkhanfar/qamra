"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { api, errorText } from "@/lib/api";

type Step = "intro" | "scan" | "codes";

/** Two-step verification enrollment: password → QR/secret → first code → recovery codes (shown once). */
export function MfaSetup({ hasPassword, onDone }: { hasPassword: boolean; onDone: () => void }) {
  const t = useTranslations("mfa");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [step, setStep] = useState<Step>("intro");
  const [secret, setSecret] = useState("");
  const [codes, setCodes] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [qrVersion, setQrVersion] = useState(0);

  async function start(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const password = String(new FormData(e.currentTarget).get("password") ?? "");
    setBusy(true);
    setError(null);
    const res = await api<{ secret: string; uri: string }>("/api/auth/mfa/setup", {
      json: { password: password || null },
    });
    setBusy(false);
    if (!res.ok) return setError(errorText(res.error, locale, te("unknown")));
    setSecret(res.data.secret);
    setQrVersion((v) => v + 1);
    setStep("scan");
  }

  async function enable(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const code = String(new FormData(e.currentTarget).get("code") ?? "").trim();
    setBusy(true);
    setError(null);
    const res = await api<{ recovery_codes: string[] }>("/api/auth/mfa/enable", { json: { code } });
    setBusy(false);
    if (!res.ok) return setError(errorText(res.error, locale, te("unknown")));
    setCodes(res.data.recovery_codes);
    setStep("codes");
  }

  function download() {
    const blob = new Blob([codes.join("\n") + "\n"], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "qamra-recovery-codes.txt";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <section className="mx-auto flex max-w-lg flex-col gap-5 rounded-xl border border-line bg-paper-raised p-6 md:p-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-h2 text-night-900">{step === "codes" ? t("recoveryTitle") : t("setupTitle")}</h1>
        <p className="text-ink-muted">{step === "codes" ? t("recoveryLead") : t("setupLead")}</p>
      </div>
      {error && <Alert>{error}</Alert>}

      {step === "intro" && (
        <form onSubmit={start} className="flex flex-col gap-4" noValidate>
          {hasPassword && (
            <TextField name="password" type="password" label={t("password")} autoComplete="current-password" required />
          )}
          <Button type="submit" variant="solid" loading={busy} loadingLabel={t("verifying")}>
            {t("start")}
          </Button>
        </form>
      )}

      {step === "scan" && (
        <form onSubmit={enable} className="flex flex-col gap-4" noValidate>
          <p className="text-small text-ink">{t("scan")}</p>
          {/* eslint-disable-next-line @next/next/no-img-element -- same-origin, no-store QR from the API */}
          <img
            src={`/api/auth/mfa/qr.png?v=${qrVersion}`}
            alt=""
            width={220}
            height={220}
            className="self-center rounded-md border border-line bg-white p-2"
          />
          <code
            dir="ltr"
            className="self-center rounded-sm bg-paper-sunk px-3 py-2 font-mono text-small tracking-wider break-all"
          >
            {secret.replace(/(.{4})/g, "$1 ").trim()}
          </code>
          <TextField
            name="code"
            label={t("enterCode")}
            autoComplete="one-time-code"
            inputMode="numeric"
            required
            maxLength={8}
            ltr
          />
          <Button type="submit" variant="primary" loading={busy} loadingLabel={t("verifying")}>
            {t("enable")}
          </Button>
        </form>
      )}

      {step === "codes" && (
        <div className="flex flex-col gap-4">
          <ol dir="ltr" className="grid grid-cols-2 gap-2 rounded-md bg-paper-sunk p-4 font-mono text-small">
            {codes.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ol>
          <div className="flex flex-wrap gap-3">
            <Button type="button" variant="secondary" size="sm" onClick={download}>
              {t("download")}
            </Button>
            <Button type="button" variant="solid" size="sm" onClick={onDone}>
              {t("done")}
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
