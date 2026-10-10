"""Every image prompt (and image-QA system prompt) an art style assembles, for golden snapshots.

The art-style guides and the house style are merged into many prompts: the character sheet, every page
and cover of a book, the companion and family-member sheets, the Classic placeholder and portrait, the
class-book scenes and the page QA. `assembled_prompts(style)` builds all of them for fixed children and two
themes, offline, so a change meant for one style can be proven to leave the others byte-identical.

The golden file (`fixtures/prompt_snapshots.json`) keeps a SHA-256 per prompt group (a book's pages, a
book's QA, every other prompt on its own); `--dump DIR` writes the texts themselves, to diff two versions.
Regenerate the golden file only for a change that is meant to touch every style:

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
from qamra_ai.pipeline.classbook import Kid, load_class_template, picture_prompt
from qamra_ai.pipeline.classic import Variant, placeholder_request, portrait_request
from qamra_ai.pipeline.companion import companion_request, default_companion_request
from qamra_ai.pipeline.family_member import MemberSpec, member_request
from qamra_ai.pipeline.layout import plan_book
from qamra_ai.pipeline.models import Child, CompanionSpec, DrawingReview
from qamra_ai.pipeline.pages import BookContext, page_request, qa_request
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import house_style
from qamra_ai.pipeline.theme import ArtStyle, load_style, load_theme

GOLDEN = Path(__file__).parent / "fixtures" / "prompt_snapshots.json"
# every style a book can be drawn in: the store's guides and the legacy media of content/styles/styles.yaml
STYLES = ("3d", "watercolor", "cartoon", "coloring", "crayon", "papercut", "semi-realistic")
THEMES = ("new-sibling", "graduation")
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
    template = load_class_template("graduation")
    kids = [
        Kid(id=f"k{i}", name=c.name, gender=c.gender, age=c.age, hijab=c.hijab, glasses=c.glasses, sheet=IMG)
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
    data = {slug: snapshot(load_style(slug)) for slug in STYLES}
    if args.write:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if args.dump:
        for slug in STYLES:
            dump(load_style(slug), args.dump / slug)
    print(f"{sum(len(v) for v in data.values())} prompt groups over {len(data)} styles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
