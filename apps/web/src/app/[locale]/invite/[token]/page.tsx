import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { InviteFlow } from "@/components/portal/InviteFlow";

type Props = { params: Promise<{ token: string }> };

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("portal.invite"))("pageTitle"), robots: { index: false, follow: false } };
}

/** A parent's invite link from their child's kindergarten. */
export default async function InvitePage({ params }: Props) {
  const { token } = await params;
  return <InviteFlow token={decodeURIComponent(token)} />;
}
