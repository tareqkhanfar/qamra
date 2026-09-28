import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { PageShell } from "@/components/site/PageShell";
import { CartView } from "@/components/store/CartView";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("store.cart"))("title"), robots: { index: false } };
}

/** The cart (Addendum 4 §5): several books, add-ons, discounts and the running total. */
export default async function CartPage() {
  const t = await getTranslations("store.cart");
  return (
    <PageShell>
      <section className="mx-auto flex max-w-[1100px] flex-col gap-6 px-4 py-8 md:px-10 md:py-12">
        <h1 className="text-h2 text-night-900 md:text-h1">{t("title")}</h1>
        <CartView />
      </section>
    </PageShell>
  );
}
