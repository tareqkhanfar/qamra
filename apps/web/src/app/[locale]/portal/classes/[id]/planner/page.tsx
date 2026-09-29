import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Planner } from "@/components/portal/Planner";
import { PortalShell } from "@/components/portal/PortalShell";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("portal"))("nav.planner"), robots: { index: false, follow: false } };
}

/** The page planner (design ClassPlanner). */
export default async function Page({ params }: Props) {
  const { id } = await params;
  return (
    <PortalShell active="planner" classId={id}>
      <Planner classId={id} />
    </PortalShell>
  );
}
