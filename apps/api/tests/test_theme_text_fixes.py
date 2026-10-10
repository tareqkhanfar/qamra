"""A tashkeel or wording fix in a theme file reaches the Classic templates on deploy without a new paid
vowelization.

`qamra seed-themes` (qamra_api.seed) makes each `qamra_ai.pipeline.vowelize.CORRECTIONS` fix in the stored
theme, its versions, and every Classic template's pinned definition and cached vowelization, which it re-keys
to the corrected words: the template stays «vowelized» (`texts_ready`), so `ensure_texts` never calls the
model, and the book prints «وَرَفَعَتِ الشَّهَادَةَ».
"""

import copy
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.classic import classic_story
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.theme import Theme, load_theme
from qamra_ai.pipeline.vowelize import TEXT_FIXES, VowelizedTexts, source_hash, sources
from qamra_api.routers.admin_classic import texts_ready
from qamra_api.seed import upsert_themes
from qamra_core.db.classic import ClassicTemplate
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.db.studio import ThemeVersion

FIXED, SLIP = "{وَرَفَعَ/وَرَفَعَتِ} الشَّهَادَةَ", "{وَرَفَعَ/وَرَفَعَتْ} الشَّهَادَةَ"


def _with_slip(definition: dict[str, Any]) -> dict[str, Any]:
    old = copy.deepcopy(definition)
    for page in old["pages"]:
        page["text_ar"] = page["text_ar"].replace(FIXED, SLIP)
    assert old != definition
    return old


async def test_the_deploy_fixes_the_cached_texts_and_keeps_them_fresh(adb: AsyncSession) -> None:
    await upsert_themes(adb)
    row = (await adb.execute(select(ThemeRow).where(ThemeRow.slug == "graduation"))).scalar_one()
    current = copy.deepcopy(row.definition)
    old = _with_slip(current)
    # the theme as it was stored before the fix, and two templates that pinned and vowelized those words
    row.definition = old
    for version in (await adb.execute(select(ThemeVersion).where(ThemeVersion.theme_id == row.id))).scalars():
        version.definition = old
    templates = []
    for variant, gender in (("girl", "f"), ("boy", "m")):
        source = sources(Theme.model_validate(old), gender)
        cache = {"hash": source_hash(source), "gender": gender, "texts": source.model_dump(), "kept": []}
        t = ClassicTemplate(
            theme_id=row.id, theme_version=row.version, art_style="watercolor", variant=variant,
            generation={"theme_def": old, "texts": cache},
        )  # fmt: skip
        adb.add(t)
        templates.append(t)
    stale = ClassicTemplate(
        theme_id=row.id, theme_version=row.version, art_style="3d", variant="girl",
        generation={"theme_def": old, "texts": {"hash": "older-words", "texts": {}}},
    )  # fmt: skip
    adb.add(stale)
    await adb.commit()
    assert all(texts_ready(t) for t in templates)

    changed = await upsert_themes(adb)  # the deploy
    assert "!graduation:watercolor:girl:texts" in changed  # her words had the slip: corrected, re-keyed
    assert "!graduation:watercolor:boy" in changed  # «وَرَفَعَ» was right: the same words, the same key
    assert "!graduation:3d:girl" in changed  # its definition only: its cache was stale already
    for t in templates:
        await adb.refresh(t)
        assert texts_ready(t), t.variant  # fresh for the corrected words: no new vowelization
        assert t.generation["theme_def"] == current
        assert t.generation["texts"]["corrected"]
    girl = VowelizedTexts.model_validate(templates[0].generation["texts"]["texts"])
    printed = " ".join(p.text for p in girl.pages)
    assert "وَرَفَعَتِ الشَّهَادَةَ" in printed and "وَرَفَعَتْ الشَّهَادَةَ" not in printed
    story = classic_story(
        Theme.model_validate(current), Child(name="أبو بكر", gender="m", age=5), "ar", "", None
    )
    assert story.title == "يوم تخرّج أبي بكر"
    await adb.refresh(stale)
    assert stale.generation["texts"] == {"hash": "older-words", "texts": {}} and not texts_ready(stale)
    await adb.refresh(row)
    assert row.definition == current
    versions = (await adb.execute(select(ThemeVersion).where(ThemeVersion.theme_id == row.id))).scalars()
    assert all(v.definition == current for v in versions)

    assert not [c for c in await upsert_themes(adb) if c.startswith("!")]  # the next deploy: nothing to do


def _before_review(definition: dict[str, Any], slug: str) -> dict[str, Any]:
    """The theme's definition as it was before the gender review of 2026-10-09 (its `TEXT_FIXES` undone)."""
    text = json.dumps(definition, ensure_ascii=False)
    for fix in (f for f in TEXT_FIXES if f.theme == slug):
        text = text.replace(
            json.dumps(fix.new, ensure_ascii=False)[1:-1], json.dumps(fix.old, ensure_ascii=False)[1:-1]
        )
    old: dict[str, Any] = json.loads(text)
    assert old != definition
    return old


async def test_the_gender_review_fixes_reach_the_templates_without_the_model(adb: AsyncSession) -> None:
    """new-sibling's «للأهل» page reads «تُطَمْئِنُهُ/تُطَمْئِنُها الحكاية بأنّ…» now, and its English «reassures
    {him/her}»; graduation's English «hugged {him/her} tight». Templates that pinned and vowelized the old
    words get the new ones on deploy, their caches stay fresh (no model call), and the books print them."""
    await upsert_themes(adb)
    templates: list[tuple[ClassicTemplate, str]] = []
    files: dict[str, dict[str, Any]] = {}
    for slug in ("new-sibling", "graduation"):
        row = (await adb.execute(select(ThemeRow).where(ThemeRow.slug == slug))).scalar_one()
        files[slug] = copy.deepcopy(row.definition)  # the theme file's words, as stored
        old = _before_review(copy.deepcopy(row.definition), slug)
        row.definition = old
        for version in (
            await adb.execute(select(ThemeVersion).where(ThemeVersion.theme_id == row.id))
        ).scalars():
            version.definition = old
        for variant, gender in (("girl", "f"), ("boy", "m")):
            source = sources(Theme.model_validate(old), gender)
            model = source.model_copy(deep=True)  # the model's vowelization of the old words
            model.lesson = model.lesson.replace("تطمئن الحكاية أنّ", "تُطَمْئِنُ الحِكايَةُ أَنَّ")
            cache = {"hash": source_hash(source), "gender": gender, "texts": model.model_dump(), "kept": []}
            t = ClassicTemplate(
                theme_id=row.id, theme_version=row.version, art_style="watercolor", variant=variant,
                generation={"theme_def": old, "texts": cache},
            )  # fmt: skip
            adb.add(t)
            templates.append((t, slug))
    await adb.commit()

    changed = await upsert_themes(adb)  # the deploy
    assert "!new-sibling:watercolor:girl:texts" in changed and "!new-sibling:watercolor:boy:texts" in changed
    assert "!graduation:watercolor:girl" in changed  # English only: the same Arabic, the same key
    for t, slug in templates:
        await adb.refresh(t)
        assert texts_ready(t), (slug, t.variant)  # fresh for the new words: no vowelization call
        current = load_theme(slug)
        assert t.generation["theme_def"] == files[slug]
        gender = "m" if t.variant == "boy" else "f"
        name = "يوسف" if gender == "m" else "ليان"
        texts = VowelizedTexts.model_validate(t.generation["texts"]["texts"])
        story = classic_story(
            Theme.model_validate(t.generation["theme_def"]),
            Child(name=name, gender=gender, age=5),
            "ar",
            "",
            texts,
        )
        if slug == "new-sibling":
            assert (
                "تُطَمْئِنُهُ الحكاية بأنّ مكانَه" if gender == "m" else "تُطَمْئِنُها الحكاية بأنّ مكانَها"
            ) in story.parents_lesson
        english = classic_story(current, Child(name="Layan", gender="f", age=5), "en", "")
        if slug == "graduation":
            assert "who hugged her tight" in english.pages[13].text
    assert not [c for c in await upsert_themes(adb) if c.startswith("!")]  # the next deploy: nothing to do
