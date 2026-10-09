/**
 * The order flow per product (lib/flows.ts), checked against docs/plans/order-flows.md §c.3 and §e:
 * `npm test` (node --test; Node strips the types, so no test library is needed).
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import {
  ACTIVITY_LINES,
  agesFor,
  asksNameEn,
  canShow,
  formatPlan,
  isArabicName,
  isLatinName,
  kindOf,
  outsideAges,
  parsePlan,
  planFor,
  progress,
  resumeAt,
  stepsFor,
  tracesName,
  type FlowState,
  type StepId,
} from "./flows.ts";

/** A flow's state: a story or an activity book for a child at some point of the flow. */
function state(patch: Partial<FlowState>): FlowState {
  const productLine = patch.productLine === undefined ? "magic" : patch.productLine;
  return {
    kind: kindOf(productLine),
    productLine,
    child: null,
    reusable: false,
    character: null,
    book: null,
    stylePreset: false,
    companionOffered: productLine === "magic",
    asksFamily: productLine === "family",
    plan: null,
    ...patch,
  };
}

const NEW_CHILD = { consent: false, photos: 0 };
const CONSENTED = { consent: true, photos: 0 };
const PHOTOGRAPHED = { consent: true, photos: 1 };

describe("stepsFor: the steps per product and child (§c.3)", () => {
  const rows: { name: string; s: Partial<FlowState>; steps: StepId[] }[] = [
    {
      name: "Classic, new child, style from the story page = 8",
      s: { productLine: "classic", child: NEW_CHILD, stylePreset: true },
      steps: ["child", "consent", "photo", "character", "story", "writing", "format", "addons"],
    },
    {
      name: "Classic, approved watercolor character = 5",
      s: { productLine: "classic", child: PHOTOGRAPHED, reusable: true },
      steps: ["child", "story", "writing", "format", "addons"],
    },
    {
      name: "Magic, new child = 11",
      s: { productLine: "magic", child: NEW_CHILD },
      steps: [
        "child",
        "consent",
        "photo",
        "style",
        "character",
        "companion",
        "story",
        "writing",
        "review",
        "format",
        "addons",
      ],
    },
    {
      name: "Magic, character ready in the chosen style = 7",
      s: { productLine: "magic", child: PHOTOGRAPHED, reusable: true },
      steps: ["child", "companion", "story", "writing", "review", "format", "addons"],
    },
    {
      name: "Magic, no child chosen yet (counts as a new child)",
      s: { productLine: "magic", child: null },
      steps: [
        "child",
        "consent",
        "photo",
        "style",
        "character",
        "companion",
        "story",
        "writing",
        "review",
        "format",
        "addons",
      ],
    },
    {
      name: "Story with the type not chosen: the type step right after the child",
      s: { productLine: null, child: PHOTOGRAPHED, companionOffered: true },
      steps: ["child", "line", "style", "character", "companion", "story", "writing", "review", "format", "addons"],
    },
    {
      name: "Story, consent given but no photo yet",
      s: { productLine: "classic", child: CONSENTED, stylePreset: true },
      steps: ["child", "photo", "character", "story", "writing", "format", "addons"],
    },
    // the style step is back for the activity books (owner, 2026-10-09): after the photo, before the drawing
    ...(["workbook", "journey", "islamic"] as const).flatMap((line) => [
      {
        name: `${line}: new child = 6`,
        s: { productLine: line, child: NEW_CHILD },
        steps: ["child", "consent", "photo", "style", "character", "summary"] as StepId[],
      },
      {
        name: `${line}: no child chosen yet = 6`,
        s: { productLine: line, child: null },
        steps: ["child", "consent", "photo", "style", "character", "summary"] as StepId[],
      },
      {
        name: `${line}: consent but no photo`,
        s: { productLine: line, child: CONSENTED },
        steps: ["child", "photo", "style", "character", "summary"] as StepId[],
      },
      {
        name: `${line}: photo but no character`,
        s: { productLine: line, child: PHOTOGRAPHED },
        steps: ["child", "style", "character", "summary"] as StepId[],
      },
      {
        name: `${line}: a usable character = 2`,
        s: { productLine: line, child: PHOTOGRAPHED, reusable: true },
        steps: ["child", "summary"] as StepId[],
      },
    ]),
    {
      name: "family: new child = 7",
      s: { productLine: "family", child: NEW_CHILD },
      steps: ["child", "consent", "photo", "style", "character", "family", "summary"],
    },
    {
      name: "family: a usable character = 3",
      s: { productLine: "family", child: PHOTOGRAPHED, reusable: true },
      steps: ["child", "family", "summary"],
    },
  ];
  for (const row of rows) {
    it(row.name, () => assert.deepEqual(stepsFor(state(row.s)), row.steps));
  }
});

describe("hard rules (§e)", () => {
  const children = [null, NEW_CHILD, CONSENTED, PHOTOGRAPHED];
  const flags = [false, true];
  const all = (lines: (string | null)[]) =>
    lines.flatMap((productLine) =>
      children.flatMap((child) =>
        flags.flatMap((reusable) =>
          flags.map((stylePreset) => state({ productLine, child, reusable, stylePreset, companionOffered: true })),
        ),
      ),
    );

  it("no line, companion, story, writing, review, format or add-ons step in an activity flow", () => {
    for (const s of all([...ACTIVITY_LINES])) {
      const steps = stepsFor({ ...s, plan: ["line", "style", "consent"] });
      for (const banned of ["line", "companion", "story", "writing", "review", "format", "addons"]) {
        assert.ok(!steps.includes(banned as StepId), `${s.productLine}: ${banned} in ${steps.join(",")}`);
      }
    }
  });

  it("an activity flow asks the style exactly when it draws, right before the character", () => {
    for (const s of all([...ACTIVITY_LINES]).map((x) => ({ ...x, stylePreset: false }))) {
      const steps = stepsFor(s);
      assert.equal(steps.includes("style"), steps.includes("character"), steps.join(","));
      if (steps.includes("style")) assert.equal(steps[steps.indexOf("style") + 1], "character", steps.join(","));
      assert.equal(steps.includes("style"), !s.reusable, `${s.productLine}: ${steps.join(",")}`);
    }
  });

  it("no summary or family step in a story flow", () => {
    for (const s of all(["classic", "magic", null])) {
      const steps = stepsFor({ ...s, asksFamily: true });
      assert.ok(!steps.includes("summary") && !steps.includes("family"), steps.join(","));
    }
  });

  it("family only for the family line", () => {
    for (const line of ACTIVITY_LINES) {
      const steps = stepsFor(state({ productLine: line, child: PHOTOGRAPHED, reusable: true }));
      assert.equal(steps.includes("family"), line === "family", line);
    }
  });

  it("ACTIVITY_LINES includes islamic and matches lib/shop.ts", () => {
    assert.ok((ACTIVITY_LINES as readonly string[]).includes("islamic"));
    const shop = readFileSync(new URL("./shop.ts", import.meta.url), "utf8");
    const list = /ACTIVITY_LINES\s*=\s*\[([^\]]*)\]/.exec(shop)?.[1] ?? "";
    assert.deepEqual(
      [...list.matchAll(/"([a-z]+)"/g)].map((m) => m[1]),
      [...ACTIVITY_LINES],
    );
  });

  it("every step of every flow can be counted", () => {
    for (const s of all([...ACTIVITY_LINES, "classic", "magic", null])) {
      const steps = stepsFor(s);
      steps.forEach((step, i) => assert.deepEqual(progress(steps, step), { n: i + 1, total: steps.length }));
    }
  });
});

describe("kindOf", () => {
  it("activity lines are activity books; the rest are stories", () => {
    for (const line of ACTIVITY_LINES) assert.equal(kindOf(line), "activity");
    for (const line of ["classic", "magic", "coloring", null]) assert.equal(kindOf(line), "story");
  });
});

describe("the plan pins the count while the parent passes steps", () => {
  it("activity: consent given, photo saved and style picked keep «n من 6»", () => {
    const start = state({ productLine: "islamic", child: NEW_CHILD });
    const plan = planFor(start, false);
    assert.equal(formatPlan(plan), "consent,photo,style,character");
    const later = [
      { child: NEW_CHILD, step: "consent", n: 2 },
      { child: CONSENTED, step: "photo", n: 3 },
      { child: PHOTOGRAPHED, step: "style", n: 4 },
      { child: PHOTOGRAPHED, step: "character", n: 5 },
    ] as const;
    for (const at of later) {
      const s = { ...start, child: at.child, plan: parsePlan(formatPlan(plan)) };
      assert.deepEqual(progress(stepsFor(s), at.step), { n: at.n, total: 6 });
    }
    // the character is approved: it is now reusable, and the review is still 6 of 6
    const done = { ...start, child: PHOTOGRAPHED, reusable: true, character: { approved: true }, plan };
    assert.deepEqual(progress(stepsFor(done), "summary"), { n: 6, total: 6 });
  });

  it("activity: «ارسموا شخصية جديدة بأسلوب آخر» pins the drawing steps although a character is ready", () => {
    const ready = state({ productLine: "journey", child: PHOTOGRAPHED, reusable: true });
    // the wizard plans the flow as if nothing were reusable; the plan holds while the ready one still exists
    const plan = planFor({ ...ready, reusable: false }, false);
    assert.equal(formatPlan(plan), "style,character");
    assert.deepEqual(stepsFor({ ...ready, plan }), ["child", "style", "character", "summary"]);
    assert.ok(canShow("style", { ...ready, plan }));
    // photos are deleted 24 hours after an approval: a new photo first
    const old = state({ productLine: "family", child: CONSENTED, reusable: true });
    const again = planFor({ ...old, reusable: false }, false);
    assert.equal(formatPlan(again), "photo,style,character");
    assert.deepEqual(stepsFor({ ...old, plan: again }), ["child", "photo", "style", "character", "family", "summary"]);
  });

  it("activity: a ready character pins `reuse` (2 steps)", () => {
    const s = state({ productLine: "workbook", child: PHOTOGRAPHED, reusable: true });
    const plan = planFor(s, false);
    assert.deepEqual(plan, ["reuse"]);
    assert.deepEqual(progress(stepsFor({ ...s, plan }), "summary"), { n: 2, total: 2 });
  });

  it("story: the type picked in the flow stays counted, and the style step too once a style is set", () => {
    const start = state({ productLine: null, child: NEW_CHILD });
    // the type is chosen (Magic, nothing preset): the style is part of the plan
    const picked = { ...start, productLine: "magic", companionOffered: true };
    const plan = planFor(picked, true);
    assert.equal(formatPlan(plan), "line,consent,photo,style,character");
    // later the URL has the drawn style (stylePreset would now read true): the style step is still counted
    const later = { ...picked, child: PHOTOGRAPHED, stylePreset: true, character: { approved: false }, plan };
    assert.deepEqual(progress(stepsFor(later), "character"), { n: 6, total: 12 });
  });

  it("parsePlan ignores unknown words", () => {
    assert.deepEqual(parsePlan("photo,x,character"), ["photo", "character"]);
    assert.deepEqual(parsePlan(null), []);
  });
});

describe("resumeAt and canShow", () => {
  const rows: { name: string; s: Partial<FlowState>; at: StepId }[] = [
    { name: "no child → child", s: { productLine: "islamic" }, at: "child" },
    { name: "activity, new child → consent", s: { productLine: "islamic", child: NEW_CHILD }, at: "consent" },
    { name: "activity, consent → photo", s: { productLine: "workbook", child: CONSENTED }, at: "photo" },
    {
      name: "activity, a saved photo and no drawing → style",
      s: { productLine: "journey", child: PHOTOGRAPHED },
      at: "style",
    },
    {
      name: "activity, drawing → character",
      s: { productLine: "journey", child: PHOTOGRAPHED, character: { approved: false } },
      at: "character",
    },
    {
      name: "activity, usable character → summary",
      s: { productLine: "islamic", child: PHOTOGRAPHED, reusable: true },
      at: "summary",
    },
    {
      name: "family, usable character → family",
      s: { productLine: "family", child: PHOTOGRAPHED, reusable: true },
      at: "family",
    },
    {
      name: "family, approved in this flow → family",
      s: { productLine: "family", child: PHOTOGRAPHED, character: { approved: true } },
      at: "family",
    },
    { name: "story, type unknown → line", s: { productLine: null, child: PHOTOGRAPHED }, at: "line" },
    { name: "story, new child → consent", s: { productLine: "classic", child: NEW_CHILD }, at: "consent" },
    { name: "story, consent → photo", s: { productLine: "classic", child: CONSENTED }, at: "photo" },
    { name: "story, photo → style", s: { productLine: "magic", child: PHOTOGRAPHED }, at: "style" },
    {
      name: "story, approved character → story",
      s: { productLine: "magic", child: PHOTOGRAPHED, reusable: true, character: { approved: true } },
      at: "story",
    },
    {
      name: "story, book drawing → writing",
      s: { productLine: "magic", child: PHOTOGRAPHED, book: { status: "generating", line: "magic" } },
      at: "writing",
    },
    {
      name: "Magic preview → review",
      s: { productLine: "magic", child: PHOTOGRAPHED, book: { status: "preview", line: "magic" } },
      at: "review",
    },
    {
      name: "Classic preview → format",
      s: { productLine: "classic", child: PHOTOGRAPHED, book: { status: "preview", line: "classic" } },
      at: "format",
    },
  ];
  for (const row of rows) {
    it(`resumeAt: ${row.name}`, () => {
      const s = state(row.s);
      assert.equal(resumeAt(s), row.at);
      assert.ok(canShow(row.at, s), `canShow(${row.at})`);
    });
  }

  it("activity flows never show the story steps, whatever the URL says", () => {
    const s = state({
      productLine: "islamic",
      child: PHOTOGRAPHED,
      reusable: true,
      character: { approved: true },
      book: { status: "preview", line: "magic" },
      companionOffered: true,
    });
    for (const step of ["line", "companion", "story", "writing", "review", "format", "addons"] as const) {
      assert.equal(canShow(step, s), false, step);
    }
    assert.ok(canShow("summary", s));
    assert.equal(canShow("family", s), false);
  });

  it("the activity style step needs the consent and a saved photo (it draws right away)", () => {
    assert.equal(canShow("style", state({ productLine: "workbook", child: CONSENTED })), false);
    assert.ok(canShow("style", state({ productLine: "workbook", child: PHOTOGRAPHED })));
    assert.equal(canShow("style", state({ productLine: "workbook", child: NEW_CHILD })), false);
  });

  it("story flows never show the summary or family steps", () => {
    const s = state({ productLine: "magic", child: PHOTOGRAPHED, reusable: true, asksFamily: true });
    assert.equal(canShow("summary", s), false);
    assert.equal(canShow("family", s), false);
  });

  it("the review step needs a usable character", () => {
    const s = state({ productLine: "workbook", child: PHOTOGRAPHED });
    assert.equal(canShow("summary", s), false);
    assert.ok(canShow("summary", { ...s, character: { approved: true } }));
  });
});

describe("progress", () => {
  it("counts a step outside the list where it falls", () => {
    const steps: StepId[] = ["child", "summary"];
    assert.deepEqual(progress(steps, "photo"), { n: 2, total: 3 });
    assert.deepEqual(progress(steps, "summary"), { n: 2, total: 2 });
  });
});

describe("the activity books' questions (mirror of GET /api/shop/workbooks/needs)", () => {
  it("English name: dawseyeh always; journey 2, 3 and the set; never family or islamic", () => {
    assert.ok(asksNameEn("workbook", { level: "kg1", volume: "1" }));
    assert.ok(!asksNameEn("journey", { stage: "1" }));
    for (const stage of ["2", "3", "set"]) assert.ok(asksNameEn("journey", { stage }), stage);
    assert.ok(!asksNameEn("family", { format: "spiral" }));
    assert.ok(!asksNameEn("islamic", { volume: "V1" }));
  });

  it("the ages per variant (§c.3)", () => {
    assert.deepEqual(agesFor("workbook", { level: "kg1" }), [4, 5]);
    assert.deepEqual(agesFor("workbook", { level: "kg2" }), [5, 6]);
    assert.deepEqual(agesFor("journey", { stage: "1" }), [3, 4]);
    assert.deepEqual(agesFor("journey", { stage: "3" }), [5, 6]);
    assert.deepEqual(agesFor("islamic", { volume: "L1" }), [4, 6]);
    assert.deepEqual(agesFor("islamic", { volume: "V4" }), [6, 8]);
    assert.deepEqual(agesFor("islamic", { volume: "R" }), [4, 8]);
    assert.deepEqual(agesFor("family", {}), [3, 7]);
    assert.equal(agesFor("magic", {}), null);
  });

  it("the age check warns outside the range only", () => {
    assert.ok(outsideAges(3, [5, 6]));
    assert.ok(!outsideAges(5, [5, 6]));
    assert.ok(!outsideAges(3, null));
  });

  it("tracing books: dawseyeh and journey", () => {
    assert.ok(tracesName("workbook") && tracesName("journey"));
    assert.ok(!tracesName("family") && !tracesName("islamic") && !tracesName("magic"));
  });

  it("names: Arabic letters for tracing, Latin letters for the English name", () => {
    for (const ok of ["ضحى", "سلمى", "نور الهدى", "مُحَمَّد", "رؤى", "لؤي", "عبد-الرحمن", "ســلمى"]) {
      assert.ok(isArabicName(ok), ok);
    }
    for (const bad of ["Adam", "ضحى2", "", "  ", "سلمى!", "-سلمى", "سارة Sara"]) assert.ok(!isArabicName(bad), bad);
    for (const ok of ["Duha", "Abdel-Rahman", "Nour Al Huda", "D'Arcy"]) assert.ok(isLatinName(ok), ok);
    for (const bad of ["ضحى", "Duha1", "", "-Duha", "Du.ha"]) assert.ok(!isLatinName(bad), bad);
  });
});
