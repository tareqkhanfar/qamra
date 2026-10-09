import { VoiceRecord } from "@/components/voice/VoiceRecord";
import { voiceMetadata } from "@/lib/voiceMeta";

type Props = { params: Promise<{ id: string }>; searchParams: Promise<{ page?: string }> };

export const generateMetadata = () => voiceMetadata("record");

/** «صوت أهلي»: the parent records the book, page by page (design VoiceRecord); `?page=<n>` opens that page
 * (the listen page behind a printed QR links its owner here). */
export default async function VoiceRecordPage({ params, searchParams }: Props) {
  const [{ id }, { page }] = await Promise.all([params, searchParams]);
  const start = Number(page);
  return <VoiceRecord id={decodeURIComponent(id)} start={Number.isInteger(start) ? start : undefined} />;
}
