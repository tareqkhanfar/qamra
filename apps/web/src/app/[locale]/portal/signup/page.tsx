import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { SignupForm } from "@/components/portal/SignupForm";
import { PageShell } from "@/components/site/PageShell";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("portal.signup");
  return { title: t("title"), description: t("lead") };
}

/** A kindergarten asks to join (CLAUDE.md §8: our team approves it). */
export default function PortalSignupPage() {
  return (
    <PageShell>
      <section className="px-4 py-10 md:py-16">
        <SignupForm />
      </section>
    </PageShell>
  );
}
