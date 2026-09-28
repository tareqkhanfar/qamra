import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminMetrics } from "@/components/admin/AdminMetrics";
import { AdminShell } from "@/components/admin/AdminShell";
import { SelfHostedCard } from "@/components/admin/SelfHostedCard";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("admin");
  return { title: t("nav.metrics"), robots: { index: false, follow: false } };
}

export default function AdminMetricsPage() {
  return (
    <AdminShell active="metrics">
      <div className="flex flex-col gap-8">
        <AdminMetrics />
        <SelfHostedCard />
      </div>
    </AdminShell>
  );
}
