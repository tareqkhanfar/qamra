/**
 * A theme's book title for one child (lib/themeTitle.ts), as the API fills it (qamra_ai.pipeline.theme.fill_title):
 * the name in its case, never a brace: `npm test`.
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { fillTitle } from "./themeTitle.ts";

describe("fillTitle", () => {
  it("a genitive slot takes the genitive: «يوم تخرّج أبي بكر»", () => {
    assert.equal(fillTitle("يوم تخرّج {name:gen}", "أبو بكر", "m"), "يوم تخرّج أبي بكر");
    assert.equal(fillTitle("يوم تخرّج {name:gen}", "أبو بكر", null), "يوم تخرّج أبي بكر");
    assert.equal(fillTitle("حكاية {name:gen} الخاصة", "ذو الفقار", "m"), "حكاية ذي الفقار الخاصة");
  });

  it("any other name is the same in every slot", () => {
    assert.equal(fillTitle("يوم تخرّج {name:gen}", "سلمى", "f"), "يوم تخرّج سلمى");
    assert.equal(fillTitle("{name} في موسم الزيتون", "سلمى", null), "سلمى في موسم الزيتون");
  });

  it("a subject stays as typed, «يا» and {name:acc} take the accusative", () => {
    assert.equal(fillTitle("{name} وقارب الأحلام", "أبو بكر", "m"), "أبو بكر وقارب الأحلام");
    assert.equal(fillTitle("أحسنت يا {name}", "أبو بكر", "m"), "أحسنت يا أبا بكر");
    assert.equal(fillTitle("نحبّ {name:acc}", "أبو بكر", "m"), "نحبّ أبا بكر");
  });

  it("the gender picks a form; with none both stay, and no brace is ever left", () => {
    assert.equal(fillTitle("{name} {حارس/حارسة} النجوم", "سلمى", "f"), "سلمى حارسة النجوم");
    assert.equal(fillTitle("{name} {حارس/حارسة} النجوم", "أبو بكر", "m"), "أبو بكر حارس النجوم");
    assert.equal(fillTitle("{name} {حارس/حارسة} النجوم", "سلمى", null), "سلمى حارس/حارسة النجوم");
    for (const title of ["يوم تخرّج {name:gen}", "{name:acc}", "{name} {حارس/حارسة} النجوم"]) {
      assert.doesNotMatch(fillTitle(title, "أبو بكر", null), /[{}]/);
    }
  });
});
