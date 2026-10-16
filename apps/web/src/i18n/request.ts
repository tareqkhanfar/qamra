import * as rootParams from "next/root-params";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import { routing } from "./routing";

export default getRequestConfig(async ({ locale }) => {
  if (!locale) {
    const param = await rootParams.locale();
    if (hasLocale(routing.locales, param)) {
      locale = param;
    } else {
      notFound();
    }
  }
  // A missing file the proxy skips (/favicon.ico) reaches the [locale] layout with its name as the locale:
  // its 404 page renders in Arabic instead of failing to load «favicon.ico.json» (a 500).
  if (!hasLocale(routing.locales, locale)) locale = routing.defaultLocale;
  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
