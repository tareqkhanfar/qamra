import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { getPublicSettings, pricesShown } from "@/lib/catalog";
import { adminGateMessages } from "@/lib/clientMessages";
import { isVerifiedAdmin } from "@/lib/staffSession";

/**
 * The staff's messages (costs, margins, printer prices, the studio…) reach the browser only here, and only for a
 * verified admin session; anyone else gets the public messages and the admin gate's lines. A nested provider
 * replaces the root one's messages, so the admin's set is the whole file.
 */
export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const [messages, admin] = await Promise.all([getMessages(), isVerifiedAdmin()]);
  const prices = admin || pricesShown(await getPublicSettings());
  return (
    <NextIntlClientProvider messages={admin ? messages : adminGateMessages(messages, { prices })}>
      {children}
    </NextIntlClientProvider>
  );
}
