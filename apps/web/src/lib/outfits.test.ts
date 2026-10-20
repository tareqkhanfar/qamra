/** «ماذا يلبس؟» (lib/outfits.ts): which outfits a child is offered, the preselected one, and the drawn swatches. */
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { initialOutfit, outfitName, outfitsFor, outfitSrc, outfitSvg, shade, type Outfits } from "./outfits.ts";

const tee = { shape: "tee" as const, top: "#F1E6CF", bottom: "#26315F", shoes: "#7A5234" };
const CATALOG: Outfits = {
  version: 1,
  default: "classic",
  outfits: [
    {
      id: "classic",
      name_ar: "الكلاسيكي",
      name_en: "Classic",
      lines: ["magic", "workbook"],
      hijab_color: "#A7BC9C",
      hijab_trim: null,
      looks: { f: { swatch: tee }, m: { swatch: tee } },
    },
    {
      id: "rose-dress",
      name_ar: "الفستان الورديّ",
      name_en: "Rose dress",
      lines: ["magic"],
      hijab_color: "#F1E6CF",
      hijab_trim: null,
      looks: { f: { swatch: { ...tee, shape: "dress", top: "#D58C98", pattern: "#FFFFFF" } } },
    },
    {
      id: "tatreez",
      name_ar: "المطرّز الفلسطيني",
      name_en: "Palestinian embroidery",
      lines: ["magic"],
      hijab_color: "#FAFAF7",
      hijab_trim: "#A8242C",
      looks: {
        f: { swatch: { ...tee, shape: "thobe", top: "#232326", pattern: "#A8242C" } },
        m: { swatch: { ...tee, shape: "vest", top: "#232326", accent: "#FFFFFF", pattern: "#A8242C" } },
      },
    },
  ],
};

describe("outfitsFor", () => {
  it("offers a girl's and a boy's outfits on the line, and none on Classic", () => {
    assert.deepEqual(
      outfitsFor(CATALOG, "f", "magic").map((o) => o.id),
      ["classic", "rose-dress", "tatreez"],
    );
    assert.deepEqual(
      outfitsFor(CATALOG, "m", "magic").map((o) => o.id),
      ["classic", "tatreez"],
    );
    assert.deepEqual(
      outfitsFor(CATALOG, "f", "workbook").map((o) => o.id),
      ["classic"],
    );
    assert.deepEqual(outfitsFor(CATALOG, "f", "classic"), []);
    assert.deepEqual(outfitsFor(null, "f", "magic"), []);
  });
});

describe("initialOutfit", () => {
  const offered = outfitsFor(CATALOG, "f", "magic");
  it("is the default for a new child", () => {
    assert.equal(initialOutfit(offered, "classic", []), "classic");
  });
  it("is the outfit of the last-approved drawing while it is offered", () => {
    const drawings = [
      { approved: true, approved_at: "2026-10-20T10:00:00Z", outfit: "tatreez" },
      { approved: true, approved_at: "2026-10-19T10:00:00Z", outfit: "rose-dress" },
      { approved: false, outfit: "classic" },
    ];
    assert.equal(initialOutfit(offered, "classic", drawings), "tatreez");
    assert.equal(initialOutfit(outfitsFor(CATALOG, "f", "workbook"), "classic", drawings), "classic");
  });
});

describe("outfitName", () => {
  it("names a drawing's outfit, the default for older drawings", () => {
    assert.equal(outfitName(CATALOG, "rose-dress", "ar"), "الفستان الورديّ");
    assert.equal(outfitName(CATALOG, undefined, "en"), "Classic");
    assert.equal(outfitName(CATALOG, "gone", "en"), null);
    assert.equal(outfitName(null, "classic", "ar"), null);
  });
});

describe("outfitSvg", () => {
  it("draws the outfit's colours, and a girl's hijab in the colour that goes with it", () => {
    const [classic, dress, tatreez] = CATALOG.outfits;
    const svg = outfitSvg(dress, "f", false);
    assert.ok(svg.startsWith("<svg") && svg.includes('fill="#D58C98"') && !svg.includes('#F1E6CF"/>'));
    assert.ok(outfitSvg(classic, "f", true).includes('fill="#A7BC9C"'));
    assert.ok(!outfitSvg(classic, "f", false).includes("#A7BC9C"));
    assert.ok(!outfitSvg(classic, "m", true).includes("#A7BC9C")); // boys: never a hijab
    assert.ok(outfitSvg(tatreez, "f", true).includes('stroke="#A8242C"'));
    assert.ok(outfitSvg(tatreez, "m", false).includes('fill="#232326"'));
    assert.ok(outfitSrc(dress, "f", false).startsWith("data:image/svg+xml;charset=utf-8,%3Csvg"));
  });
  it("never puts a value that is not a colour into the SVG", () => {
    const bad = { ...CATALOG.outfits[0], looks: { f: { swatch: { ...tee, top: '"/><script>' } } } };
    const svg = outfitSvg(bad, "f", false);
    assert.ok(!svg.includes("<script>") && svg.includes("#F1E6CF"));
  });
  it("shades colours", () => {
    assert.equal(shade("#808080", 0.5), "#404040");
    assert.equal(shade("#000000", 2), "#ffffff");
  });
});
