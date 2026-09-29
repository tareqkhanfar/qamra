"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { Alert } from "@/components/ui/Alert";
import { buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { coverImage, freeCoverApi, shareImage, type FreeCover } from "@/lib/freeCover";
import { money, type Catalog } from "@/lib/store";

const POLL_MS = 3000;

/** Design FreeCover (Addendum 9): the drawn cover, sharing, and the way on to the whole book. */
export function FreeCoverResult({ id, brand }: { id: string; brand: string }) {
  const t = useTranslations("freeCover");
  const locale = useLocale();
  const [cover, setCover] = useState<FreeCover | null>(null);
  const [missing, setMissing] = useState(false);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    api<Catalog>("/api/store/catalog").then((r) => alive && r.ok && setCatalog(r.data));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      const r = await freeCoverApi.get(id);
      if (!alive) return;
      if (!r.ok) {
        setMissing(true);
        clearInterval(timer);
        return;
      }
      setCover(r.data);
      if (r.data.status !== "drawing") clearInterval(timer); // ready or failed: stop asking
    };
    const timer = setInterval(() => {
      setTick((n) => n + 1);
      void load();
    }, POLL_MS);
    void load();
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [id]);

  if (missing) return <Alert>{t("notFound")}</Alert>;
  if (!cover || cover.status === "drawing") {
    return (
      <div role="status" className="flex flex-col items-center gap-4 py-16 text-center">
        <MoonPhase p={((tick % 12) + 1) / 12} className="size-24" />
        <h1 className="text-[26px] text-night-900">{t("drawing")}</h1>
        <p className="text-body text-ink-muted">{t("drawingBody")}</p>
      </div>
    );
  }
  if (cover.status === "failed") {
    return (
      <div className="flex flex-col gap-4 py-10">
        <Alert>{t("failed")}</Alert>
        <Link href="/free-cover" className={buttonClasses("secondary", "md", "self-start")}>
          {t("again")}
        </Link>
      </div>
    );
  }

  const name = cover.child_name;
  const price = (slug: string) => {
    const p = catalog?.products.find((x) => x.slug === slug)?.from_price;
    return p ? money(p, catalog?.currency ?? "ILS", locale) : "";
  };
  const next = (line: "classic" | "magic") => `/create?child=${cover.child_id}&line=${line}&theme=${cover.theme}`;
  const text = t("shareText", { name, brand });
  return <ResultView cover={cover} name={name} price={price} next={next} text={text} />;
}

function ResultView({
  cover,
  name,
  price,
  next,
  text,
}: {
  cover: FreeCover;
  name: string;
  price: (slug: string) => string;
  next: (line: "classic" | "magic") => string;
  text: string;
}) {
  const t = useTranslations("freeCover");
  const tile =
    "flex min-h-[72px] flex-col items-center justify-center gap-1 rounded-2xl border border-line bg-paper-raised text-small font-semibold text-night-900";
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1">
        <h1 className="text-[28px] text-night-900">{t("readyTitle", { name })}</h1>
        <p className="text-body text-ink-muted">{t("body")}</p>
      </div>
      <div className="flex justify-center rounded-3xl bg-paper-sunk py-6">
        {/* eslint-disable-next-line @next/next/no-img-element -- the parent's own watermarked cover, through the API */}
        <img
          src={coverImage(cover.id, "cover.jpg")}
          alt={t("alt", { name })}
          className="aspect-square w-[min(270px,72vw)] rounded-[16px_6px_6px_16px] border-l-[10px] border-night-950 shadow-2 rtl:rounded-[6px_16px_16px_6px] rtl:border-r-[10px] rtl:border-l-0"
        />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <button
          type="button"
          className={tile}
          onClick={() => void shareImage(coverImage(cover.id, "cover.jpg"), "cover.jpg", text)}
        >
          <svg className="size-6 text-success" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M4 20l1.4-4.2A8 8 0 1 1 8.4 18.7Z"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinejoin="round"
            />
          </svg>
          {t("whatsapp")}
        </button>
        <button
          type="button"
          className={tile}
          onClick={() => void shareImage(coverImage(cover.id, "story.jpg"), "story.jpg", text)}
        >
          <svg className="size-6 text-amber-700" viewBox="0 0 24 24" aria-hidden="true">
            <rect x="4" y="3" width="16" height="18" rx="4" fill="none" stroke="currentColor" strokeWidth="2" />
            <circle cx="12" cy="12" r="3.5" fill="none" stroke="currentColor" strokeWidth="2" />
          </svg>
          {t("storyShare")}
        </button>
        <a className={tile} href={coverImage(cover.id, "cover.jpg", true)} download>
          <svg className="size-6" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M12 4v11M7 10l5 5 5-5M5 20h14"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
          {t("download")}
        </a>
      </div>
      <p className="text-small text-ink-muted">{t("onlyDrawn", { name })}</p>

      <section className="flex flex-col gap-2.5">
        <h2 className="text-[20px] text-night-900">{t("continue")}</h2>
        <Link
          href={next("classic")}
          className="flex min-h-[72px] items-center gap-3 rounded-[18px] border-[1.5px] border-line bg-paper-raised px-4 py-3"
        >
          <span className="flex grow flex-col gap-0.5">
            <strong className="text-body">{t("classic")}</strong>
            <span className="text-small text-ink-muted">{t("classicBody")}</span>
          </span>
          {price("classic-book") && (
            <strong className="whitespace-nowrap">{t("from", { price: price("classic-book") })}</strong>
          )}
        </Link>
        <Link
          href={next("magic")}
          className="flex min-h-[72px] items-center gap-3 rounded-[18px] bg-night-900 px-4 py-3 text-paper"
        >
          <span className="flex grow flex-col gap-0.5">
            <strong className="text-body">{t("magic")}</strong>
            <span className="text-small text-night-100">{t("magicBody", { name })}</span>
          </span>
          {price("magic-book") && <strong className="whitespace-nowrap text-amber-300">{price("magic-book")}</strong>}
        </Link>
      </section>

      <div className="flex items-center gap-3 rounded-2xl bg-success-bg p-3.5 text-small">
        <svg className="size-[22px] shrink-0 text-success" viewBox="0 0 24 24" aria-hidden="true">
          <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" />
            <path d="M9 12l2 2 4-4" />
          </g>
        </svg>
        <span>{t("privacy", { name })}</span>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-10 border-t border-line bg-paper/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-[640px] px-4 pt-3 pb-6">
          <Link href={next("classic")} className={buttonClasses("primary", "lg", "grow")}>
            {price("classic-book") ? t("ctaBook", { name, price: price("classic-book") }) : t("ctaPlain", { name })}
          </Link>
        </div>
      </div>
    </div>
  );
}
