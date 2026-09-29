"""«مغامراتي مع عائلتي» pages for talking and feeling (Addendum 7 §4.5, §4.6, §4.9, §4.12): picture talk
(before and after, a big scene to describe, speech bubbles to fill, role play), feelings faces, which
feeling fits a situation, finish the story or the sentence, and the interview template.

The feelings pages keep a gentle tone (A7 §9): every feeling is named without judging, there is never one
right answer about how someone feels, and no page diagnoses anything.
"""

from __future__ import annotations

from typing import Any

from markupsafe import Markup

from qamra_workbook.render import draw, people
from qamra_workbook.render.pages.family import family_of, uri
from qamra_workbook.render.pages.family_day import scene
from qamra_workbook.render.pages.motor import nested_picture
from qamra_workbook.render.registry import Built, PageContext, page_type

FEELING_NAMES: dict[str, str] = {
    "happy": "الفرح",
    "sad": "الحزن",
    "angry": "الغضب",
    "scared": "الخوف",
    "missing": "الاشتياق",
    "proud": "الفخر",
    "calm": "الهدوء",
    "surprised": "المفاجأة",
}


def face_svg(feeling: str, size: float = 22) -> Markup:
    kind = feeling if feeling in people.FEELING_COLORS else "happy"
    return draw.svg(size, size, people.feeling_face(kind, size / 2, size / 2, size / 2 - 0.8), "face")


def bust_svg(job: str) -> Markup:
    return draw.svg(60, people.BUST_H, people.job_bust(job, edge_mm=1.2), "bust")


def harbour() -> Markup:
    """A big scene to describe: the sea with a fishing boat, fish, the shore with a house and a tree."""
    w, h = 170.0, 92.0
    body = [
        '<defs><linearGradient id="hb-sky" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#DCEFFA"/>'
        '<stop offset="1" stop-color="#FFFFFF"/></linearGradient></defs>',
        draw.el("rect", x=0, y=0, width=w, height=h, rx=5, fill="url(#hb-sky)"),
        nested_picture("sun", 136, 4, 24),
        nested_picture("cloud", 12, 6, 22),
        nested_picture("cloud", 84, 2, 18),
        draw.el("path", d=f"M0 52 C30 48 60 56 95 52 L95 {h} L0 {h} Z", fill="#8EC1EC"),
        draw.el("path", d=f"M92 50 C112 44 140 46 {w} 50 L{w} {h} L92 {h} Z", fill="#F3DDB0"),
        nested_picture("boat", 22, 26, 36),
        nested_picture("fish", 10, 66, 16),
        nested_picture("fish", 56, 72, 14),
        nested_picture("house", 118, 22, 34),
        nested_picture("tree", 96, 20, 28),
        nested_picture("bird", 64, 14, 12),
        nested_picture("cat", 146, 58, 16),
    ]
    for x in (8, 40, 72):
        body.append(draw.path(f"M{x} 60 q4 -3 8 0 q4 3 8 0", stroke="#FFFFFF", width=0.9))
    return draw.svg(w, h, "".join(body), "harbour")


@page_type("picture-talk")
def picture_talk(ctx: PageContext) -> Built:
    """Talk about pictures (the grown-up listens and asks): `mode: before-after` (what happened before, what
    comes after), `scene` (describe a big picture), `bubbles` (what would they say?) or `roles` (choose a
    role and act a scene)."""
    params = ctx.page.params
    mode = str(params.get("mode", "scene"))
    problems = (
        [] if mode in ("before-after", "scene", "bubbles", "roles") else [f"no picture-talk mode {mode!r}"]
    )
    data: dict[str, Any] = {"mode": mode, "character": uri(ctx.assets.character)}
    if mode == "before-after":
        rows = [dict(r) for r in params.get("rows", [])]
        if not 2 <= len(rows) <= 3:
            problems.append(f"before-and-after shows 2–3 pictures, not {len(rows)}")
        data["rows"] = [
            {"pic": scene([str(x) for x in r.get("pictures", [])]), "text": ctx.text(str(r.get("text", "")))}
            for r in rows
        ]
        data["why"] = ctx.text("لماذا؟")
    elif mode == "scene":
        data["scene"] = harbour()
        data["questions"] = [
            {"icon": str(q.get("icon", "talk")), "text": ctx.text(str(q["text"]))}
            for q in params.get("questions", [])
        ]
        data["sentences"] = [ctx.num(i + 1) for i in range(int(params.get("sentences", 5)))]
    elif mode == "bubbles":
        who = [dict(x) for x in params.get("people", [])]
        if not 2 <= len(who) <= 4:
            problems.append(f"speech bubbles for 2–4 people, not {len(who)}")
        data["people"] = [
            {
                "art": bust_svg(str(x["job"])) if x.get("job") else face_svg(str(x.get("face", "happy")), 40),
                "label": ctx.text(str(x.get("label", ""))),
                "level": int(x.get("level", 1)),
            }
            for x in who
        ]
        data["kind"] = ctx.text(str(params.get("kind", "")))
    else:  # roles
        data["roles"] = [
            {"art": bust_svg(str(x["job"])), "label": ctx.text(str(x["label"]))}
            for x in params.get("roles", [])
        ]
        data["places"] = [ctx.text(str(x)) for x in params.get("places", [])]
        data["parts"] = [ctx.text(str(x)) for x in params.get("parts", ["البداية", "المشكلة", "الحل"])]
    return Built(data, None, problems)


# ---- feelings ----------------------------------------------------------------------------------------------


@page_type("feelings-faces")
def feelings_faces(ctx: PageContext) -> Built:
    """Faces to name and copy in the mirror: ⭐ `feelings`, ⭐⭐ `challenge` more; and the child's own
    face."""
    params = ctx.page.params
    simple = [str(f) for f in params.get("feelings", ["happy", "sad", "angry"])]
    more = [str(f) for f in params.get("challenge", ["scared", "missing", "proud"])]
    problems = [f"no face for {f!r}" for f in [*simple, *more] if f not in FEELING_NAMES]
    data = {
        "faces": [
            {"svg": face_svg(f, 40), "name": FEELING_NAMES.get(f, f), "level": 1 if f in simple else 2}
            for f in [*simple, *more]
        ],
        "mirror": ctx.text(str(params.get("mirror", "{قلّدته/قلّدتِه}"))),
        "mine": ctx.text(str(params.get("mine", "وجهي الآن"))),
    }
    return Built(data, None, problems)


@page_type("situation-feeling-match")
def situation_feeling_match(ctx: PageContext) -> Built:
    """Join each situation to a face: ⭐ the first `simple` situations, ⭐⭐ the rest. Two people may feel
    differently about the same thing, so there is no answer key."""
    params = ctx.page.params
    situations = [dict(x) for x in params.get("situations", [])]
    simple = int(params.get("simple", 3))
    problems = [] if 3 <= len(situations) <= 5 else [f"3–5 situations, not {len(situations)}"]
    faces = [str(x.get("feeling", "happy")) for x in situations]
    order = list(dict.fromkeys(faces))
    ctx.rng("faces").shuffle(order)
    data = {
        "situations": [
            {
                "pic": scene([str(p) for p in x.get("pictures", [])]),
                "text": ctx.text(str(x.get("text", ""))),
                "level": 1 if i < simple else 2,
            }
            for i, x in enumerate(situations)
        ],
        "faces": [{"svg": face_svg(f, 30), "name": FEELING_NAMES.get(f, f)} for f in order],
    }
    return Built(data, None, problems)


@page_type("story-finish")
def story_finish(ctx: PageContext) -> Built:
    """Finish it: `mode: sentences` («عندما أغضب أستطيع…», a row a feeling), `mode: story` (the beginning of a
    story to read aloud, the child draws or tells the end) or `mode: problem` (a problem to solve kindly)."""
    params = ctx.page.params
    mode = str(params.get("mode", "story"))
    problems = [] if mode in ("sentences", "story", "problem") else [f"no story-finish mode {mode!r}"]
    data: dict[str, Any] = {"mode": mode, "character": uri(ctx.assets.character)}
    if mode == "sentences":
        rows = [dict(r) for r in params.get("rows", [])]
        simple = int(params.get("simple", 2))
        data["rows"] = [
            {
                "face": face_svg(str(r.get("face", "angry")), 24),
                "text": ctx.text(str(r["text"])),
                "level": 1 if i < simple else 2,
            }
            for i, r in enumerate(rows)
        ]
        if not 2 <= len(rows) <= 4:
            problems.append(f"2–4 sentences to finish, not {len(rows)}")
    else:
        story = [ctx.text(str(x)) for x in params.get("story", [])]
        if not 1 <= len(story) <= 4:
            problems.append(f"the story's beginning has 1–4 sentences, not {len(story)}")
        data["story"] = story
        data["panels"] = [scene([str(p) for p in x.get("pictures", [])]) for x in params.get("panels", [])]
        data["end"] = ctx.text(str(params.get("end", "النهاية كما {أتخيّلها/أتخيّلها}")))
        data["second"] = ctx.text(str(params.get("second", "نهاية ثانية")))
        data["feel"] = [
            {"name": ctx.text(str(x)), "faces": [face_svg(f, 13) for f in ("sad", "angry", "happy")]}
            for x in params.get("feel", [])
        ]
    return Built(data, None, problems)


# ---- the interview -----------------------------------------------------------------------------------------


@page_type("interview-template")
def interview_template(ctx: PageContext) -> Built:
    """The child interviews a grown-up about their work: ⭐ questions, then ⭐⭐ ones, each with room to draw
    or write the answer, and a portrait of the person interviewed."""
    params = ctx.page.params
    problems: list[str] = []
    family_of(ctx, problems)
    questions = [dict(q) for q in params.get("questions", [])]
    if not 3 <= len(questions) <= 6:
        problems.append(f"an interview has 3–6 questions, not {len(questions)}")
    data = {
        "who": ctx.text(str(params.get("who", "{adult}"))),
        "questions": [
            {
                "text": ctx.text(str(q["text"])),
                "icon": str(q.get("icon", "talk")),
                "level": int(q.get("level", 1)),
                "n": ctx.num(i + 1),
            }
            for i, q in enumerate(questions)
        ],
        "reporter": ctx.text("{الصحفي/الصحفية}: {child}"),
    }
    return Built(data, None, problems)
