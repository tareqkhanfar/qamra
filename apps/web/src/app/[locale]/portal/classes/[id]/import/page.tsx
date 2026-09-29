import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { ImportView } from "@/components/portal/ImportView";
import { PortalShell } from "@/components/portal/PortalShell";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("portal"))("nav.import"), robots: { index: false, follow: false } };
}

/** The children list from CSV (design PortalImport). */
export default async function Page({ params }: Props) {
  const { id } = await params;
  return (
    <PortalShell active="import" classId={id}>
      <ImportView classId={id} />
    </PortalShell>
  );
}
