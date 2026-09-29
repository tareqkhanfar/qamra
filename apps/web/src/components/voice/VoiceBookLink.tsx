"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Link } from "@/i18n/navigation";
import { voiceApi } from "@/lib/voice";
import { Icon, ICONS } from "./VoicePieces";

/** The parent's books bought with «أصوات العائلة» (one request for the whole account page). */
export function useVoiceBooks(): Set<string> {
  const [ids, setIds] = useState<Set<string>>(new Set());
  useEffect(() => {
    void voiceApi.mine().then((r) => r.ok && setIds(new Set(r.data)));
  }, []);
  return ids;
}

export function VoiceBookLink({ id }: { id: string }) {
  const t = useTranslations("voice");
  return (
    <Link
      href={`/books/${id}/voice`}
      className="flex min-h-11 items-center gap-1.5 self-start rounded-full bg-amber-100 px-3 text-caption font-bold text-amber-700"
    >
      <Icon d={ICONS.mic} className="size-4" />
      {t("accountLink")}
    </Link>
  );
}
