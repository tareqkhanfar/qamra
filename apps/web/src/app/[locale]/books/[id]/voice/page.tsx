import { VoiceRecord } from "@/components/voice/VoiceRecord";
import { voiceMetadata } from "@/lib/voiceMeta";

type Props = { params: Promise<{ id: string }> };

export const generateMetadata = () => voiceMetadata("record");

/** «صوت أهلي»: the parent records the book, page by page (design VoiceRecord). */
export default async function VoiceRecordPage({ params }: Props) {
  const { id } = await params;
  return <VoiceRecord id={decodeURIComponent(id)} />;
}
