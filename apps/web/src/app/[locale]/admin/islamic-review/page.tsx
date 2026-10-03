import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminIslamicReview } from "@/components/admin/AdminIslamicReview";
import { AdminShell } from "@/components/admin/AdminShell";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("islamicReview");
  return { title: t("title"), robots: { index: false, follow: false } };
}

/** «قلبي يعرف الله»: the scholar's review, unit by unit (Addendum 10 §3.3). */
export default function AdminIslamicReviewPage() {
  return (
    <AdminShell active="islamicReview">
      <AdminIslamicReview />
    </AdminShell>
  );
}
