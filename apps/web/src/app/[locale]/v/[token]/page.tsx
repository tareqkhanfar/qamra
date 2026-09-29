import { VoiceListenStart } from "@/components/voice/VoiceListenStart";
import { voiceMetadata } from "@/lib/voiceMeta";

type Props = { params: Promise<{ token: string }> };

export const generateMetadata = () => voiceMetadata("listen");

/** The back cover's QR: the book's first page. */
export default async function VoiceListenStartPage({ params }: Props) {
  const { token } = await params;
  return <VoiceListenStart token={decodeURIComponent(token)} />;
}
