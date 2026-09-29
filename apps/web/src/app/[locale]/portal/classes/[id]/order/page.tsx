import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { OrderView } from "@/components/portal/OrderView";
import { PortalShell } from "@/components/portal/PortalShell";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("portal"))("nav.order"), robots: { index: false, follow: false } };
}

/** The class order and invoice (design ClassPrint, PortalOrder). */
export default async function Page({ params }: Props) {
  const { id } = await params;
  return (
    <PortalShell active="order" classId={id}>
      <OrderView classId={id} />
    </PortalShell>
  );
}
