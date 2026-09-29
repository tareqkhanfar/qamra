import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { BatchReview } from "@/components/portal/BatchReview";
import { PortalShell } from "@/components/portal/PortalShell";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("portal"))("nav.review"), robots: { index: false, follow: false } };
}

/** The batch and the review (design PortalBatch, ClassReview, ClassCovers). */
export default async function Page({ params }: Props) {
  const { id } = await params;
  return (
    <PortalShell active="review" classId={id}>
      <BatchReview classId={id} />
    </PortalShell>
  );
}
