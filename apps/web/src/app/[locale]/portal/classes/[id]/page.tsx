import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { ClassBoard } from "@/components/portal/ClassBoard";
import { PortalShell } from "@/components/portal/PortalShell";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("portal"))("nav.board"), robots: { index: false, follow: false } };
}

/** A class's children and their parents' invites (design PortalInvite, ClassReady). */
export default async function ClassPage({ params }: Props) {
  const { id } = await params;
  return (
    <PortalShell active="board" classId={id}>
      <ClassBoard classId={id} />
    </PortalShell>
  );
}
