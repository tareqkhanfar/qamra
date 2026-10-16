"use client";

/**
 * «إخفاء الأسعار» for client components: the layout reads the admin switch (`show_prices`) once per request and
 * passes it down, so a client screen knows whether it may show a price. Off when unknown.
 */
import { createContext, useContext, type ReactNode } from "react";

const PricesContext = createContext(false);

export function PricesProvider({ show, children }: { show: boolean; children: ReactNode }) {
  return <PricesContext value={show}>{children}</PricesContext>;
}

/** True only while the admin shows prices to customers. */
export const useShowPrices = (): boolean => useContext(PricesContext);
