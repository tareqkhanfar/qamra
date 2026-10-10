"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { MoonMark } from "@/components/Logo";
import { buttonClasses } from "@/components/ui/Button";
import { brandName } from "@/config/brand";
import { Link } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { readerApi, type SharedBook } from "@/lib/reader";
import { BookReader } from "./BookReader";
import { ReaderMessage, ReaderSkeleton } from "./ReaderStates";

/** A share link: the book only, for family without an account. Nothing else about the child or the parent. */
export function SharedReader({ token }: { token: string }) {
  const t = useTranslations("reader");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [book, setBook] = useState<SharedBook | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    void readerApi.shared(token).then((r) => {
      if (!alive) return;
      if (r.ok) setBook(r.data);
      else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
    });
    return () => {
      alive = false;
    };
  }, [token, locale, te]);

  if (error) return <ReaderMessage title={t("shared.gone")} body={error} href="/" cta={t("shared.visit")} />;
  if (!book) return <ReaderSkeleton label={t("loading")} />;

  const brand = brandName(locale);
  const lead = (
    <Link href="/" aria-label={brand} className="flex shrink-0 items-center">
      <MoonMark className="size-9" tone="dark" />
    </Link>
  );
  const end = (
    <>
      <p className="text-body text-ink-muted">{t("shared.end", { brand, gender: book.hero_gender ?? "other" })}</p>
      <Link href="/" className={buttonClasses("primary", "md")}>
        {t("shared.cta")}
      </Link>
    </>
  );
  return <BookReader book={book} lead={lead} end={end} />;
}
