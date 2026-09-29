import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminGate } from "@/components/admin/AdminGate";
import { PackingSlip } from "@/components/admin/PackingSlip";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("orderPath.slip");
  return { title: t("title"), robots: { index: false, follow: false } };
}

/** The printable packing slip of one order (admin → order → «إيصال التغليف»), without the admin chrome. */
export default async function PackingSlipPage({ params }: Props) {
  const { id } = await params;
  return (
    <main className="min-h-dvh bg-white py-4 print:py-0">
      <AdminGate>
        <PackingSlip id={id} />
      </AdminGate>
    </main>
  );
}
