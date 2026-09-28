import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { CreateWizard } from "@/components/create/CreateWizard";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("create"))("newBook"), robots: { index: false } };
}

/** The create flow (design Create1–Create9): a full-screen wizard; its state lives in the URL and the API. */
export default function CreatePage() {
  return (
    <Suspense>
      <CreateWizard />
    </Suspense>
  );
}
