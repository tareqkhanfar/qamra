"use client";

import { useLocale } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";

export function LocaleSwitcher({ label }: { label: string }) {
  const locale = useLocale();
  const pathname = usePathname();
  const other = locale === "ar" ? "en" : "ar";
  return (
    <Link
      href={pathname}
      locale={other}
      lang={other}
      className="text-small text-night-700 hover:bg-night-100 inline-flex min-h-11 items-center rounded-full px-3 font-semibold"
    >
      {label}
    </Link>
  );
}
