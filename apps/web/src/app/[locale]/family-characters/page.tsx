import type { Metadata } from "next";
import { SiteFooter } from "@/components/site/SiteFooter";
import { FamilyCharacters } from "@/components/workbook/FamilyCharacters";

export const metadata: Metadata = { title: "رسم أفراد العائلة", robots: { index: false, follow: false } };

/** The illustrated-family add-on (Addendum 7 §7): the parent's page for each person's consent, photo and drawing. */
export default function FamilyCharactersPage() {
  return (
    <>
      <main className="mx-auto w-full max-w-[760px] px-4 py-10">
        <FamilyCharacters />
      </main>
      <SiteFooter />
    </>
  );
}
