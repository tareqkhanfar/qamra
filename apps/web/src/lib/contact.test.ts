/**
 * How to reach Qamra (lib/contact.ts): the admin's settings with the brand's own details as the fallback, and the
 * links a tap opens (the QR page writes the book's code into the WhatsApp message and the email subject).
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  CONTACT_DEFAULTS,
  contactFrom,
  contactItems,
  mailtoLink,
  socialHandle,
  telLink,
  whatsappLink,
} from "./contact.ts";

describe("contactFrom", () => {
  it("falls back to the brand's details when the settings are missing or empty", () => {
    assert.deepEqual(contactFrom(null), CONTACT_DEFAULTS);
    assert.deepEqual(contactFrom({ support_whatsapp: "  ", support_email: "" }), CONTACT_DEFAULTS);
    assert.equal(CONTACT_DEFAULTS.phone, "+970595870228");
    assert.equal(CONTACT_DEFAULTS.whatsapp, "+972595870228");
    assert.equal(CONTACT_DEFAULTS.email, "info@qamra.app");
    assert.equal(CONTACT_DEFAULTS.instagram, "https://www.instagram.com/qamra.app/");
    assert.equal(CONTACT_DEFAULTS.facebook, "https://www.facebook.com/qamrabooks");
  });

  it("uses the admin's own values", () => {
    const c = contactFrom({ support_email: "hello@example.org", support_phone: "+970599000000" });
    assert.equal(c.email, "hello@example.org");
    assert.equal(c.phone, "+970599000000");
    assert.equal(c.whatsapp, CONTACT_DEFAULTS.whatsapp);
  });
});

describe("the links", () => {
  it("WhatsApp: digits only, with the first message written (and the book's code in it)", () => {
    assert.equal(whatsappLink("+972595870228"), "https://wa.me/972595870228");
    const text = "مرحبًا قمرة، نودّ طلب نسخة إضافية من كتابنا (رمز الكتاب: QB-7K4M2).";
    const href = whatsappLink("+972 59 587 0228", text);
    assert.ok(href.startsWith("https://wa.me/972595870228?text="));
    assert.equal(decodeURIComponent(new URL(href).search.slice("?text=".length)), text);
    assert.equal(new URL(href).searchParams.get("text"), text);
    assert.ok(href.includes("QB-7K4M2"));
    assert.ok(!href.includes(" ")); // fully encoded
  });

  it("email: a subject with the code, spaces as %20 (never +)", () => {
    assert.equal(mailtoLink("info@qamra.app"), "mailto:info@qamra.app");
    const href = mailtoLink("info@qamra.app", "Question about book QB-7K4M2");
    assert.equal(href, "mailto:info@qamra.app?subject=Question%20about%20book%20QB-7K4M2");
    const ar = mailtoLink("info@qamra.app", "سؤال عن كتاب (رمز الكتاب: QB-7K4M2)");
    assert.equal(decodeURIComponent(ar.split("?subject=")[1]!), "سؤال عن كتاب (رمز الكتاب: QB-7K4M2)");
  });

  it("phone and the social handles", () => {
    assert.equal(telLink("+970595870228"), "tel:+970595870228");
    assert.equal(socialHandle("https://www.instagram.com/qamra.app/"), "@qamra.app");
    assert.equal(socialHandle("https://www.facebook.com/qamrabooks"), "@qamrabooks");
    assert.equal(socialHandle("not a url"), "");
  });
});

describe("contactItems", () => {
  it("the phone, WhatsApp and the email; Facebook and Instagram with `social`", () => {
    const keys = (s?: boolean | "only") => contactItems(CONTACT_DEFAULTS, { social: s }).map((i) => i.key);
    assert.deepEqual(keys(), ["phone", "whatsapp", "email"]);
    assert.deepEqual(keys(true), ["phone", "whatsapp", "email", "facebook", "instagram"]);
    assert.deepEqual(keys("only"), ["facebook", "instagram"]);
    const all = contactItems(CONTACT_DEFAULTS, { social: true });
    assert.deepEqual(
      all.map((i) => i.href),
      [
        "tel:+970595870228",
        "https://wa.me/972595870228",
        "mailto:info@qamra.app",
        "https://www.facebook.com/qamrabooks",
        "https://www.instagram.com/qamra.app/",
      ],
    );
    assert.equal(all.find((i) => i.key === "instagram")!.value, "@qamra.app");
  });

  it("the QR page's code goes into the WhatsApp message and the email subject, and nowhere without one", () => {
    const withCode = contactItems(CONTACT_DEFAULTS, {
      whatsappText: "Hello Qamra, I have a question about our book (book code: QB-7K4M2).",
      emailSubject: "A question about a Qamra book (book code: QB-7K4M2)",
    });
    assert.ok(withCode.find((i) => i.key === "whatsapp")!.href.includes("QB-7K4M2"));
    assert.ok(withCode.find((i) => i.key === "email")!.href.includes("QB-7K4M2"));
    const plain = contactItems(CONTACT_DEFAULTS, { social: true, whatsappText: "Hello Qamra, I have a question." });
    assert.ok(plain.every((i) => !i.href.includes("QB-")));
  });
});
