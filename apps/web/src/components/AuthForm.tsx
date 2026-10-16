"use client";

import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button, buttonClasses } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { Link, useRouter } from "@/i18n/navigation";
import { api, errorText, safeNext, type MfaChallenge, type User } from "@/lib/api";
import {
  checkFields,
  focusFirstInvalid,
  onlyFields,
  problemTexts,
  serverFieldErrors,
  type FieldErrors,
  type Rule,
  withoutField,
} from "@/lib/fieldErrors";
import { toAsciiDigits } from "@/lib/phone";

const ORDER = ["full_name", "email", "password"] as const;
const RULES: Record<"login" | "register", Partial<Record<(typeof ORDER)[number], Rule>>> = {
  login: { email: { required: true, email: true }, password: { required: true } },
  register: {
    full_name: { required: true },
    email: { required: true, email: true },
    password: { required: true, min: [8, "passwordShort"] },
  },
};

export function AuthForm({ mode, googleEnabled = false }: { mode: "login" | "register"; googleEnabled?: boolean }) {
  const t = useTranslations("auth");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNext(params.get("next"), "/account");
  // switching between sign-in and sign-up keeps where the parent was going (e.g. «أضف للسلة» → /create)
  const keepNext = params.get("next") ? `?${new URLSearchParams({ next })}` : "";
  const switchHref = `${mode === "login" ? "/register" : "/login"}${keepNext}`;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(params.get("error") === "google_failed" ? t("googleFailed") : null);
  const [errors, setErrors] = useState<FieldErrors>({}); // messages under the fields
  const [mfaStep, setMfaStep] = useState(false);
  const tm = useTranslations("mfa");

  async function onCode(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const code = toAsciiDigits(String(new FormData(e.currentTarget).get("code") ?? "")).trim(); // ١٢٣ → 123
    setBusy(true);
    setError(null);
    const res = await api<User>("/api/auth/mfa/verify", { json: { code } });
    if (res.ok) {
      router.replace(next);
      router.refresh();
      return;
    }
    setBusy(false);
    setError(errorText(res.error, locale, res.status === 0 ? te("network") : te("unknown")));
    if (res.error?.code === "token_expired") setMfaStep(false);
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const element = e.currentTarget;
    const form = new FormData(element);
    const mark = (marked: FieldErrors) => {
      setErrors(marked);
      setError(te("checkFields"));
      focusFirstInvalid(element, ORDER, marked);
    };
    const values = Object.fromEntries(ORDER.map((k) => [k, String(form.get(k) ?? "")]));
    const problems = checkFields(values, RULES[mode] as Record<string, Rule>);
    if (Object.keys(problems).length) return mark(problemTexts(problems, te));
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
    setErrors({});
    const res = await api<User | MfaChallenge>(`/api/auth/${mode}`, { json: body });
    if (res.ok && "mfa_required" in res.data) {
      setBusy(false);
      setMfaStep(true);
      return;
    }
    if (res.ok) {
      router.replace(next);
      router.refresh();
      return;
    }
    setBusy(false);
    const marked = onlyFields(serverFieldErrors(res.error, locale), ORDER);
    if (Object.keys(marked).length) mark(marked);
    else setError(errorText(res.error, locale, res.status === 0 ? te("network") : te("unknown")));
  }

  const clear = (e: FormEvent<HTMLFormElement>) => {
    const name = (e.target as HTMLInputElement).name;
    if (name) setErrors((current) => withoutField(current, name));
  };
  if (mfaStep)
    return (
      <form onSubmit={onCode} className="flex flex-col gap-4" noValidate>
        <div className="flex flex-col gap-1">
          <h2 className="text-h3 text-night-900">{tm("loginTitle")}</h2>
          <p className="text-small text-ink-muted">{tm("loginLead")}</p>
        </div>
        {error && <Alert>{error}</Alert>}
        <TextField
          name="code"
          label={tm("code")}
          hint={tm("codeHint")}
          autoComplete="one-time-code"
          inputMode="numeric"
          required
          maxLength={20}
          ltr
          autoFocus
        />
        <Button
          type="submit"
          variant="solid"
          size="lg"
          loading={busy}
          loadingLabel={tm("verifying")}
          className="w-full"
        >
          {tm("verify")}
        </Button>
      </form>
    );
  return (
    <form onSubmit={onSubmit} onInput={clear} className="flex flex-col gap-4" noValidate>
      {error && <Alert>{error}</Alert>}
      {mode === "register" && (
        <TextField
          name="full_name"
          label={t("fullName")}
          hint={t("fullNameHint")}
          autoComplete="name"
          required
          maxLength={120}
          error={errors.full_name}
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
        error={errors.email}
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
        error={errors.password}
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

      {googleEnabled && (
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

      {mode === "login" ? (
        <div className="flex flex-col gap-2 border-t border-line pt-4 text-center">
          <p className="text-small text-ink-muted">{t("noAccount")}</p>
          <Link href={switchHref} className={buttonClasses("secondary", "lg", "w-full")}>
            {t("createAccount")}
          </Link>
        </div>
      ) : (
        <p className="text-center text-small text-ink-muted">
          {t("haveAccount")}{" "}
          <Link href={switchHref} className="font-semibold text-night-800 underline underline-offset-4">
            {t("submitLogin")}
          </Link>
        </p>
      )}
    </form>
  );
}
