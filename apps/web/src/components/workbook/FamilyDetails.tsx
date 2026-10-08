/**
 * «مغامراتي مع عائلتي»: the family as the book prints it (A7 §7): the relations it knows, a member, and what the
 * cart line gets. The form is the order flow's family step (create/activity/FamilyStep.tsx), after the child is
 * chosen; the product page asks nothing (order flows §c.7, chunk 11).
 */

/** The relations the book knows (the API's `RELATIONS`): the word it prints and the figure it draws. */
export const RELATIONS = [
  "mother",
  "father",
  "grandmother",
  "grandfather",
  "maternal-aunt",
  "paternal-aunt",
  "maternal-uncle",
  "paternal-uncle",
  "brother",
  "sister",
  "baby",
  "other",
] as const;
export type Relation = (typeof RELATIONS)[number];
const SCARF: readonly Relation[] = ["mother", "grandmother", "maternal-aunt", "paternal-aunt", "sister", "other"];
export const MAX_MEMBERS = 6; // A7 §7: what the book's pages hold

export type FamilyMember = { relation: Relation | ""; name: string; adult: boolean; scarf: boolean };
export type Family = { name: string; city: string; members: FamilyMember[] };
export const emptyFamily = (): Family => ({ name: "", city: "", members: [] });

/** What `POST /api/shop/workbooks/cart` gets as `family`, or undefined when the parent skipped it. */
export function familyPayload(f: Family) {
  const members = f.members
    .filter((m) => m.relation)
    .map((m) => ({
      relation: m.relation,
      name: m.name.trim(),
      ...(m.relation === "other" ? { adult: m.adult } : {}),
      scarf: SCARF.includes(m.relation as Relation) && m.scarf,
    }));
  if (!f.name.trim() && !f.city.trim() && !members.length) return undefined;
  return { name: f.name.trim(), city: f.city.trim(), members };
}
