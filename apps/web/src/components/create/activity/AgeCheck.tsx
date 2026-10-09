"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { nameCases } from "@/lib/arabicName";
import { outsideAges } from "@/lib/flows";

/**
 * The review step's age check (§c.8): when the child's age is outside the ages this level or volume is made for,
 * a friendly amber note, with a link back to the product page to choose another one. It never blocks the order.
 */
export function AgeCheck({
  name,
  gender,
  age,
  ages,
  href,
}: {
  name: string;
  gender: "m" | "f";
  age: number;
  ages: [number, number] | null;
  href: string;
}) {
  const t = useTranslations("create.activity.summary");
  if (!ages || !outsideAges(age, ages)) return null;
  return (
    <p role="status" className="rounded-2xl border-[1.5px] border-amber-500 bg-amber-100 px-4 py-3 text-small text-ink">
      {t.rich("ages", {
        ...nameCases(name),
        gender,
        age,
        min: ages[0],
        max: ages[1],
        link: (chunks) => (
          <Link href={href} className="font-bold underline underline-offset-4">
            {chunks}
          </Link>
        ),
      })}
    </p>
  );
}
