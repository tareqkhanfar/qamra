/** «حكاية خاصة» (Magic custom story, product magic-custom-story): the family's brief for a story of their own. */
import { useState } from "react";
import type { Catalog } from "@/lib/store";

export const CUSTOM_THEME = "custom";
export const CUSTOM_PRODUCT = "magic-custom-story";
export const LIMITS = { short: 60, wish: 120, role: 20, name: 30, family: 6 } as const;

export type FamilyMember = { role: string; name: string };
export type CustomBrief = {
  occasion: string;
  place: string;
  loves: [string, string, string];
  wish: string;
  family: FamilyMember[];
};

export const emptyBrief = (): CustomBrief => ({ occasion: "", place: "", loves: ["", "", ""], wish: "", family: [] });

const filled = (s: string) => s.trim().length >= 2;

/** Every required field has at least 2 letters: occasion, place, 2 of the 3 loved things, the wish. */
export function briefReady(b: CustomBrief): boolean {
  return filled(b.occasion) && filled(b.place) && b.loves.filter(filled).length >= 2 && filled(b.wish);
}

/** What the API gets: trimmed, empty loved things and people without a role left out. */
export function briefBody(b: CustomBrief) {
  return {
    occasion: b.occasion.trim(),
    place: b.place.trim(),
    loves: b.loves.map((s) => s.trim()).filter(Boolean),
    wish: b.wish.trim(),
    family: b.family.filter((m) => m.role.trim()).map((m) => ({ role: m.role.trim(), name: m.name.trim() || null })),
  };
}

export type CustomBriefBody = ReturnType<typeof briefBody>;

/** The extra price of a custom story over the Magic book (both from the catalog, the admin's prices). */
export function customExtra(catalog: Catalog | null): number | null {
  const low = (slug: string) => {
    const prices = (catalog?.products.find((p) => p.slug === slug)?.variants ?? [])
      .map((v) => Number(v.price))
      .filter((n) => Number.isFinite(n) && n > 0);
    return prices.length ? Math.min(...prices) : null;
  };
  const custom = low(CUSTOM_PRODUCT);
  const magic = low("magic-book");
  return custom !== null && magic !== null ? custom - magic : null;
}

/** The brief as the parent types it; kept in this tab (sessionStorage) so going back never loses it. The story
 * step renders only after the wizard's data loaded in the browser, so reading storage at first render is safe. */
export function useCustomBrief(childId: string): [CustomBrief, (b: CustomBrief) => void] {
  const key = `qamra:custom-brief:${childId}`;
  const [brief, setBrief] = useState<CustomBrief>(() => {
    try {
      const saved = typeof window === "undefined" ? null : window.sessionStorage.getItem(key);
      return saved ? { ...emptyBrief(), ...(JSON.parse(saved) as Partial<CustomBrief>) } : emptyBrief();
    } catch {
      return emptyBrief(); // storage blocked or unreadable: start empty
    }
  });
  function update(b: CustomBrief) {
    setBrief(b);
    try {
      window.sessionStorage.setItem(key, JSON.stringify(b));
    } catch {
      // a private window may refuse storage; the form still works
    }
  }
  return [brief, update];
}
