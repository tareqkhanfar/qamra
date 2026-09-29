import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

/** Addendum 9 names the add-ons step `/create/.../addons`; the wizard keeps its state in the query string. */
export default async function AddOnsRoute({ searchParams }: Props) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(await searchParams)) {
    if (typeof value === "string" && key !== "step") query.set(key, value);
  }
  query.set("step", "addons");
  redirect({ href: `/create?${query.toString()}`, locale: await getLocale() });
}
