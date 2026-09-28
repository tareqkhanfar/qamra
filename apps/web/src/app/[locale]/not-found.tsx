import { getTranslations } from "next-intl/server";
import { buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";

export default async function NotFound() {
  const t = await getTranslations("errors");
  return (
    <section className="mx-auto mt-20 flex max-w-md flex-col items-center gap-5 text-center">
      <h1 className="text-h2 text-night-900 font-bold">{t("notFoundTitle")}</h1>
      <Link href="/" className={buttonClasses("solid", "md")}>
        {t("backHome")}
      </Link>
    </section>
  );
}
