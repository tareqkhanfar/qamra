export const dynamic = "force-dynamic";

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";

export default async function AdminIndex() {
  redirect({ href: "/admin/settings", locale: await getLocale() });
}
