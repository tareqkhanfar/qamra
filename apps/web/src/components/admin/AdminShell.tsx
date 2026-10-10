import type { ReactNode } from "react";
import { getLocale, getTranslations } from "next-intl/server";
import { brandName } from "@/config/brand";
import { Link } from "@/i18n/navigation";
import { AdminGate } from "./AdminGate";

type Section =
  | "queue"
  | "samples"
  | "orders"
  | "catalog"
  | "printCosts"
  | "reports"
  | "metrics"
  | "settings"
  | "printBatches"
  | "organizations"
  | "leads"
  | "themes"
  | "journeyAudio"
  | "islamicReview"
  | "staff"
  | "audit";

/** Admin chrome (design: admin artboards): night sidebar with brand + «إدارة» badge; content on paper. */
export async function AdminShell({ active, children }: { active: Section; children: ReactNode }) {
  const [t, locale] = await Promise.all([getTranslations("admin"), getLocale()]);
  const tp = await getTranslations("printBatches"); // print batches: their label lives in their namespace
  const tk = await getTranslations("portal.admin"); // kindergartens (Phase 4 portal)
  const ts = await getTranslations("studio.nav"); // the template studio: staff roles and the audit log
  const tj = await getTranslations("journeyAudio.admin"); // «رحلتي الأولى»: the audio QR recordings
  const ti = await getTranslations("islamicReview"); // «قلبي يعرف الله»: the scholar's review
  const items = [
    { id: "queue", href: "/admin/queue", ready: true },
    { id: "samples", href: "/admin/samples", ready: true },
    { id: "orders", href: "/admin/orders", ready: true },
    { id: "catalog", href: "/admin/catalog", ready: true },
    { id: "printCosts", href: "/admin/print-costs", ready: true },
    { id: "printBatches", href: "/admin/print-batches", ready: true, label: tp("nav") },
    { id: "organizations", href: "/admin/organizations", ready: true, label: tk("nav") },
    {
      id: "leads",
      href: "/admin/leads",
      ready: true,
      label: locale === "en" ? "Quote requests" : "طلبات عروض الأسعار",
    },
    { id: "reports", href: "/admin/reports", ready: true },
    { id: "themes", href: "/admin/studio/themes", ready: true }, // the theme editor; its tabs lead to the templates
    { id: "journeyAudio", href: "/admin/journey-audio", ready: true, label: tj("nav") },
    { id: "islamicReview", href: "/admin/islamic-review", ready: true, label: ti("nav") },
    { id: "metrics", href: "/admin/metrics", ready: true },
    { id: "settings", href: "/admin/settings", ready: true },
    { id: "staff", href: "/admin/staff", ready: true, label: ts("staff") },
    { id: "audit", href: "/admin/audit", ready: true, label: ts("audit") },
  ] as const;
  return (
    <div className="min-h-dvh bg-paper lg:grid lg:grid-cols-[260px_1fr]">
      <aside className="bg-night-950 text-ink-dark-muted lg:min-h-dvh">
        <div className="flex items-center justify-between gap-3 px-5 py-4 lg:flex-col lg:items-stretch lg:py-6">
          <Link href="/" className="flex items-center gap-2">
            <span className="font-display text-[26px] font-extrabold text-paper">{brandName(locale)}</span>
            <span className="rounded-full bg-amber-500 px-2 py-0.5 text-xs font-bold text-night-950">{t("badge")}</span>
          </Link>
          <nav className="flex gap-1 overflow-x-auto lg:mt-6 lg:flex-col" aria-label={t("title")}>
            {items.map((it) =>
              it.ready ? (
                <Link
                  key={it.id}
                  href={it.href}
                  aria-current={active === it.id ? "page" : undefined}
                  className={`flex min-h-11 items-center rounded-sm px-3 font-semibold whitespace-nowrap ${active === it.id ? "bg-night-800 text-paper" : "hover:bg-night-900 hover:text-paper"}`}
                >
                  {"label" in it ? it.label : t(`nav.${it.id}`)}
                </Link>
              ) : (
                <span
                  key={it.id}
                  className="flex min-h-11 items-center justify-between gap-2 rounded-sm px-3 whitespace-nowrap opacity-60"
                >
                  {t(`nav.${it.id}`)}
                  <span className="rounded-full bg-night-800 px-2 py-0.5 text-[11px]">{t("soon")}</span>
                </span>
              ),
            )}
          </nav>
          <Link href="/" className="hidden text-small text-ink-dark-muted hover:text-paper lg:mt-auto lg:block">
            {t("backToSite")}
          </Link>
        </div>
      </aside>
      <main className="min-w-0 px-4 py-6 md:px-10 md:py-10">
        <AdminGate>{children}</AdminGate>
      </main>
    </div>
  );
}
