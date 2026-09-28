import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { PageShell } from "@/components/site/PageShell";
import { CheckoutForm } from "@/components/store/CheckoutForm";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("store.checkout"))("title"), robots: { index: false } };
}

export default async function CheckoutPage() {
  const t = await getTranslations("store.checkout");
  return (
    <PageShell>
      <section className="mx-auto flex max-w-[1100px] flex-col gap-6 px-4 py-8 md:px-10 md:py-12">
        <h1 className="text-h2 text-night-900 md:text-h1">{t("title")}</h1>
        <CheckoutForm />
      </section>
    </PageShell>
  );
}
