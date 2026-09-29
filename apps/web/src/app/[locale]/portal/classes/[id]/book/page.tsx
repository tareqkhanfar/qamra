import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { BookSetup } from "@/components/portal/BookSetup";
import { PortalShell } from "@/components/portal/PortalShell";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("portal"))("nav.book"), robots: { index: false, follow: false } };
}

/** The class book setup (design ClassSetup, PortalClass). */
export default async function Page({ params }: Props) {
  const { id } = await params;
  return (
    <PortalShell active="book" classId={id}>
      <BookSetup classId={id} />
    </PortalShell>
  );
}
