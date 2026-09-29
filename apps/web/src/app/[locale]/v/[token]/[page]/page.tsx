import { notFound } from "next/navigation";
import { VoiceListen } from "@/components/voice/VoiceListen";
import { voiceMetadata } from "@/lib/voiceMeta";

type Props = { params: Promise<{ token: string; page: string }> };

export const generateMetadata = () => voiceMetadata("listen");

/** A story page's printed QR: `https://{BRAND_DOMAIN}/v/{token}/{page}` (design VoiceListen). */
export default async function VoiceListenPage({ params }: Props) {
  const { token, page } = await params;
  const beat = Number(page);
  if (!Number.isInteger(beat) || beat < 1 || beat > 99) notFound();
  return <VoiceListen token={decodeURIComponent(token)} beat={beat} />;
}
