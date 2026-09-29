import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { Link } from "@/i18n/navigation";

/** The free cover's full-screen frame (design FreeCover): a close button, the title, then the content. */
export async function FreeCoverShell({ children }: { children: ReactNode }) {
  const t = await getTranslations("freeCover");
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col bg-paper">
      <header className="flex h-[60px] items-center justify-between border-b border-line px-4">
        <Link href="/stories" aria-label={t("close")} className="flex size-11 items-center justify-center">
          <svg className="size-[22px]" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </Link>
        <strong className="text-body text-night-900">{t("title")}</strong>
        <span className="w-11" />
      </header>
      <main className="flex flex-1 flex-col">{children}</main>
    </div>
  );
}
