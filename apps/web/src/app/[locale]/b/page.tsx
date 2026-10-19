import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";

/** `/b` without a book's code: the same page as /hello. */
export default async function BookCodeless() {
  redirect({ href: "/hello", locale: await getLocale() });
}
