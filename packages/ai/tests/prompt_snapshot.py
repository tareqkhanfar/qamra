"""Every image prompt (and image-QA system prompt) an art style assembles, for golden snapshots.

The art-style guides and the house style are merged into many prompts: the character sheet, every page
and cover of a book, the companion and family-member sheets, the Classic placeholder and portrait, the
class-book scenes and the page QA. `assembled_prompts(style)` builds all of them for fixed children and two
themes, offline, so a change meant for one style can be proven to leave the others byte-identical.

The golden file (`fixtures/prompt_snapshots.json`) keeps a SHA-256 per prompt group (a book's pages, a
book's QA, every other prompt on its own), per style and per kept earlier guide version
(`semi-realistic.v2`); `--dump DIR` writes the texts themselves, to diff two versions. It was first taken
before «شبه حقيقي» v3 (commit 0bd49a6): the other styles' entries have not changed since. Regenerate it only
for a change that is meant to touch the prompts it guards:

    PYTHONPATH=packages/ai/tests uv run python packages/ai/tests/prompt_snapshot.py --write
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from tests_helpers import png

from qamra_ai.config import Settings
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.pipeline.book import default_companion
from qamra_ai.pipeline.character import character_request
from qamra_ai.pipeline.character import portrait_request as character_portrait_request
from qamra_ai.pipeline.classbook import Kid, load_class_template, picture_prompt
from qamra_ai.pipeline.classic import Variant, placeholder_request, portrait_request
from qamra_ai.pipeline.companion import companion_request, default_companion_request
from qamra_ai.pipeline.family_member import MemberSpec, member_request
from qamra_ai.pipeline.layout import plan_book
from qamra_ai.pipeline.models import Child, CompanionSpec, DrawingReview
from qamra_ai.pipeline.pages import BookContext, page_request, qa_request
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import history_guide, house_style
from qamra_ai.pipeline.theme import ArtStyle, art_style, load_style, load_theme

GOLDEN = Path(__file__).parent / "fixtures" / "prompt_snapshots.json"
# every style a book can be drawn in: the store's guides and the legacy media of content/styles/styles.yaml
STYLES = ("3d", "watercolor", "cartoon", "coloring", "crayon", "papercut", "semi-realistic")
# earlier guide versions kept in prompts/style/history/, snapshotted as "<slug>.v<version>". The
# semi-realistic v2 entry proved the v2/v3 comparison drew the real v2 (commit 220c5f1); with portrait first
# (2026-10-10) the templates changed for every guide, so no kept version reproduces its old prompts any more.
HISTORY: tuple[tuple[str, int], ...] = ()


def snapshot_styles() -> dict[str, ArtStyle]:
    """golden key → art style: every current style, and every kept earlier version."""
    styles = {slug: load_style(slug) for slug in STYLES}
    for slug, version in HISTORY:
        styles[f"{slug}.v{version}"] = art_style(history_guide(slug, version))
    return styles


THEMES = ("new-sibling", "graduation")
NOTES = {"hair": "dark brown with lighter tips, swept up at the front", "eyes": "narrow when smiling"}
FACE_SHAPE = "from the top of the forehead to the chin, the face is an oval (width to length 0.79)."
CHECKS = ["Figure 3 (side view) faced two ways (the head right, the body left, the feet left)."]
CHILDREN = {
    "girl": Child(name="تالا", gender="f", age=5, glasses=True),
    "hijab": Child(name="ليان", gender="f", age=6, hijab=True),
    "boy": Child(name="آدم", gender="m", age=4),
}
IMG = png("tan")
_BEAT = re.compile(r":\d+(:redraw)?$")


def _rt() -> Runtime:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    return Runtime(settings=settings, text=None, image=FakeImageProvider())  # type: ignore[arg-type]


def _book_prompts(style: ArtStyle, out: dict[str, str]) -> None:
    rt = _rt()
    for slug in THEMES:
        theme = load_theme(slug)
        for who, child in CHILDREN.items():
            for full in (False, True):  # a new book / a book with every reference image
                companion = default_companion(theme, "ar")
                ctx = BookContext(
                    child=child,
                    lang="ar",
                    theme=theme,
                    style=style,
                    house=house_style(),
                    plan=plan_book(theme, "ar", companion_page=False),
                    character_sheet=IMG,
                    outfits={},
                    seed=11,
                    companion=companion,
                    companion_sheet=IMG if full else None,
                    cover=IMG if full else None,
                    cover_plate=IMG if full else None,
                    photo=IMG if full else None,
                    portrait=IMG if full else None,
                )
                if full and ctx.bible is not None:
                    ctx.cast_sheets = {cid: IMG for cid in ctx.bible.cast}
                tag = f"{slug}:{who}:{'full' if full else 'new'}"
                for beat in sorted(ctx.plan.beats):
                    out[f"page:{tag}:{beat}"] = page_request(rt, ctx, beat, 1).prompt
                    out[f"page:{tag}:{beat}:redraw"] = page_request(
                        rt, ctx, beat, 2, fixes=["face", "style", "outfit", "crop"]
                    ).prompt
                for beat in (0, 1):
                    system, parts = qa_request(ctx, beat, IMG)
                    texts = "\n".join(p for p in parts if isinstance(p, str))
                    out[f"qa:{tag}:{beat}"] = f"{system}\n----\n{texts}"


def assembled_prompts(style: ArtStyle) -> dict[str, str]:
    """name → the exact prompt text this style sends."""
    out: dict[str, str] = {}
    for who, child in CHILDREN.items():
        out[f"character:{who}"] = character_request(child, [IMG], style).prompt
        out[f"character:{who}:redraw"] = character_request(
            child, [IMG, IMG], style, attempt=2, fixes=["skin", "face", "hair", "age"]
        ).prompt
        # portrait first (what books send): the portrait, then the sheet painted from it
        out[f"character-portrait:{who}"] = character_portrait_request(child, [IMG], style).prompt
        out[f"character-portrait:{who}:redraw"] = character_portrait_request(
            child, [IMG], style, attempt=2, fixes=["face", "age"], note="The hair is shorter at the sides."
        ).prompt
        out[f"character:{who}:portrait-first"] = character_request(child, [IMG], style, portrait=IMG).prompt
        out[f"character:{who}:portrait-first:redraw"] = character_request(
            child, [IMG], style, attempt=2, fixes=["hair"], note="Straighter hair.", portrait=IMG
        ).prompt
        # with the likeness notes the text model writes from the photo (2026-10-19)
        out[f"character-portrait:{who}:notes"] = character_portrait_request(
            child, [IMG], style, notes=NOTES
        ).prompt
        out[f"character:{who}:portrait-first:notes"] = character_request(
            child, [IMG], style, portrait=IMG, notes=NOTES
        ).prompt
        # with the photo's measured face shape, and the sheet check's one redraw (2026-10-21)
        out[f"character-portrait:{who}:face-shape"] = character_portrait_request(
            child, [IMG], style, notes=NOTES, face_shape=FACE_SHAPE
        ).prompt
        out[f"character:{who}:portrait-first:face-shape"] = character_request(
            child, [IMG], style, portrait=IMG, notes=NOTES, face_shape=FACE_SHAPE
        ).prompt
        out[f"character:{who}:portrait-first:checked"] = character_request(
            child, [IMG], style, portrait=IMG, notes=NOTES, face_shape=FACE_SHAPE, checks=CHECKS
        ).prompt
        out[f"classic-portrait:{who}:sheet"] = portrait_request(child, style, IMG, from_sheet=True).prompt
        out[f"classic-portrait:{who}:photo"] = portrait_request(child, style, IMG, from_sheet=False).prompt
    for relation, adult, scarf in (("mom", True, True), ("grandpa", True, False), ("baby", False, False)):
        member = MemberSpec(relation=relation, adult=adult, scarf=scarf)
        out[f"family-member:{relation}"] = member_request(member, [IMG], style).prompt
    review = DrawingReview(
        safe=True,
        is_drawing=True,
        description_en="a round orange cat with three whiskers on each side and a blue tail",
        key_features=["round orange body", "three whiskers each side", "blue tail"],
        reasons=[],
    )
    spec = CompanionSpec(name="بوبو", traits="brave and kind", description_en=review.description_en)
    out["companion:drawing"] = companion_request(spec, review, IMG, style, 1).prompt
    out["companion:default"] = default_companion_request(
        "a small, round crescent-moon creature with a soft glow", style
    ).prompt
    theme = load_theme("graduation")
    for key in ("girl", "girl_hijab", "boy"):
        variant = Variant(key=key, gender="m" if key == "boy" else "f", hijab=key == "girl_hijab")
        out[f"classic-placeholder:{key}"] = placeholder_request(variant, style, theme, 5).prompt
    if style == load_style(style.slug):  # class books name their style by slug: current guides only
        template = load_class_template("graduation")
        kids = [
            Kid(
                id=f"k{i}",
                name=c.name,
                gender=c.gender,
                age=c.age,
                hijab=c.hijab,
                glasses=c.glasses,
                sheet=IMG,
            )
            for i, c in enumerate(CHILDREN.values())
        ]
        out["class:cover"] = picture_prompt(template, template.cover, kids, style.slug, kind="cover")
        for scene in template.scenes[:3]:
            out[f"class:{scene.key}"] = picture_prompt(template, scene, kids[:2], style.slug, kind="page")
    _book_prompts(style, out)
    return out


def group_of(name: str) -> str:
    """A book's pages (with their redraws) and its QA prompts are one group per book."""
    return _BEAT.sub("", name)


def snapshot(style: ArtStyle) -> dict[str, str]:
    """group → SHA-256 (16 hex) over every prompt in it, names included."""
    groups: dict[str, list[str]] = {}
    for name, text in sorted(assembled_prompts(style).items()):
        groups.setdefault(group_of(name), []).append(f"{name}\n{text}")
    return {g: hashlib.sha256("\n\0".join(v).encode("utf-8")).hexdigest()[:16] for g, v in groups.items()}


def dump(style: ArtStyle, folder: Path) -> None:
    """Every prompt as a text file, to diff two versions."""
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in assembled_prompts(style).items():
        (folder / f"{name.replace(':', '__')}.txt").write_text(text + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--write", action="store_true", help="rewrite the golden file from the current code")
    p.add_argument("--dump", type=Path, help="write every prompt as text under DIR/<style>/")
    args = p.parse_args(argv)
    styles = snapshot_styles()
    data = {key: snapshot(style) for key, style in styles.items()}
    if args.write:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if args.dump:
        for key, style in styles.items():
            dump(style, args.dump / key)
    print(f"{sum(len(v) for v in data.values())} prompt groups over {len(data)} styles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
