"use client";

import { useLocale } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";

export function LocaleSwitcher({ label, tone = "light" }: { label: string; tone?: "light" | "dark" }) {
  const locale = useLocale();
  const pathname = usePathname();
  const other = locale === "ar" ? "en" : "ar";
  return (
    <Link
      href={pathname}
      locale={other}
      lang={other}
      className={`inline-flex min-h-11 items-center rounded-full px-3 text-small font-semibold ${tone === "dark" ? "text-night-100 hover:bg-night-800" : "text-night-700 hover:bg-night-100"}`}
    >
      {label}
    </Link>
  );
}
