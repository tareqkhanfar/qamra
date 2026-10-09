"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState, type FormEvent } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { useRouter } from "@/i18n/navigation";
import { api, errorText, upload } from "@/lib/api";

type ThemeCard = { slug: string; name: string; status: "available" | "coming_soon" };

const field =
  "min-h-[48px] w-full rounded-sm border border-line bg-paper-raised px-3.5 text-body text-ink outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-100";

/** Admin test books (Addendum 3 §7 acceptance runs): same pipeline, lands in the approval queue. */
export function SampleForm() {
  const t = useTranslations("samples");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [themes, setThemes] = useState<ThemeCard[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasDrawing, setHasDrawing] = useState(false);

  useEffect(() => {
    void (async () => {
      const res = await api<ThemeCard[]>(`/api/themes?lang=${locale}`);
      if (res.ok) setThemes(res.data.filter((th) => th.status === "available"));
    })();
  }, [locale]);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    for (const key of ["hijab", "glasses", "consent", "offline"]) form.set(key, form.get(key) ? "true" : "false");
    if (!(form.get("drawing") as File | null)?.size) form.delete("drawing");
    setBusy(true);
    setError(null);
    const res = await upload<{ book_id: string }>("/api/admin/samples", form);
    setBusy(false);
    if (!res.ok) {
      const details = res.error?.details as { ar?: string; en?: string } | undefined;
      const specific = details && (locale === "ar" ? details.ar : details.en);
      setError(specific || errorText(res.error, locale, res.status === 0 ? te("network") : te("unknown")));
      return;
    }
    router.push("/admin/queue");
  }

  return (
    <form onSubmit={submit} className="mx-auto flex max-w-2xl flex-col gap-5" encType="multipart/form-data">
      <header className="flex flex-col gap-1">
        <h1 className="text-h2 text-night-900 md:text-h1">{t("title")}</h1>
        <p className="text-ink-muted">{t("lead")}</p>
      </header>
      {error && <Alert>{error}</Alert>}
      <div className="grid gap-4 rounded-xl border border-line bg-paper-raised p-5 md:grid-cols-2">
        <label className="flex flex-col gap-1.5 md:col-span-2">
          <span className="font-semibold">{t("theme")}</span>
          <select name="theme" required className={field}>
            {themes.map((th) => (
              <option key={th.slug} value={th.slug}>
                {th.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="font-semibold">{t("name")}</span>
          <input name="name" required maxLength={40} className={field} />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1.5">
            <span className="font-semibold">{t("gender")}</span>
            <select name="gender" className={field}>
              <option value="f">{t("girl")}</option>
              <option value="m">{t("boy")}</option>
            </select>
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="font-semibold">{t("age")}</span>
            <input name="age" type="number" min={2} max={10} defaultValue={5} dir="ltr" className={field} />
          </label>
        </div>
        <label className="flex flex-col gap-1.5">
          <span className="font-semibold">{t("lang")}</span>
          <select name="lang" defaultValue={locale} className={field}>
            <option value="ar">العربية</option>
            <option value="en">English</option>
          </select>
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="font-semibold">{t("style")}</span>
          <select name="style" className={field}>
            <option value="3d">سينمائي ثلاثي الأبعاد · 3D</option>
            <option value="watercolor">مائي فاخر · Watercolor</option>
            <option value="cartoon">كرتون ملوّن · Cartoon</option>
            <option value="semi-realistic">شبه حقيقي · Semi-realistic</option>
          </select>
        </label>
        <label className="flex items-center gap-3">
          <input type="checkbox" name="hijab" className="size-5 accent-night-900" />
          <span>{t("hijab")}</span>
        </label>
        <label className="flex items-center gap-3">
          <input type="checkbox" name="glasses" className="size-5 accent-night-900" />
          <span>{t("glasses")}</span>
        </label>
        <label className="flex flex-col gap-1.5 md:col-span-2">
          <span className="font-semibold">{t("message")}</span>
          <input name="message" maxLength={120} className={field} />
        </label>
        <label className="flex flex-col gap-1.5 md:col-span-2">
          <span className="font-semibold">{t("photos")}</span>
          <input
            name="photos"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            required
            className="text-small file:me-3 file:rounded-full file:border-0 file:bg-night-900 file:px-4 file:py-2 file:text-paper"
          />
          <span className="text-caption text-ink-muted">{t("photosHint")}</span>
        </label>
        <label className="flex flex-col gap-1.5 md:col-span-2">
          <span className="font-semibold">{t("drawing")}</span>
          <input
            name="drawing"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => setHasDrawing(Boolean(e.target.files?.length))}
            className="text-small file:me-3 file:rounded-full file:border-0 file:bg-night-100 file:px-4 file:py-2"
          />
        </label>
        {hasDrawing && (
          <>
            <label className="flex flex-col gap-1.5">
              <span className="font-semibold">{t("companionName")}</span>
              <input name="companion_name" maxLength={30} className={field} />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="font-semibold">{t("companionType")}</span>
              <select name="companion_type" className={field}>
                {(["creature", "animal", "robot", "other"] as const).map((k) => (
                  <option key={k} value={k}>
                    {t(`types.${k}`)}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}
      </div>
      <div className="flex flex-col gap-3 rounded-xl border border-line bg-paper-raised p-5">
        <label className="flex items-start gap-3">
          <input type="checkbox" name="consent" required className="mt-1 size-5 accent-night-900" />
          <span className="font-semibold">{t("consent")}</span>
        </label>
        <label className="flex items-start gap-3">
          <input type="checkbox" name="offline" className="mt-1 size-5 accent-night-900" />
          <span>
            {t("offline")}
            <span className="block text-caption text-ink-muted">{t("offlineHint")}</span>
          </span>
        </label>
      </div>
      <Button type="submit" variant="primary" size="lg" loading={busy} loadingLabel={t("working")}>
        {t("submit")}
      </Button>
    </form>
  );
}
