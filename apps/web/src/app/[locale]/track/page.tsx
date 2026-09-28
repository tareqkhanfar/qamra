import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { PageShell } from "@/components/site/PageShell";
import { TrackForm } from "@/components/store/OrderView";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("store.track"))("title"), robots: { index: false } };
}

export default async function TrackPage() {
  return (
    <PageShell>
      <section className="px-4 py-10 md:py-16">
        <TrackForm />
      </section>
    </PageShell>
  );
}
