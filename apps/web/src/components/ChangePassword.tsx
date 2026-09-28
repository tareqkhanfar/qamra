"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { api, errorText } from "@/lib/api";

/** Change password; the API signs out every other session. */
export function ChangePassword() {
  const t = useTranslations("password");
  const ta = useTranslations("auth");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    setBusy(true);
    setMessage(null);
    const res = await api("/api/auth/password", {
      json: { current_password: String(f.get("current") ?? ""), new_password: String(f.get("new") ?? "") },
    });
    setBusy(false);
    if (res.ok) {
      form.reset();
      setMessage({ tone: "success", text: t("done") });
    } else
      setMessage({
        tone: "error",
        text: errorText(res.error, locale, res.status === 0 ? te("network") : te("unknown")),
      });
  }

  return (
    <details className="rounded-xl border border-line bg-paper-raised p-5">
      <summary className="cursor-pointer font-semibold text-night-900">{t("title")}</summary>
      <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-4">
        {message && <Alert tone={message.tone}>{message.text}</Alert>}
        <TextField
          name="current"
          type="password"
          label={t("current")}
          autoComplete="current-password"
          required
          revealLabels={{ show: ta("showPassword"), hide: ta("hidePassword") }}
        />
        <TextField
          name="new"
          type="password"
          label={t("new")}
          hint={t("hint")}
          autoComplete="new-password"
          required
          minLength={8}
          revealLabels={{ show: ta("showPassword"), hide: ta("hidePassword") }}
        />
        <Button type="submit" variant="solid" loading={busy} loadingLabel={t("saving")} className="self-start">
          {t("save")}
        </Button>
      </form>
    </details>
  );
}
