import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { PageShell } from "@/components/site/PageShell";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata(): Promise<Metadata> {
  const [t, locale] = await Promise.all([getTranslations("privacyPage"), getLocale()]);
  return pageMetadata({ path: "/privacy", locale, title: t("title"), description: t("lead") });
}

const TERMS = [
  { label: "Anthropic — Commercial Terms", href: "https://www.anthropic.com/legal/commercial-terms" },
  { label: "Google — Gemini API Additional Terms", href: "https://ai.google.dev/gemini-api/terms" },
  { label: "fal.ai — Terms of Service", href: "https://fal.ai/terms" },
  { label: "fal.ai — Data Processing Addendum", href: "https://fal.ai/legal/data-processing-addendum" },
];

/** Privacy page (Addendum 3 §6.5): what happens to children's photos, and the providers' terms. */
export default async function PrivacyPage() {
  const t = await getTranslations("privacyPage");
  const sections = t.raw("sections") as { h: string; p: string }[];
  return (
    <PageShell>
      <article className="mx-auto flex max-w-3xl flex-col gap-8 px-4 py-10 md:py-16">
        <header className="flex flex-col gap-3">
          <h1 className="text-h1 text-night-900 md:text-display-l">{t("title")}</h1>
          <p className="text-body-l text-ink-muted">{t("lead")}</p>
        </header>
        {sections.map((s) => (
          <section key={s.h} className="flex flex-col gap-2" data-reveal>
            <h2 className="text-h3 text-night-900">{s.h}</h2>
            <p className="text-body-l text-ink">{s.p}</p>
          </section>
        ))}
        <section className="flex flex-col gap-2 rounded-xl border border-line bg-paper-raised p-5">
          <h2 className="text-h3 text-night-900">{t("links")}</h2>
          <ul className="flex flex-col gap-1" dir="ltr">
            {TERMS.map((l) => (
              <li key={l.href}>
                <a
                  href={l.href}
                  rel="noreferrer"
                  target="_blank"
                  className="text-night-800 underline underline-offset-4"
                >
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </section>
        <p className="text-small text-ink-muted">{t("updated")}</p>
      </article>
    </PageShell>
  );
}
