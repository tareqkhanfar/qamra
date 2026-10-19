/**
 * The book code printed in every book («QB-7K4M2») and the QR page it opens (`/b/QB-7K4M2`, or `/hello` without a
 * book): `npm test` (node --test; Node strips the types).
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { BOOK_CODE_ALPHABET, BOOK_CODE_RE, findBookByCode, normalizeBookCode } from "./bookCode.ts";

describe("normalizeBookCode", () => {
  it("accepts any case, with or without the dash, and gives «QB-XXXXX»", () => {
    assert.equal(normalizeBookCode("QB-7K4M2"), "QB-7K4M2");
    assert.equal(normalizeBookCode("qb-7k4m2"), "QB-7K4M2");
    assert.equal(normalizeBookCode("qb7k4m2"), "QB-7K4M2");
    assert.equal(normalizeBookCode("  QB7K4M2 "), "QB-7K4M2");
    assert.equal(normalizeBookCode("QB%2D7K4M2"), "QB-7K4M2"); // URL-encoded dash
  });

  it("refuses everything that is not a book code", () => {
    for (const bad of [
      "",
      null,
      undefined,
      "QB-7K4M", // too short
      "QB-7K4M22", // too long
      "QB-7K4M0", // 0 is not in the alphabet (looks like O)
      "QB-1K4M2", // nor 1 (I, L)
      "QB-BK4M2", // nor B (8)
      "QB-OK4M2",
      "7K4M2", // no prefix
      "QB--7K4M2",
      "QB-7K4M2.png",
      "QB 7K4M2", // a space is the admin search's job, not a printed URL's
      "%",
      "../QB-7K4M2",
    ])
      assert.equal(normalizeBookCode(bad), null, String(bad));
  });

  it("the pattern and the alphabet agree", () => {
    assert.equal(BOOK_CODE_ALPHABET.length, 24);
    for (const ch of BOOK_CODE_ALPHABET) assert.ok(BOOK_CODE_RE.test(`QB-${ch.repeat(5)}`), ch);
    for (const ch of "01BGILOQSUVZ") assert.ok(!BOOK_CODE_RE.test(`QB-${ch.repeat(5)}`), ch);
  });
});

describe("findBookByCode", () => {
  const book = { code: "QB-7K4M2", child_name: "سلمى", product_ar: "دوسية التأسيس", product_en: "Foundation workbook" };

  it("never asks the API for a malformed code (the page is then /hello)", async () => {
    let asked = 0;
    const fetchJson = async () => {
      asked++;
      return book;
    };
    for (const bad of ["", "hello", "QB-0000O", "QB-7K4M2/../x"])
      assert.equal(await findBookByCode(bad, fetchJson), null, bad);
    assert.equal(asked, 0);
  });

  it("asks for the normalized code and keeps only the first name and the product", async () => {
    let path = "";
    const found = await findBookByCode("qb7k4m2", async (p) => {
      path = p;
      return { ...book, photo: "secret", parent_phone: "0590000000" };
    });
    assert.equal(path, "/api/books/by-code/QB-7K4M2");
    assert.deepEqual(found, book);
  });

  it("an unknown code, a rate limit, a broken API or an odd answer is the plain page", async () => {
    assert.equal(await findBookByCode("QB-7K4M2", async () => null), null); // 404 / 429
    assert.equal(
      await findBookByCode("QB-7K4M2", async () => {
        throw new Error("down");
      }),
      null,
    );
    assert.equal(await findBookByCode("QB-7K4M2", async () => ({ error: "not_found" })), null);
    assert.equal(await findBookByCode("QB-7K4M2", async () => ({ ...book, child_name: " " })), null);
  });
});

describe("the QR page", () => {
  const web = new URL("../../", import.meta.url);
  const source = (path: string) => readFileSync(new URL(path, web), "utf8");

  it("/hello renders the page without a book, and /b/{code} only looks the code up", () => {
    assert.match(source("src/app/[locale]/hello/page.tsx"), /<HelloPage book=\{null\} \/>/);
    assert.match(source("src/app/[locale]/b/[code]/page.tsx"), /getBookByCode\(code,/);
  });

  it("without a book: no book card, no extra-copy button and no code in any link", () => {
    const page = source("src/components/site/HelloPage.tsx");
    assert.match(page, /\{book && \(/); // the child's first name and the product only with a found book
    assert.match(page, /\{code && \(/); // «اطلبوا نسخة إضافية» only with a found book's code
    assert.match(page, /const code = book\?\.code;/);
  });

  it("/b/{code} is never indexed and the proxy gives it a language", () => {
    assert.match(source("src/app/[locale]/b/[code]/page.tsx"), /robots: \{ index: false, follow: false \}/);
    assert.match(source("src/lib/seo.ts"), /"\/b\/",/);
    // the matcher skips only paths with a dot (files) and Next's own: "/b/QB-7K4M2" goes through next-intl
    assert.ok(source("src/proxy.ts").includes('"/((?!_next|_vercel|audio|.*\\\\..*).*)"'));
    const re = new RegExp("^/((?!_next|_vercel|audio|.*\\..*).*)$");
    assert.ok(re.test("/b/QB-7K4M2"));
    assert.ok(re.test("/hello"));
  });

  for (const locale of ["ar", "en"] as const) {
    it(`${locale}: every QR page text exists and the book's messages carry its code`, () => {
      const all = JSON.parse(source(`messages/${locale}.json`)) as Record<string, Record<string, string>>;
      const hello = all.hello!;
      for (const key of [
        "title",
        "lead",
        "metaDescription",
        "yourBook",
        "bookFor",
        "bookCode",
        "thanks",
        "orderTitle",
        "orderAnother",
        "orderCopy",
        "followTitle",
        "siteTitle",
        "home",
        "allBooks",
        "whatsappHello",
        "whatsappBook",
        "whatsappCopy",
        "emailHello",
        "emailBook",
      ])
        assert.ok(hello[key]?.trim(), key);
      for (const key of ["whatsappBook", "whatsappCopy", "emailBook"]) assert.match(hello[key]!, /\{code\}/, key);
      for (const key of ["whatsappHello", "emailHello", "title", "lead"]) assert.doesNotMatch(hello[key]!, /\{code\}/);
      assert.ok(all.contact!.facebook && all.contact!.instagram);
    });
  }
});
