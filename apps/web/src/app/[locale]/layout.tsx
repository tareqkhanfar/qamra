import type { Metadata, Viewport } from "next";
import { Baloo_Bhaijaan_2, IBM_Plex_Sans_Arabic } from "next/font/google";
import { locale as rootLocale } from "next/root-params";
import { NextIntlClientProvider } from "next-intl";
import { getTranslations } from "next-intl/server";
import { Header } from "@/components/Header";
import { brandName } from "@/config/brand";
import { routing } from "@/i18n/routing";
import "../globals.css";

const baloo = Baloo_Bhaijaan_2({
  subsets: ["arabic", "latin"],
  weight: ["500", "700", "800"],
  variable: "--font-baloo",
});
const plex = IBM_Plex_Sans_Arabic({
  subsets: ["arabic", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-plex",
});

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata(): Promise<Metadata> {
  const locale = await rootLocale();
  const t = await getTranslations({ locale, namespace: "meta" });
  return {
    title: t("title", { brand: brandName(locale) }),
    description: t("description"),
    icons: { icon: "/icon.svg" },
  };
}

export const viewport: Viewport = { themeColor: "#FBF6EC", width: "device-width", initialScale: 1 };

export default async function LocaleLayout({ children }: { children: React.ReactNode }) {
  const locale = await rootLocale();
  return (
    <html lang={locale} dir={locale === "ar" ? "rtl" : "ltr"} className={`${baloo.variable} ${plex.variable}`}>
      <body className="bg-dots min-h-dvh antialiased">
        <NextIntlClientProvider>
          <Header />
          <main className="mx-auto w-full max-w-6xl px-4 pb-16">{children}</main>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
