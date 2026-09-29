import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { CartScreen } from "@/components/order/CartScreen";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("store.cart"))("title"), robots: { index: false } };
}

/** The cart (Addendum 9, design Cart): a full-screen step of the order path, like the create flow. */
export default function CartPage() {
  return <CartScreen />;
}
