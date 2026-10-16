import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["ar", "en"],
  defaultLocale: "ar",
  localePrefix: "always",
  // Arabic-first product: English only when the parent picks it (remembered in a cookie).
  localeDetection: false,
  // The pages declare their hreflang links themselves (lib/seo.ts, on https://qamra.app); the middleware's
  // `Link` header would name the scheme the edge proxy saw (http) instead.
  alternateLinks: false,
});

export type Locale = (typeof routing.locales)[number];
