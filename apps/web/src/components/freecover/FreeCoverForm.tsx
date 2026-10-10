"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Link, useRouter } from "@/i18n/navigation";
import { api, errorText, type User } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import type { ThemeCard } from "@/lib/catalog";
import { classicAvailable, classicVariant } from "@/lib/classic";
import { createApi, type Child } from "@/lib/create";
import { freeCoverApi } from "@/lib/freeCover";

const AGES = [3, 4, 5, 6, 7, 8];
const STYLE = "watercolor";

/**
 * «شوف غلاف طفلك خلال دقيقة» (Addendum 9): the name, the look, the guardian's consent and one photo, through the
 * create flow's own endpoints; then one small cover drawn from the story's ready illustrations.
 */
export function FreeCoverForm({ initialTheme }: { initialTheme: string | null }) {
  const t = useTranslations("freeCover");
  const tc = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [themes, setThemes] = useState<ThemeCard[]>([]);
  const [children, setChildren] = useState<Child[]>([]);
  const [picked, setPicked] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [gender, setGender] = useState<"m" | "f" | null>(null);
  const [age, setAge] = useState<number>(5);
  const [hijab, setHijab] = useState(false);
  const [theme, setTheme] = useState<string | null>(initialTheme);
  const [photo, setPhoto] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const me = await api<User>("/api/auth/me");
      if (!alive) return;
      if (!me.ok && me.status === 401) {
        router.replace(
          `/login?next=${encodeURIComponent(`/free-cover${initialTheme ? `?theme=${initialTheme}` : ""}`)}`,
        );
        return;
      }
      const [worlds, kids] = await Promise.all([api<ThemeCard[]>(`/api/themes?lang=${locale}`), createApi.children()]);
      if (!alive) return;
      if (worlds.ok) setThemes(worlds.data);
      if (kids.ok) setChildren(kids.data);
    })();
    return () => {
      alive = false;
    };
  }, [locale, router, initialTheme]);

  const child = children.find((c) => c.id === picked) ?? null;
  const look = classicVariant(child ?? { gender: gender ?? "f", hijab: (gender ?? "f") === "f" && hijab });
  const ready = themes.filter((th) => th.status === "available" && classicAvailable(th, STYLE, look));
  const chosen = ready.find((th) => th.slug === theme) ?? ready[0] ?? null;
  const needsPhoto = !child || (child.photos === 0 && !child.characters.some((c) => c.approved));
  const needsConsent = !child || !child.consent;
  const who = { ...nameCases(child?.name ?? (name.trim() || t("yourChild"))), gender: child?.gender ?? gender ?? "f" };

  async function submit() {
    setError(null);
    if (!child && (!name.trim() || !gender)) return setError(t("missing"));
    if (needsPhoto && !photo) return setError(t("missingPhoto"));
    if (needsConsent && !consent) return setError(tc("consent.required"));
    if (!chosen) return setError(t("noStory", { gender: child?.gender ?? gender ?? "other" }));
    setBusy(true);
    const fail = (r: { error: Parameters<typeof errorText>[0]; status: number }) => {
      setBusy(false);
      setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
    };
    let current = child;
    if (!current) {
      const r = await createApi.addChild({
        name: name.trim(),
        gender: gender!,
        age,
        interests: [],
        hijab,
        glasses: false,
      });
      if (!r.ok) return fail(r);
      current = r.data;
      setChildren((list) => [...list, r.data]);
      setPicked(r.data.id);
    }
    if (!current.consent) {
      const r = await createApi.consent(current.id, tc("consent.version"));
      if (!r.ok) return fail(r);
    }
    if (needsPhoto && photo) {
      const r = await createApi.photo(current.id, photo);
      if (!r.ok) return fail(r);
    }
    const r = await freeCoverApi.request(current.id, chosen.slug, locale);
    if (!r.ok) return fail(r);
    router.push(`/free-cover/result?id=${r.data.id}`);
  }

  const chip = (on: boolean) =>
    `min-h-11 rounded-full px-4 text-body font-semibold ${on ? "bg-night-900 text-paper-raised" : "border-[1.5px] border-line bg-paper-raised text-night-900"}`;

  return (
    <div className="mx-auto flex w-full max-w-[640px] flex-col gap-6 px-4 pt-6 pb-36">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-[28px] leading-snug text-night-900">{t("formTitle")}</h1>
        <p className="text-body text-ink-muted">{t("formBody")}</p>
      </div>

      {children.length > 0 && (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 text-body font-semibold">{t("who")}</legend>
          <div className="flex flex-wrap gap-2">
            {children.map((c) => (
              <button key={c.id} type="button" className={chip(picked === c.id)} onClick={() => setPicked(c.id)}>
                {c.name}
              </button>
            ))}
            <button type="button" className={chip(picked === null)} onClick={() => setPicked(null)}>
              {t("newChild")}
            </button>
          </div>
        </fieldset>
      )}

      {!child && (
        <div className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-body font-semibold">{t("name")}</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={40}
              autoComplete="off"
              className="min-h-12 rounded-2xl border-[1.5px] border-line bg-paper-raised px-4 text-body"
            />
          </label>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t("gender")}>
            {(["f", "m"] as const).map((g) => (
              <button
                key={g}
                type="button"
                role="radio"
                aria-checked={gender === g}
                className={chip(gender === g)}
                onClick={() => setGender(g)}
              >
                {t(g === "f" ? "girl" : "boy")}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t("age")}>
            {AGES.map((a) => (
              <button
                key={a}
                type="button"
                role="radio"
                aria-checked={age === a}
                className={chip(age === a)}
                onClick={() => setAge(a)}
              >
                {a}
              </button>
            ))}
          </div>
          {gender === "f" && (
            <label className="flex min-h-11 items-center gap-3 text-body">
              <input
                type="checkbox"
                checked={hijab}
                onChange={(e) => setHijab(e.target.checked)}
                className="size-6 accent-night-900"
              />
              {t("hijab")}
            </label>
          )}
        </div>
      )}

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-body font-semibold">{t("story")}</legend>
        {ready.length ? (
          <div className="flex flex-wrap gap-2">
            {ready.map((th) => (
              <button
                key={th.slug}
                type="button"
                className={chip(chosen?.slug === th.slug)}
                onClick={() => setTheme(th.slug)}
              >
                {th.name}
              </button>
            ))}
          </div>
        ) : (
          <Alert>{t("noStory", { gender: child?.gender ?? gender ?? "other" })}</Alert>
        )}
      </fieldset>

      {needsPhoto && (
        <label className="flex cursor-pointer flex-col gap-2 rounded-2xl border-[1.5px] border-dashed border-line bg-paper-raised p-4">
          <span className="text-body font-semibold">{t("photo")}</span>
          <span className="text-small text-ink-muted">{photo ? photo.name : t("photoHint")}</span>
          <input
            type="file"
            accept="image/*"
            className="text-small"
            onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
          />
        </label>
      )}

      {needsConsent && (
        <div className="flex flex-col gap-2">
          <ul className="flex flex-col gap-1.5 text-small text-ink-muted">
            {(["p1", "p3", "p4"] as const).map((p) => (
              <li key={p}>• {tc(`consent.${p}.body`, who)}</li>
            ))}
            <li>• {t("photoRule", who)}</li>
          </ul>
          <label
            className={`flex cursor-pointer items-start gap-3 rounded-2xl p-4 text-body ${consent ? "border-2 border-night-900 bg-night-100" : "border-[1.5px] border-line bg-paper-raised"}`}
          >
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-0.5 size-6 shrink-0 accent-night-900"
            />
            <span>{tc.rich("consent.accept", { ...who, b: (chunks) => <strong>{chunks}</strong> })}</span>
          </label>
          <Link
            href="/privacy"
            target="_blank"
            className="min-h-11 text-small font-semibold text-night-900 underline underline-offset-4"
          >
            {tc("consent.privacy")}
          </Link>
        </div>
      )}

      {error && <Alert>{error}</Alert>}

      <div className="fixed inset-x-0 bottom-0 z-10 border-t border-line bg-paper/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-[640px] px-4 pt-3 pb-6">
          <Button variant="primary" size="lg" className="grow" onClick={submit} loading={busy} disabled={!ready.length}>
            {t("cta")}
          </Button>
        </div>
      </div>
    </div>
  );
}
