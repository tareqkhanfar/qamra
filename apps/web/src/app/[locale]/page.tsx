import { getTranslations } from "next-intl/server";
import { MoonMark } from "@/components/Logo";
import { ArrowForward, buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";

export default async function HomePage() {
  const t = await getTranslations("home");
  return (
    <section className="mx-auto flex max-w-2xl flex-col items-center gap-6 pt-14 text-center sm:pt-24">
      <div className="relative">
        <span
          className="animate-twinkle absolute -start-6 -top-2 size-2 rounded-full bg-amber-300"
          aria-hidden="true"
        />
        <span
          className="animate-twinkle absolute -end-8 top-8 size-1.5 rounded-full bg-amber-500 [animation-delay:0.8s]"
          aria-hidden="true"
        />
        <MoonMark className="animate-float size-24" />
      </div>
      <p className="text-caption font-semibold tracking-wide text-amber-700">{t("eyebrow")}</p>
      <h1 className="text-h1 text-night-900 sm:text-display-l font-extrabold">{t("title")}</h1>
      <p className="text-body-l text-ink-muted max-w-xl">{t("subtitle")}</p>
      <div className="flex w-full flex-col items-center gap-3 sm:w-auto sm:flex-row">
        <Link href="/register" className={buttonClasses("primary", "lg", "w-full sm:w-auto")}>
          {t("cta")}
          <ArrowForward />
        </Link>
        <Link href="/login" className={buttonClasses("secondary", "lg", "w-full sm:w-auto")}>
          {t("secondary")}
        </Link>
      </div>
      <p className="text-caption text-sage-700 font-medium">🔒 {t("privacy")}</p>
    </section>
  );
}
