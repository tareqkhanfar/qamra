"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { ContactIcon } from "@/components/site/ContactIcon";

/**
 * A printed book's code («QB-7K4M2»): bold, monospaced and left to right inside Arabic text, so two orders for
 * children with the same name are told apart at a glance. `copy` adds a button that copies it.
 */
export function BookCode({
  code,
  copy = false,
  className = "",
}: {
  code: string | null | undefined;
  copy?: boolean;
  className?: string;
}) {
  const t = useTranslations("bookCode");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 1500);
    return () => clearTimeout(timer);
  }, [copied]);

  if (!code) return null;
  const write = async () => {
    try {
      await navigator.clipboard.writeText(code);
    } catch {
      window.prompt(t("label"), code); // no clipboard (e.g. plain http): copy it by hand
    }
    setCopied(true);
  };
  return (
    <span className={`inline-flex items-center gap-1.5 ${className}`}>
      <bdi dir="ltr" className="font-mono font-bold tracking-wider text-night-900">
        {code}
      </bdi>
      {copy && (
        <button
          type="button"
          onClick={() => void write()}
          aria-label={t("copyLabel", { code })}
          title={t("copy")}
          className="inline-flex min-h-8 items-center gap-1 rounded-full border border-line bg-paper-raised px-2 text-caption text-ink-muted hover:border-night-700 hover:text-night-900"
        >
          <ContactIcon name="copy" className="size-4" />
          <span aria-live="polite">{copied ? t("copied") : t("copy")}</span>
        </button>
      )}
    </span>
  );
}
