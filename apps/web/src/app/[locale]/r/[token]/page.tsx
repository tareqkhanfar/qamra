import { VoiceElder } from "@/components/voice/VoiceElder";
import { voiceMetadata } from "@/lib/voiceMeta";

type Props = { params: Promise<{ token: string }> };

export const generateMetadata = () => voiceMetadata("elder");

/** A grandparent's recording link: no account, expires in 7 days (design VoiceElder). */
export default async function VoiceElderPage({ params }: Props) {
  const { token } = await params;
  return <VoiceElder token={decodeURIComponent(token)} />;
}
