import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminShell } from "@/components/admin/AdminShell";
import { TemplateEditor } from "@/components/admin/studio/TemplateEditor";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("studio.editor");
  return { title: t("metaTitle"), robots: { index: false, follow: false } };
}

/** One Classic template's pages: hero boxes, locks, redraws, the words and their preview. */
export default async function AdminTemplateEditorPage({ params }: Props) {
  const { id } = await params;
  return (
    <AdminShell active="themes">
      <TemplateEditor id={id} />
    </AdminShell>
  );
}
