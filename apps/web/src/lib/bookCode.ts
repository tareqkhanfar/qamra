/**
 * The code printed in every book («QB-7K4M2»): "QB-" and five symbols from an alphabet without look-alikes
 * (no 0/O, 1/I/L, B/8, G/6, S/5, U/V, Q/Z). The book's QR opens `https://qamra.app/b/QB-7K4M2`, and the owner uses
 * it to tell two orders for children with the same name apart.
 *
 * Pure TypeScript with no "@/" imports, so `node --test src/lib/*.test.ts` loads it (Node strips the types).
 */

export const BOOK_CODE_ALPHABET = "23456789ACDEFHJKMNPRTWXY";

/** A book code as people may type it: any case, with or without the dash. */
export const BOOK_CODE_RE = /^QB-?[23456789ACDEFHJKMNPRTWXY]{5}$/i;

/** "qb7k4m2" / "QB-7k4m2" (also URL-encoded) → "QB-7K4M2"; null for anything that is not a book code. */
export function normalizeBookCode(raw: string | null | undefined): string | null {
  if (!raw) return null;
  let text = raw;
  try {
    text = decodeURIComponent(raw);
  } catch {
    // a lone "%": not a code anyway, the test below says no
  }
  text = text.trim();
  if (!BOOK_CODE_RE.test(text)) return null;
  return `QB-${text.slice(-5).toUpperCase()}`;
}

/** What `GET /api/books/by-code/{code}` tells a visitor: the child's first name and the product, nothing else. */
export type BookByCode = { code: string; child_name: string; product_ar: string; product_en: string };

/**
 * The book a QR page names, or null: the API is asked only for a well-formed code, and any other answer (unknown
 * code, rate limit, the API down, an odd body) is null, so the page shows the same welcome as /hello.
 */
export async function findBookByCode(
  raw: string | null | undefined,
  fetchJson: (path: string) => Promise<unknown>,
): Promise<BookByCode | null> {
  const code = normalizeBookCode(raw);
  if (!code) return null;
  let found: unknown;
  try {
    found = await fetchJson(`/api/books/by-code/${encodeURIComponent(code)}`);
  } catch {
    return null;
  }
  if (!found || typeof found !== "object") return null;
  const book = found as Partial<BookByCode>;
  const name = typeof book.child_name === "string" ? book.child_name.trim() : "";
  if (!name || typeof book.product_ar !== "string" || typeof book.product_en !== "string") return null;
  return { code, child_name: name, product_ar: book.product_ar, product_en: book.product_en };
}
