import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { CheckoutScreen } from "@/components/order/CheckoutScreen";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("store.checkout"))("title"), robots: { index: false } };
}

/** Address and cash on delivery (Addendum 9, design Create10): the last step of the order path. */
export default function CheckoutPage() {
  return <CheckoutScreen />;
}
