import { useTranslations } from "next-intl";
import { Scene, fromArt } from "@/components/art/Scene";
import { Link } from "@/i18n/navigation";
import type { ThemeCard } from "@/lib/catalog";

const TAG_STYLE: Record<string, string> = {
  popular: "bg-amber-500 text-night-950",
  new: "bg-success-bg text-success",
  kindergarten: "bg-night-900 text-paper",
  coming_soon: "bg-lav-300 text-night-900",
};

/** Story-world card. `strip` = landing (compact), `catalog` = the themes grid (chips, price, CTA). */
export function ThemeCardView({
  theme,
  variant,
  price,
}: {
  theme: ThemeCard;
  variant: "strip" | "catalog";
  price?: string | null;
}) {
  const t = useTranslations("common");
  const soon = theme.status === "coming_soon";
  const tag = soon ? "coming_soon" : theme.tag;
  const ages = t("ages", { min: theme.age_min, max: theme.age_max });
  return (
    <Link
      href={`/themes/${theme.slug}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-line bg-paper-raised text-ink transition hover:-translate-y-0.5 hover:shadow-2"
    >
      <div className="relative">
        <Scene
          {...fromArt(theme.art)}
          ratio={variant === "catalog" ? 400 / 260 : 300 / 240}
          kidScale={theme.art.kid_scale ?? 0.72}
        />
        {variant === "catalog" && tag && (
          <span
            className={`absolute start-3.5 top-3.5 rounded-full px-3 py-1.5 text-caption font-bold ${TAG_STYLE[tag]}`}
          >
            {t(`tags.${tag}`)}
          </span>
        )}
        {variant === "strip" && soon && (
          <span
            className={`absolute start-3 top-3 rounded-full px-2.5 py-1 text-caption font-bold ${TAG_STYLE.coming_soon}`}
          >
            {t("comingSoon")}
          </span>
        )}
      </div>
      {variant === "strip" ? (
        <div className="flex flex-col gap-1.5 p-5">
          <span className="text-caption font-semibold text-ink-muted">{ages}</span>
          <h3 className="text-[22px] leading-tight text-night-900">{theme.name}</h3>
          <p className="text-small text-ink-muted">{theme.tagline}</p>
        </div>
      ) : (
        <div className="flex grow flex-col gap-2 p-[22px]">
          <div className="flex gap-2 text-caption">
            <span className="rounded-full bg-night-100 px-2.5 py-1 text-night-900">{ages}</span>
            <span className="rounded-full bg-paper-sunk px-2.5 py-1">{t("pages", { count: theme.pages })}</span>
          </div>
          <h3 className="text-[24px] leading-tight text-night-900">{theme.name}</h3>
          <p className="text-[15px] leading-relaxed text-ink-muted">{theme.tagline}</p>
          <div className="mt-auto flex items-center justify-between gap-3 pt-1.5">
            <strong className="text-body">
              {soon ? t("comingSoon") : price ? t("priceFrom", { price }) : t("priceSoon")}
            </strong>
            {!soon && (
              <span className="text-[15px] font-bold text-amber-700">
                {t("chooseWorld")} <span className="inline-block rtl:-scale-x-100">→</span>
              </span>
            )}
          </div>
        </div>
      )}
    </Link>
  );
}
