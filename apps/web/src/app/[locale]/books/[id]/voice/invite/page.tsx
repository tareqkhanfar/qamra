import { VoiceInvite } from "@/components/voice/VoiceInvite";
import { voiceMetadata } from "@/lib/voiceMeta";

type Props = { params: Promise<{ id: string }> };

export const generateMetadata = () => voiceMetadata("invite");

/** Invite a grandparent to record from their own phone (design VoiceInvite). */
export default async function VoiceInvitePage({ params }: Props) {
  const { id } = await params;
  return <VoiceInvite id={decodeURIComponent(id)} />;
}
