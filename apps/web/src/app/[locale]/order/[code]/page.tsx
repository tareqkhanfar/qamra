import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { PageShell } from "@/components/site/PageShell";
import { OrderView } from "@/components/store/OrderView";

type Props = { params: Promise<{ code: string }>; searchParams: Promise<{ placed?: string }> };

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("store.track"))("title"), robots: { index: false } };
}

/** An order's status. The phone that proves it's yours stays in this browser tab (or is asked for). */
export default async function OrderPage({ params, searchParams }: Props) {
  const [{ code }, { placed }] = await Promise.all([params, searchParams]);
  return (
    <PageShell>
      <section className="px-4 py-10 md:py-16">
        <OrderView code={decodeURIComponent(code).toUpperCase()} placed={placed === "1"} />
      </section>
    </PageShell>
  );
}
