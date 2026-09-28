import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { SampleForm } from "@/components/admin/SampleForm";
import { AdminShell } from "@/components/admin/AdminShell";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("admin");
  return { title: t("nav.samples"), robots: { index: false, follow: false } };
}

export default function AdminSamplesPage() {
  return (
    <AdminShell active="samples">
      <SampleForm />
    </AdminShell>
  );
}
