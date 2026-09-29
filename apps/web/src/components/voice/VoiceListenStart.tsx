"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Spinner } from "@/components/ui/Button";
import { brandName } from "@/config/brand";
import { Link, useRouter } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { voiceApi } from "@/lib/voice";

/** The back cover's QR (no page number): opens the first story page, in the book's language. */
export function VoiceListenStart({ token }: { token: string }) {
  const t = useTranslations("voice.listen");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    void voiceApi.start(token).then((r) => {
      if (r.ok) router.replace(`/v/${token}/${r.data.first}`, { locale: r.data.language });
      else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
    });
  }, [token, locale, router, te]);
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-night-950 p-6 text-center text-paper">
      {error ? (
        <>
          <h1 className="text-h3">{t("gone")}</h1>
          <p className="text-body text-ink-dark-muted">{error}</p>
          <Link href="/" className="font-bold text-amber-300">
            {t("home", { brand: brandName(locale) })}
          </Link>
        </>
      ) : (
        <Spinner />
      )}
    </main>
  );
}
