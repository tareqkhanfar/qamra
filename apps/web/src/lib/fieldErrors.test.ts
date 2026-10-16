/**
 * Arabic-keyboard phone numbers and messages under the right field (Tareq, 2026-10-16: the checkout kept answering
 * «بعض البيانات غير صحيحة» to ٠٥٩٩… and never said which field).
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, it } from "node:test";
import { checkFields, firstInvalid, onlyFields, problemTexts, serverFieldErrors } from "./fieldErrors.ts";
import { normalizePhone, toAsciiDigits } from "./phone.ts";

describe("normalizePhone (same rules as qamra_core.phone)", () => {
  const cases: [string, string][] = [
    ["0599123456", "0599123456"],
    ["٠٥٩٩١٢٣٤٥٦", "0599123456"], // Arabic-Indic
    ["۰۵۹۹۱۲۳۴۵۶", "0599123456"], // Persian
    ["٠٥٩٩-١٢٣-٤٥٦", "0599123456"],
    ["(059) 912-3456", "0599123456"],
    ["059\u{00A0}912 3456", "0599123456"],
    ["599123456", "0599123456"],
    ["+970 59 912 3456", "+970599123456"],
    ["+972 59 912 3456", "+972599123456"],
    ["00970599123456", "+970599123456"],
    ["970599123456", "+970599123456"],
    ["+٩٧٠ ٠٥٩٩ ١٢٣ ٤٥٦", "+970599123456"],
    ["\u{200E}+970599123456\u{200F}", "+970599123456"],
    ["970599123456+", "+970599123456"],
    ["02-2981234", "022981234"],
    ["+962 79 123 4567", "+962791234567"],
    ["+1 415 523 8886", "+14155238886"],
  ];
  for (const [typed, stored] of cases) it(`${typed} → ${stored}`, () => assert.equal(normalizePhone(typed), stored));
  for (const bad of ["", "abc", "1234567", "05991234", "059912345678", "+970 12", "05٩٩x123456"])
    it(`refuses ${JSON.stringify(bad)}`, () => assert.equal(normalizePhone(bad), null));
  it("turns only digits into ASCII", () => assert.equal(toAsciiDigits("سلمى ٥ سنوات ۷"), "سلمى 5 سنوات 7"));
});

describe("checkFields", () => {
  const rules = {
    name: { required: true, min: [2, "nameShort"] },
    phone: { required: "phoneMissing", phone: true },
    city: { required: "city" },
    address: { required: true, min: [5, "addressShort"] },
    count: { int: [1, 500] },
  } as const;

  it("accepts Arabic digits and a long-enough address, whatever its letters", () => {
    const values = { name: "أم ليان", phone: "٠٥٩٩١٢٣٤٥٦", city: "البيرة", address: "ضضضضضضضضض", count: "٢٥" };
    assert.deepEqual(checkFields(values, rules), {});
  });

  it("names each problem, in the form's order", () => {
    const problems = checkFields({ name: "م", phone: "٠٥٩٩", city: "", address: "بيت", count: "٦٠٠" }, rules);
    assert.deepEqual(problems, {
      name: { key: "nameShort" },
      phone: { key: "phone" },
      city: { key: "city" },
      address: { key: "addressShort" },
      count: { key: "numberMax", n: 500 },
    });
    assert.deepEqual(checkFields({ phone: "  " }, { phone: rules.phone }), { phone: { key: "phoneMissing" } });
    assert.deepEqual(checkFields({ terms: false }, { terms: { required: "terms" } }), { terms: { key: "terms" } });
  });

  it("every problem has its text in both languages", () => {
    const web = new URL("../../", import.meta.url).pathname;
    for (const locale of ["ar", "en"]) {
      const messages = JSON.parse(readFileSync(join(web, "messages", `${locale}.json`), "utf8"));
      const fields = messages.errors.fields as Record<string, string>;
      const plain = ["required", "phone", "phoneMissing", "email", "number", "choose", "city", "terms", "tooLong"];
      for (const key of [...plain, "tooShort", "nameShort", "passwordShort", "addressShort"])
        assert.ok(fields[key] && !fields[key].includes("{"), `${locale}: errors.fields.${key}`);
      for (const key of ["numberMin", "numberMax"])
        assert.ok(fields[key]?.includes("{n}"), `${locale}: errors.fields.${key} takes {n}`);
      assert.ok(messages.errors.checkFields, `${locale}: errors.checkFields`);
    }
  });

  it("turns problems into text through the translator", () => {
    const t = (key: string, v?: Record<string, number>) => `${key}${v ? `:${v.n}` : ""}`;
    assert.deepEqual(problemTexts({ a: { key: "phone" }, b: { key: "numberMin", n: 10 } }, t), {
      a: "fields.phone",
      b: "fields.numberMin:10",
    });
  });
});

describe("serverFieldErrors", () => {
  const phone = { ar: "رقم الجوال غير صحيح. اكتبوه مثل 0599123456", en: "This mobile number isn't valid." };
  const body = {
    code: "invalid_input",
    message: phone,
    details: {
      fields: ["address", "phone", "zone"],
      field_errors: {
        phone,
        address: { ar: "اكتبوا العنوان بتفصيل أكثر", en: "More detail" },
        zone: { ar: "م", en: "z" },
      },
    },
  };

  it("reads field_errors in the reader's language, with aliases", () => {
    assert.deepEqual(serverFieldErrors(body, "ar", { zone: "city" }), {
      phone: phone.ar,
      address: "اكتبوا العنوان بتفصيل أكثر",
      city: "م",
    });
    assert.equal(serverFieldErrors(body, "en").phone, phone.en);
  });

  it("falls back to the fields list with the refusal's message (older refusals)", () => {
    const old = { code: "weak_password", message: { ar: "قصيرة", en: "short" }, details: { fields: ["password"] } };
    assert.deepEqual(serverFieldErrors(old, "ar"), { password: "قصيرة" });
    assert.deepEqual(serverFieldErrors(null, "ar"), {});
    assert.deepEqual(serverFieldErrors({ code: "x", message: phone }, "ar"), {});
  });

  it("keeps the form's fields and finds the first one", () => {
    const errors = serverFieldErrors(body, "ar", { zone: "city" });
    const order = ["name", "phone", "city", "address"];
    assert.equal(firstInvalid(order, errors), "phone");
    assert.deepEqual(Object.keys(onlyFields({ ...errors, accept_terms: "x" }, order)), ["phone", "city", "address"]);
  });
});
