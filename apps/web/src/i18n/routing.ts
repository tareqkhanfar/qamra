import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["ar", "en"],
  defaultLocale: "ar",
  localePrefix: "always",
  // Arabic-first product: English only when the parent picks it (remembered in a cookie).
  localeDetection: false,
});

export type Locale = (typeof routing.locales)[number];
