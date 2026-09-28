"use client";

import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button, buttonClasses } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { Link, useRouter } from "@/i18n/navigation";
import { api, errorText, safeNext, type User } from "@/lib/api";

const GOOGLE_ENABLED = process.env.NEXT_PUBLIC_GOOGLE_LOGIN === "1";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const t = useTranslations("auth");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNext(params.get("next"), "/account");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(params.get("error") === "google_failed" ? t("googleFailed") : null);
  const [badFields, setBadFields] = useState<string[]>([]);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const body: Record<string, string> = {
      email: String(form.get("email") ?? ""),
      password: String(form.get("password") ?? ""),
    };
    if (mode === "register") {
      body.full_name = String(form.get("full_name") ?? "");
      body.locale = locale;
    }
    setBusy(true);
    setError(null);
    const res = await api<User>(`/api/auth/${mode}`, { json: body });
    if (res.ok) {
      router.replace(next);
      router.refresh();
      return;
    }
    setBusy(false);
    setError(errorText(res.error, locale, res.status === 0 ? te("network") : te("unknown")));
    const fields = res.error?.details?.fields ?? [];
    const code = res.error?.code;
    setBadFields(code === "weak_password" ? ["password"] : code === "email_taken" ? ["email"] : fields);
  }

  const bad = (f: string) => badFields.includes(f);
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      {error && <Alert>{error}</Alert>}
      {mode === "register" && (
        <TextField
          name="full_name"
          label={t("fullName")}
          hint={t("fullNameHint")}
          autoComplete="name"
          required
          maxLength={120}
          invalid={bad("full_name")}
        />
      )}
      <TextField
        name="email"
        type="email"
        label={t("email")}
        autoComplete="email"
        inputMode="email"
        required
        ltr
        invalid={bad("email")}
      />
      <TextField
        name="password"
        type="password"
        label={t("password")}
        hint={mode === "register" ? t("passwordHint") : undefined}
        autoComplete={mode === "register" ? "new-password" : "current-password"}
        required
        minLength={mode === "register" ? 8 : undefined}
        maxLength={128}
        revealLabels={{ show: t("showPassword"), hide: t("hidePassword") }}
        invalid={bad("password")}
      />
      <Button
        type="submit"
        variant={mode === "register" ? "primary" : "solid"}
        size="lg"
        loading={busy}
        loadingLabel={t("working")}
        className="mt-2 w-full"
      >
        {mode === "register" ? t("submitRegister") : t("submitLogin")}
      </Button>

      {GOOGLE_ENABLED && (
        <>
          <div className="flex items-center gap-3 text-caption text-ink-faint">
            <span className="h-px flex-1 bg-line" />
            {t("or")}
            <span className="h-px flex-1 bg-line" />
          </div>
          <a
            href={`/api/auth/google/start?next=${encodeURIComponent(`/${locale}${next}`)}`}
            className={buttonClasses("secondary", "md", "w-full")}
          >
            {t("google")}
          </a>
        </>
      )}

      <p className="text-center text-small text-ink-muted">
        {mode === "login" ? t("noAccount") : t("haveAccount")}{" "}
        <Link
          href={mode === "login" ? "/register" : "/login"}
          className="font-semibold text-night-800 underline underline-offset-4"
        >
          {mode === "login" ? t("submitRegister") : t("submitLogin")}
        </Link>
      </p>
    </form>
  );
}
