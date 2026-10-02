"""Per-book style bible (Addendum 11 §4.1): the looks that must never drift inside one book, locked once
per book and stored in `book.generation["bible"]` (a resumed or redrawn book reuses it unchanged).

- Scene groups: every scene names an outfit key, and that key is its scene group ("day", "school",
  "sleep"). The cover's group is the main one: its pages take the cover as their outfit reference. Every
  other group keeps its locked outfit text and, once drawn, the first accepted page of the group as its
  outfit reference (`pages.generate_pages` draws those anchor pages first). A flashback page in a school
  dress no longer copies the cover's gown, and the gown never drifts on the graduation pages.
- One head covering for the whole book: the main group's option names it, so the hijab never changes color.
- The hair, the companion's design and the recurring side characters (theme `cast:`) are locked too.

Sheet images come from content files, never generated per child: `cast/<id>-<style>.png` in the theme
folder first, then the shared `content/cast/`. A theme's default companion uses `cast/companion-<style>.png`
or the shared `content/cast/<default_companion.id>-<style>.png`. Cover plates (Addendum 11 §2.1) are
`themes/<slug>/plates/<style>-<n>.png`; the book's seed picks one.
"""

import hashlib
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from qamra_ai.pipeline.models import Child, CompanionSpec
from qamra_ai.pipeline.theme import CONTENT_DIR, Outfit, Theme, cast_ids

BIBLE_VERSION = 1
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
# The parent chose a hijab but the theme's cover outfit names none: one plain color for the whole book.
DEFAULT_HIJAB = "a simple soft cream hijab neatly covering the hair"
_PLATE_NAME = re.compile(r"^(?P<style>[a-z0-9_-]+?)-(?P<n>\d+)$")


class CastLock(BaseModel):
    role: str  # how the scene text names them ("the teacher")
    description: str  # the locked look


class StyleBible(BaseModel):
    version: int = BIBLE_VERSION
    main_group: str  # the cover's scene group: its pages match the cover's outfit
    outfits: dict[str, str]  # scene group → the hero's outfit (the head covering is separate)
    hijab: str | None = None  # one head covering for the whole book; None = no hijab
    hair: Literal["hijab", "sheet"] = "sheet"  # under the hijab, or exactly as on the character sheet
    companion: str | None = None  # the companion's locked design
    cast: dict[str, CastLock] = {}
    cover_plate: str | None = None  # file name under themes/<slug>/plates/ (None: the cover is drawn whole)

    def outfit_line(self, group: str) -> str | None:
        """The group's outfit with the book's head covering, as one line (legacy `outfits` shape)."""
        outfit = self.outfits.get(group)
        if outfit is None or self.hijab is None:
            return outfit
        return f"{outfit}; {self.hijab}"

    def outfit_lines(self) -> dict[str, str]:
        return {g: line for g in self.outfits if (line := self.outfit_line(g)) is not None}

    def render_others(self, others: str | None) -> str | None:
        """`{teacher} and {classmates}` → "the teacher and the four classmates"."""
        if not others:
            return None
        return re.sub(
            r"\{([a-z][a-z0-9_]*)\}",
            lambda m: self.cast[m.group(1)].role if m.group(1) in self.cast else m.group(1),
            others,
        )

    def cast_in(self, others: str | None) -> list[str]:
        """The locked cast members a scene shows, in the order it names them."""
        return [c for c in cast_ids(others) if c in self.cast]


def main_group(theme: Theme) -> str:
    return theme.cover.outfit if theme.cover is not None else "day"


def pick_outfit(options: list[Outfit], seed: int, key: str) -> Outfit:
    """The option a book wears for one outfit key. The same choice as before the bible existed, so a book
    that was started earlier keeps its clothes."""
    return options[(seed + sum(map(ord, key))) % len(options)]


def build_bible(
    theme: Theme,
    child: Child,
    seed: int,
    *,
    style: str,
    companion: CompanionSpec | None = None,
    content_dir: Path = CONTENT_DIR,
) -> StyleBible:
    main = main_group(theme)
    chosen = {key: pick_outfit(opts, seed, key) for key, opts in sorted(theme.outfits.items()) if opts}
    hijab = None
    if child.hijab:
        cover_option = chosen.get(main)
        hijab = cover_option.hijab_en if cover_option and cover_option.hijab_en else DEFAULT_HIJAB
    plates = cover_plates(theme.slug, style, content_dir)
    return StyleBible(
        main_group=main,
        outfits={k: (o.en_f if child.gender == "f" and o.en_f else o.en) for k, o in chosen.items()},
        hijab=hijab,
        hair="hijab" if child.hijab else "sheet",
        companion=(" ".join(companion.description_en.split()) or None) if companion else None,
        cast={
            m.id: CastLock(role=m.role, description=" ".join(m.description_en.split())) for m in theme.cast
        },
        cover_plate=plates[seed % len(plates)].name if plates else None,
    )


# ---- content files -----------------------------------------------------------------------------


def _first_image(base: Path) -> Path | None:
    return next((p for ext in IMAGE_EXTS if (p := base.parent / f"{base.name}{ext}").is_file()), None)


def sheet_file(
    theme: str, sheet_id: str, style: str, *, shared_id: str | None = None, content_dir: Path = CONTENT_DIR
) -> Path | None:
    """A fixed sheet image: the theme's own `cast/<id>-<style>.*`, else the shared `content/cast/`."""
    own = _first_image(content_dir / "themes" / theme / "cast" / f"{sheet_id}-{style}")
    if own is not None:
        return own
    return _first_image(content_dir / "cast" / f"{shared_id or sheet_id}-{style}")


def cover_plates(theme: str, style: str, content_dir: Path = CONTENT_DIR) -> list[Path]:
    """`themes/<slug>/plates/<style>-<n>.*`, in number order."""
    folder = content_dir / "themes" / theme / "plates"
    if not folder.is_dir():
        return []
    found: list[tuple[int, Path]] = []
    for path in folder.iterdir():
        m = _PLATE_NAME.match(path.stem)
        if path.suffix.lower() in IMAGE_EXTS and m and m.group("style") == style:
            found.append((int(m.group("n")), path))
    return [p for _, p in sorted(found)]


def plate_file(theme: str, name: str, content_dir: Path = CONTENT_DIR) -> Path | None:
    path = content_dir / "themes" / theme / "plates" / name
    return path if path.is_file() and path.name == name else None


def companion_sheet_key(*, model: str, style: str, house_version: str, description: str, prompt: str) -> str:
    """Cache key of a companion sheet drawn from its description: one per model, style, house style and
    exact design, shared by every book and theme that uses it (the plate store holds it)."""
    slug = re.sub(r"[^a-z0-9.-]+", "-", model.lower()).strip("-")
    digest = hashlib.sha256(f"{prompt}\n{description}".encode()).hexdigest()[:16]
    return f"sheets/{slug}/{style}/h{house_version}/companion-{digest}.png"
