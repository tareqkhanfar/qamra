"""«كتاب الصف» (Addendum 1 §2): the class template, a fair plan of who appears where, and the drawings.

- A class template (`content/class-books/<theme>.yaml`) lists shared scenes with a number of child places.
  Core scenes are always in the book; `extra` scenes join only when the class needs more places.
- The plan gives every child exactly `min_each` appearances (the school may raise it), spread over the book,
  never twice on one page, with the pages as evenly filled as their places allow. Places per picture are
  capped per image provider (`class_book_refs`), because models keep only a few faces consistent at once.
- A shared picture gets every child's approved character sheet as a reference and a vision check that
  looks for each child; a child who can't be found flags the page for a redraw or a human.
- Qamra Classic class books (Addendum 4 §1C) draw the shared pages once without named children: the children
  are on their personal cover, their portrait page and the class group page.
"""

import asyncio
import random
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from qamra_ai import prompts
from qamra_ai.errors import ContentBlocked, InvalidOutput, ProviderConfigError, ProviderError, QamraError
from qamra_ai.image.base import GeneratedImage, ImageRequest, RefImage, Resolution, sniff_mime
from qamra_ai.pipeline.budget import BudgetExceeded
from qamra_ai.pipeline.models import Gender, Lang
from qamra_ai.pipeline.printimg import downscale, fit_exact
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import house_style, negatives
from qamra_ai.pipeline.theme import CONTENT_DIR, ArtStyle, TimeOfDay, load_style, render_template
from qamra_ai.text.base import ImagePart, UserPart

ClassLine = Literal["classic", "magic"]
DEFAULT_REFS = 3  # children per picture when the provider isn't listed in `class_book_refs`
_REPEAT = re.compile(r"#\d+$")


class ClassScene(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9_-]+$")
    scene: str  # English, for the image model
    location: str | None = None
    time: TimeOfDay = "morning"
    outfit: str = "school"
    slots: int = Field(default=3, ge=0, le=6)  # child places, before the provider cap
    extra: bool = False
    text_ar: str
    text_en: str


class ClassCover(BaseModel):
    scene: str
    location: str | None = None
    time: TimeOfDay = "morning"
    outfit: str = "school"
    subtitle_ar: str
    subtitle_en: str


class ClassTemplate(BaseModel):
    slug: str
    version: int
    title_ar: str
    title_en: str
    everyone_ar: str
    everyone_en: str
    group_title_ar: str
    group_title_en: str
    portrait_title_ar: str
    portrait_title_en: str
    teacher_title_ar: str
    teacher_title_en: str
    blurb_ar: str
    blurb_en: str
    cover: ClassCover
    portrait_lines_ar: list[str] = Field(min_length=1)
    portrait_lines_en: list[str] = Field(min_length=1)
    locations: dict[str, str] = {}
    outfits: dict[str, str] = {}
    scenes: list[ClassScene] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> "ClassTemplate":
        keys = [s.key for s in self.scenes]
        problems = [f"duplicate scene key {k!r}" for k in sorted(set(keys)) if keys.count(k) > 1]
        placed: list[ClassScene | ClassCover] = [*self.scenes, self.cover]
        for s in placed:
            if s.location and s.location not in self.locations:
                problems.append(f"unknown location {s.location!r}")
            if s.outfit not in self.outfits:
                problems.append(f"unknown outfit {s.outfit!r}")
        for s in self.scenes:
            for text in (s.text_ar, s.text_en):
                if "{names}" not in text:
                    problems.append(f"scene {s.key}: the text must name the children ({{names}})")
        if all(s.extra for s in self.scenes):
            problems.append("at least one scene must be a core scene (extra: false)")
        if problems:
            raise ValueError(f"class template {self.slug}: " + "; ".join(sorted(set(problems))))
        return self

    def scene(self, key: str) -> ClassScene:
        """The scene for a plan key; a repeated scene is keyed `name#2`."""
        base = _REPEAT.sub("", key)
        for s in self.scenes:
            if s.key == base:
                return s
        raise KeyError(f"class template {self.slug} has no scene {base!r}")

    def title(self, lang: Lang, class_name: str) -> str:
        return (self.title_ar if lang == "ar" else self.title_en).replace("{class}", class_name)

    def cover_subtitle(self, lang: Lang, class_name: str) -> str:
        text = self.cover.subtitle_ar if lang == "ar" else self.cover.subtitle_en
        return text.replace("{class}", class_name)

    def group_title(self, lang: Lang, class_name: str) -> str:
        return (self.group_title_ar if lang == "ar" else self.group_title_en).replace("{class}", class_name)

    def blurb(self, lang: Lang, class_name: str) -> str:
        return (self.blurb_ar if lang == "ar" else self.blurb_en).replace("{class}", class_name)

    def page_text(self, key: str, lang: Lang, names: Sequence[str], class_name: str) -> str:
        scene = self.scene(key)
        everyone = (self.everyone_ar if lang == "ar" else self.everyone_en).replace("{class}", class_name)
        text = scene.text_ar if lang == "ar" else scene.text_en
        who = join_names(names, lang) if names else everyone
        return text.replace("{class}", class_name).replace("{names}", who)

    def portrait_title(self, lang: Lang, gender: Gender) -> str:
        """The heading over a child's own portrait, in the child's gender: «هٰذا أَنا» / «هٰذِهِ أَنا»."""
        return render_template(
            self.portrait_title_ar if lang == "ar" else self.portrait_title_en, gender, "", ""
        )

    def portrait_line(self, lang: Lang, index: int, gender: Gender, name: str) -> str:
        lines = self.portrait_lines_ar if lang == "ar" else self.portrait_lines_en
        return render_template(lines[index % len(lines)], gender, name, "")


def join_names(names: Sequence[str], lang: Lang) -> str:
    """«يوسف وجنى وليان» / "Yusuf, Jana and Layan"."""
    if lang == "ar":
        return " و".join(names)
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def class_books_dir(content_dir: Path = CONTENT_DIR) -> Path:
    return content_dir / "class-books"


def load_class_template(slug: str, content_dir: Path = CONTENT_DIR) -> ClassTemplate:
    path = class_books_dir(content_dir) / f"{slug}.yaml"
    if not path.is_file():
        raise KeyError(f"no class book template for theme {slug!r}")
    return ClassTemplate.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def class_template_slugs(content_dir: Path = CONTENT_DIR) -> list[str]:
    """Themes that can be a class book (they have a class template)."""
    return sorted(p.stem for p in class_books_dir(content_dir).glob("*.yaml"))


def refs_per_picture(setting: str, provider: str) -> int:
    """`class_book_refs` ("fal:3, gemini:3") → how many children one picture holds for this provider."""
    for part in (setting or "").split(","):
        name, _, value = part.strip().partition(":")
        if name.strip() == provider and value.strip().isdigit():
            return max(1, min(6, int(value.strip())))
    return DEFAULT_REFS


def class_style(slug: str) -> ArtStyle:
    """A class book's art style (the store's guides and the legacy media); watercolor when it is unknown."""
    try:
        return load_style(slug)
    except KeyError:
        return load_style("watercolor")


def style_guide(slug: str) -> str:
    """The painting-medium line for an art style."""
    return class_style(slug).guide


# ---- the plan: who appears where -------------------------------------------------------------------


@dataclass(frozen=True)
class PlannedPage:
    index: int  # story order, from 1
    key: str  # scene key; "name#2" when a very large class needs a scene twice
    slots: int  # child places on this page, after the provider cap
    children: tuple[str, ...] = ()


def plan_scenes(
    template: ClassTemplate, n_children: int, min_each: int, cap: int, line: ClassLine
) -> list[tuple[str, int]]:
    """The shared pages as (scene key, places), in story order: the core scenes, then extras (in their story
    position) until there is room for everyone's appearances, then repeats as a last resort."""
    core = [s for s in template.scenes if not s.extra]
    if line == "classic" or n_children <= 0:
        return [(s.key, 0) for s in core]

    def places(s: ClassScene) -> int:
        return max(0, min(s.slots, cap))

    need = n_children * min_each
    chosen = {s.key for s in core}
    capacity = sum(places(s) for s in core)
    for s in template.scenes:
        if capacity >= need:
            break
        if s.extra and places(s):
            chosen.add(s.key)
            capacity += places(s)
    pages = [(s.key, places(s)) for s in template.scenes if s.key in chosen]
    pool = [s for s in template.scenes if s.extra and places(s)] or [s for s in core if places(s)]
    repeat = 2
    while capacity < need and pool:
        for s in pool:
            if capacity >= need:
                break
            last = max(i for i, (k, _) in enumerate(pages) if _REPEAT.sub("", k) == s.key)
            pages.insert(last + 1, (f"{s.key}#{repeat}", places(s)))
            capacity += places(s)
        repeat += 1
    return pages


def _spread(i: int) -> float:
    """Van der Corput order (0, ½, ¼, ¾…): ties go to pages spread over the whole book."""
    out, denom = 0.0, 1.0
    while i:
        denom *= 2
        out += (i & 1) / denom
        i >>= 1
    return out


def quotas(places: Sequence[int], total: int) -> list[int]:
    """How many children each page gets: `total` appearances as evenly as the places allow."""
    q = [0] * len(places)
    left = min(total, sum(places))
    while left:
        open_pages = [i for i in range(len(places)) if q[i] < places[i]]
        i = min(open_pages, key=lambda j: (q[j], _spread(j)))
        q[i] += 1
        left -= 1
    return q


def _swap_in(pages: list[list[str]], i: int, child: str) -> bool:
    """Page i can't take `child` (already there): trade places with a child on an earlier page."""
    for j in range(i - 1, -1, -1):
        if child in pages[j]:
            continue
        for k, other in enumerate(pages[j]):
            if other not in pages[i]:
                pages[j][k] = child
                pages[i].append(other)
                return True
    return False


def assign(children: Sequence[str], places: Sequence[int], min_each: int, seed: int) -> list[list[str]]:
    """Every child exactly `min_each` times (fewer only when the pages have no room), spread over the book
    and never twice on one page. Deterministic for a seed, so a re-plan is reproducible."""
    pages: list[list[str]] = [[] for _ in places]
    if not children or not places or min_each <= 0:
        return pages
    rng = random.Random(seed)  # nosec B311: page layout, not a secret
    stream: list[str] = []
    for _ in range(min_each):
        order = list(children)
        rng.shuffle(order)
        if stream and len(order) > 1 and order[0] == stream[-1]:
            order[0], order[1] = order[1], order[0]
        stream.extend(order)
    q = quotas(places, len(stream))
    pending = stream[: sum(q)]
    for i in range(len(places)):
        waiting: list[str] = []
        while len(pages[i]) < q[i] and pending:
            child = pending.pop(0)
            if child in pages[i]:
                waiting.append(child)
            else:
                pages[i].append(child)
        pending[:0] = waiting
        while len(pages[i]) < q[i] and pending and _swap_in(pages, i, pending[0]):
            pending.pop(0)
    return pages


def coverage(pages: Sequence[Sequence[str]], children: Sequence[str]) -> dict[str, int]:
    """Appearances per child on the shared pages."""
    counts = dict.fromkeys(children, 0)
    for page in pages:
        for child in page:
            if child in counts:
                counts[child] += 1
    return counts


def build_plan(
    template: ClassTemplate,
    children: Sequence[str],
    *,
    min_each: int,
    cap: int,
    line: ClassLine,
    seed: int,
) -> list[PlannedPage]:
    scenes = plan_scenes(template, len(children), min_each, cap, line)
    places = [n for _, n in scenes]
    groups = assign(children, places, min_each, seed) if line == "magic" else [[] for _ in places]
    return [
        PlannedPage(i, key, n, tuple(group))
        for i, ((key, n), group) in enumerate(zip(scenes, groups, strict=True), start=1)
    ]


# ---- the pictures ------------------------------------------------------------------------------------

LIKENESS_OK = 7  # below this a child is "not recognizable" on the page (Addendum 1: flag for regeneration)
QA_MAX_SIDE = 1024
QA_REF_MAX_SIDE = 1024
_DRAW_ERRORS = (ContentBlocked, ProviderError, ProviderConfigError, InvalidOutput)
_EXPECTED = re.compile(r"Children expected: (\d+)")


@dataclass(frozen=True)
class Kid:
    """A child in a class picture; the approved character sheet is the likeness reference."""

    id: str
    name: str
    gender: Gender
    age: int
    hijab: bool
    glasses: bool
    sheet: bytes


class ChildCheck(BaseModel):
    ref: int  # the reference image number
    found: bool
    likeness: int = Field(ge=0, le=10)


class SceneQA(BaseModel):
    """The vision check of one class picture (Haiku-class model)."""

    children: list[ChildCheck] = []
    people_count_ok: bool
    anatomy_ok: bool
    text_in_image: bool
    style_ok: bool
    safe: bool
    notes: str = ""


@dataclass
class ClassPicture:
    status: Literal["ok", "needs_review", "failed"]
    image: GeneratedImage | None = None
    qa: SceneQA | None = None
    unrecognized: list[str] = field(default_factory=list)  # child ids the check couldn't find or recognize
    flags: list[str] = field(default_factory=list)
    attempts: list[dict[str, object]] = field(default_factory=list)


def picture_prompt(
    template: ClassTemplate,
    scene: ClassScene | ClassCover,
    kids: Sequence[Kid],
    style_slug: str,
    *,
    kind: Literal["page", "cover"],
) -> str:
    h = house_style()
    return prompts.render(
        "class_scene",
        version=1,
        kind=kind,
        style=h.style,
        medium=style_guide(style_slug),
        setting=h.setting,
        scene=scene.scene,
        location=template.locations.get(scene.location) if scene.location else None,
        time=scene.time,
        children=[
            {"ref": i, "gender": k.gender, "age": k.age, "hijab": k.hijab, "glasses": k.glasses}
            for i, k in enumerate(kids, start=1)
        ],
        outfit=template.outfits[scene.outfit],
        composition=h.composition,
        safety=h.safety,
        negative=negatives(h, class_style(style_slug).negative),
    )


def picture_request(
    template: ClassTemplate,
    scene: ClassScene | ClassCover,
    kids: Sequence[Kid],
    style_slug: str,
    *,
    kind: Literal["page", "cover"],
    step: str,
    seed: int,
    resolution: Resolution,
) -> ImageRequest:
    refs = [
        RefImage(k.sheet, sniff_mime(k.sheet), f"CHILD {i}: character reference sheet (likeness)")
        for i, k in enumerate(kids, start=1)
    ]
    prompt = picture_prompt(template, scene, kids, style_slug, kind=kind)
    return ImageRequest(step=step, prompt=prompt, refs=refs, aspect="1:1", resolution=resolution, seed=seed)


def qa_request(kids: Sequence[Kid], image: bytes, scene_text: str) -> tuple[str, list[UserPart]]:
    parts: list[UserPart] = []
    for i, k in enumerate(kids, start=1):
        parts += [
            f"Image {i}: the reference sheet of child {i}.",
            ImagePart(downscale(k.sheet, QA_REF_MAX_SIDE), "image/jpeg"),
        ]
    parts += [
        f"Image {len(kids) + 1}: the picture to check.",
        ImagePart(downscale(image, QA_MAX_SIDE), "image/jpeg"),
        f"Children expected: {len(kids)}. Scene: {scene_text}",
    ]
    return prompts.render("class_scene_qa", version=1, style=house_style().style), parts


def judge(qa: SceneQA, kids: Sequence[Kid]) -> tuple[bool, list[str], list[str]]:
    """(passed, flags, unrecognized child ids). Style is a soft flag; everything else asks for a redraw."""
    by_ref = {c.ref: c for c in qa.children}
    unrecognized = []
    for i, k in enumerate(kids, start=1):
        check = by_ref.get(i)
        if check is None or not check.found or check.likeness < LIKENESS_OK:
            unrecognized.append(k.id)
    flags = [
        name
        for name, bad in (
            ("unsafe", not qa.safe),
            ("text_in_image", qa.text_in_image),
            ("anatomy", not qa.anatomy_ok),
            ("count", not qa.people_count_ok),
            ("face", bool(unrecognized)),
            ("style", not qa.style_ok),
        )
        if bad
    ]
    return not [f for f in flags if f != "style"], flags, unrecognized


def _score(
    image_ok: bool, qa: SceneQA | None, passed: bool, flags: Sequence[str], missing: int
) -> tuple[float, ...]:
    """Rank attempts: passed first, then safe, fewer hard problems, fewer unrecognized children."""
    if qa is None:
        return (0.0, 1.0, 0.0, 0.0) if image_ok else (-1.0, 0.0, 0.0, 0.0)
    hard = sum(f in flags for f in ("unsafe", "text_in_image", "anatomy", "count"))
    return (float(passed), float(qa.safe), -float(hard), -float(missing))


async def draw_picture(
    rt: Runtime,
    make_request: Callable[[int], ImageRequest],
    kids: Sequence[Kid],
    scene_text: str,
    *,
    label: str,
    first_attempt: int = 1,
    manual: bool = False,
) -> ClassPicture:
    """One class picture with the vision check and automatic redraws (`page_max_regenerations`); the best safe
    attempt is kept. A manual redraw (the school's or an admin's click) is a single new attempt."""
    out = ClassPicture(status="failed")
    best: tuple[tuple[float, ...], GeneratedImage, SceneQA | None, list[str], list[str]] | None = None
    tries = 1 if manual else 1 + max(0, rt.settings.page_max_regenerations)
    for n in range(first_attempt, first_attempt + tries):
        req = make_request(n)
        record: dict[str, object] = {"attempt": n, "seed": req.seed, "refs": len(req.refs)}
        if manual:
            record["why"] = "manual"
        out.attempts.append(record)
        try:
            image = await rt.draw(req)
        except BudgetExceeded:
            raise
        except _DRAW_ERRORS as e:
            record["error"] = f"{type(e).__name__}: {str(e)[:200]}"
            continue
        system, user = qa_request(kids, image.data, scene_text)
        try:
            qa = await rt.ask(
                step=f"qa:{label}:a{n}",
                system=system,
                user=user,
                schema=SceneQA,
                fast=True,
                kind="qa",
                max_tokens=1500,
            )
        except BudgetExceeded:
            raise
        except QamraError as e:
            record["error"] = f"QA unavailable: {type(e).__name__}"
            if best is None:
                best = (_score(True, None, False, [], 0), image, None, ["qa_unavailable"], [])
            break  # no automatic judgement: a human decides; no blind redraws
        passed, flags, unrecognized = judge(qa, kids)
        record.update(passed=passed, flags=flags, unrecognized=unrecognized)
        rank = _score(True, qa, passed, flags, len(unrecognized))
        if best is None or rank > best[0]:
            best = (rank, image, qa, flags, unrecognized)
        if passed:
            break
    if best is not None and best[2] is not None and not best[2].safe:
        best = None  # never keep an unsafe picture, even for review
        out.flags.append("unsafe")
    if best is None:
        if any("error" in a for a in out.attempts):
            out.flags.append("draw_failed")
        return out
    _, out.image, out.qa, flags, out.unrecognized = best
    out.flags = list(dict.fromkeys([*out.flags, *flags]))
    passed = out.qa is not None and not [f for f in flags if f != "style"]
    out.status = "ok" if passed else "needs_review"
    return out


async def print_version(
    rt: Runtime, data: bytes, *, label: str, px: int, dpi: int
) -> tuple[bytes, list[str]]:
    """Upscaled and fitted exactly to the print box (incl. bleed) at `dpi`."""
    flags: list[str] = []
    try:
        data = (await rt.upscale(data, step=f"upscale:{label}", target=(px, px))).data
    except BudgetExceeded:
        raise
    except QamraError:
        flags.append("upscale_fallback")  # local Lanczos instead
    return await asyncio.to_thread(fit_exact, data, (px, px), dpi=dpi), flags


# ---- offline runs ------------------------------------------------------------------------------------


def fake_scene_qa(step: str, system: str, user: list[UserPart]) -> BaseModel:
    """A passing check that finds every expected child (tests and dry runs)."""
    text = "\n".join(p for p in user if isinstance(p, str))
    match = _EXPECTED.search(text)
    n = int(match.group(1)) if match else 0
    return SceneQA(
        children=[ChildCheck(ref=i, found=True, likeness=9) for i in range(1, n + 1)],
        people_count_ok=True,
        anatomy_ok=True,
        text_in_image=False,
        style_ok=True,
        safe=True,
        notes="ok",
    )


def install_fakes(rt: Runtime) -> None:
    """Teach the offline text provider this module's check (it answers by schema name)."""
    responders = getattr(rt.text, "responders", None)
    if rt.text.name == "fake" and isinstance(responders, dict):
        responders.setdefault("SceneQA", fake_scene_qa)
