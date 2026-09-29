import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminShell } from "@/components/admin/AdminShell";
import { ThemeVersions } from "@/components/admin/studio/ThemeVersions";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("studio.versions");
  return { title: t("title"), robots: { index: false, follow: false } };
}

/** Theme versions: review, publish, history and rollback, and the English draft. */
export default async function AdminThemeVersionsPage({ searchParams }: Props) {
  const theme = (await searchParams).theme;
  return (
    <AdminShell active="themes">
      <ThemeVersions initialTheme={typeof theme === "string" ? theme : null} />
    </AdminShell>
  );
}
