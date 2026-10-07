"""Web previews of the activity books (Addendum 9 WorkbookProduct; the owner's request of 2026-10-07): for
every part the store sells, its real cover and 8–10 chosen inside pages, so the product page shows the pages
of the level, volume or stage the parent picks.

    uv run python scripts/export_workbook_previews.py             # every product, from the renders in out/
    uv run python scripts/export_workbook_previews.py --render    # first render the sources that are missing
    uv run python scripts/export_workbook_previews.py --only islamic-series

Parts ("scopes"): «دوسية التأسيس» kg1-1 … kg2-3 (level × volume), «رحلتي الأولى للتعلّم» 1 2 3 (stages),
«مغامراتي مع عائلتي» book, «قلبي يعرف الله» V1 … V5 and R. A set (three volumes, three stages, L1, L2, the
five volumes) shows its parts' pages; the site combines them (apps/web/src/lib/workbook.ts).

Every page is drawn by the local page engine for its invented sample child «ليان» and her AI-drawn character
(no real child's data, no AI cost here). The sources, and the command that renders each one (`--render` runs
it when the source is missing; nothing calls a paid API):

    out/workbook/png-<level>-v<n>/          python -m qamra_workbook.render.workbook --level kg1 --volume 1
    out/journey/stage-<n>/png-book|cover/   python -m qamra_workbook.render.journey --stage 1 --book
    out/family-book/png-*-21x28/            python -m qamra_workbook.render.family --book --no-inserts
    out/islamic/web/<v>/interior|cover.pdf  python -m qamra_workbook.render.islamic_volume --volume v1 --print
                                                --name ليان --gender f --out out/islamic/web/v1
                                            (a print build needs the approvals: $QAMRA_ISLAMIC_REVIEW_FILE)

Writes apps/web/public/workbooks/<product>/<scope>/cover.webp and NN.webp (720 px wide) with a 360 px copy
(…-sm.webp) for strips and cards, and apps/web/src/lib/workbook-previews.json: product → default scope and
scopes → cover + pages, each with its size and its Arabic and English caption. URLs carry a digest of the
image (`?v=…`): /workbooks is cached for a week, so a new export must not be hidden by an old copy. A product
not exported keeps its entry (`--only`).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps/web/public/workbooks"
MANIFEST = ROOT / "apps/web/src/lib/workbook-previews.json"
WIDTH, SMALL = 720, 360  # the page in the viewer (≈2× a 360 px phone column) and in strips and cards
QUALITY = 80
BLEED_MM = 3.0  # the Islamic PDFs carry 3 mm bleed around a 210 × 280 mm page
ISLAMIC = ROOT / "out/islamic/web"
CHARACTER = ROOT / "out/samples/journey/assets"  # the sample character's standing pose, for the cover mock-up


@dataclass(frozen=True)
class Page:
    """One page: a PNG under the scope's folder (`stem`), or page `n` (from 1) of a PDF there (`x.pdf#n`)."""

    source: str
    ar: str
    en: str


@dataclass(frozen=True)
class Scope:
    key: str
    folder: Path
    cover: Page
    pages: tuple[Page, ...]
    render: tuple[str, ...]  # the engine command (module and arguments) that draws the source


def _workbook(level: str, volume: int, pages: list[tuple[str, str, str]]) -> Scope:
    """A volume of «دوسية التأسيس»: its first page (the child's own page, with the volume's title) is
    its cover."""
    kicker = {"kg1": "المستوى الأول", "kg2": "المستوى الثاني"}[level]
    return Scope(
        key=f"{level}-{volume}",
        folder=ROOT / f"out/workbook/png-{level}-v{volume}",
        cover=Page(
            "p001-owner-page",
            f"الصفحة الأولى: «هذا الكتاب لـ…» باسم طفلكم، {kicker}",
            f"The first page: “This book belongs to…” with your child's name ({level.upper()})",
        ),
        pages=tuple(Page(*p) for p in pages),
        render=("qamra_workbook.render.workbook", "--level", level, "--volume", str(volume)),
    )


def _journey(stage: int, pages: list[tuple[str, str, str]]) -> Scope:
    return Scope(
        key=str(stage),
        folder=ROOT / f"out/journey/stage-{stage}",
        cover=Page(
            "png-cover/journey-cover-front",
            "الغلاف باسم طفلكم وشخصيته",
            "The cover, with your child's name and character",
        ),
        pages=tuple(Page(f"png-book/{stem}", ar, en) for stem, ar, en in pages),
        render=("qamra_workbook.render.journey", "--stage", str(stage), "--book"),
    )


def _islamic(volume: str, pages: list[tuple[int, str, str]]) -> Scope:
    v = volume.lower()
    return Scope(
        key=volume,
        folder=ISLAMIC / v,
        cover=Page(
            "cover.pdf#1", "الغلاف باسم طفلكم وشخصيته", "The cover, with your child's name and character"
        ),
        pages=tuple(Page(f"interior.pdf#{n}", ar, en) for n, ar, en in pages),
        render=(
            "qamra_workbook.render.islamic_volume",
            *("--volume", v, "--print", "--name", "ليان", "--gender", "f"),
            *("--out", str(ISLAMIC / v)),
        ),
    )


SCOPES: dict[str, list[Scope]] = {
    # ---- «دوسية التأسيس»: KG1 (ages 4–5) and KG2 (5–6), three volumes each ----------------------------
    "foundation-workbook": [
        _workbook(
            "kg1",
            1,
            [
                (
                    "p003-name-trace",
                    "اسمي: أتتبّعه بحروف منقّطة كبيرة",
                    "My name: tracing it in big dotted letters",
                ),
                (
                    "p012-unit-opener",
                    "أبدأ رحلة الحروف مع شخصيتي",
                    "Starting the letters' journey with my character",
                ),
                (
                    "p018-kg1-letter-trace",
                    "أتتبّع حرف الألف من النقطة الخضراء",
                    "Tracing alif from the green dot",
                ),
                ("p033-kg1-number-intro", "العدد واحد: رقمه وكمّيته", "The number one: numeral and amount"),
                ("p040-kg1-en-letter", "A a مع كلمة apple", "A a, with the word apple"),
                (
                    "p065-kg1-cut-shadows",
                    "أقصّ كل صورة وألصقها فوق ظلّها",
                    "Cutting out each picture and pasting it on its shadow",
                ),
                ("p086-kg1-hidden-stars", "أين اختبأت النجوم؟", "Where are the stars hiding?"),
                ("p105-maze", "متاهة سهلة إلى الحديقة", "An easy maze to the garden"),
                (
                    "p114-kg1-color-by-code",
                    "ألوّن حسب الرمز: حروف وأعداد",
                    "Coloring by code: letters and numbers",
                ),
                (
                    "p116-kg1-assessment",
                    "تقييم مهارات القلم مع الأهل أو المعلّمة",
                    "The pencil-skills check, with a parent or teacher",
                ),
            ],
        ),
        _workbook(
            "kg1",
            2,
            [
                (
                    "p005-unit-opener",
                    "أتابع رحلة الحروف مع شخصيتي",
                    "Continuing the letters' journey with my character",
                ),
                ("p011-kg1-letter-trace", "أتتبّع حرف الراء", "Tracing the letter raa"),
                ("p008-number-intro-ten", "العدد ستة: رقمه وكمّيته", "The number six: numeral and amount"),
                (
                    "p029-letter-position",
                    "أين الباء في الكلمة: في أولها أم وسطها أم آخرها؟",
                    "Where is baa in the word: start, middle or end?",
                ),
                (
                    "p059-kg1-story-sequence",
                    "أرتّب القصة: بذرة ثم نبتة ثم زهرة",
                    "Putting the story in order: seed, sprout, flower",
                ),
                ("p069-kg1-inside-outside", "داخل الصندوق أم خارجه؟", "Inside the box or outside?"),
                (
                    "p082-hidden-pictures",
                    "أبحث عن خمسة أشياء مختبئة في الصورة",
                    "Finding five things hiding in the picture",
                ),
                ("p090-kg1-dot-to-dot", "أصل النقاط من 1 إلى 10", "Joining the dots from 1 to 10"),
                ("p107-kg1-en-coloring", "Color and say: P وQ وR", "Color and say: P, Q and R"),
                (
                    "p112-kg1-assessment",
                    "تقييم مهارات القلم مع الأهل أو المعلّمة",
                    "The pencil-skills check, with a parent or teacher",
                ),
            ],
        ),
        _workbook(
            "kg1",
            3,
            [
                ("p012-kg1-vocab-unit", "Numbers: من one إلى five", "Numbers: one to five"),
                (
                    "p015-number-train",
                    "قطار الأعداد: أكمل العدد الناقص",
                    "The number train: filling in the missing number",
                ),
                ("p032-kg1-picture-add", "أجمع بالصور", "Adding with pictures"),
                (
                    "p059-cut-and-paste",
                    "أقصّ القطع وأركّب الصورة",
                    "Cutting out the pieces and building the picture",
                ),
                (
                    "p082-kg1-self-portrait",
                    "أرسم نفسي وأصدقائي في الروضة",
                    "Drawing myself and my friends at kindergarten",
                ),
                (
                    "p087-unit-opener",
                    "أبدأ مع شخصيتي: أسمع حركات الحروف",
                    "Starting with my character: hearing the short vowels",
                ),
                (
                    "p090-kg1-harakat",
                    "أسمع الفتحة وأراها فوق الحرف",
                    "Hearing the fatha and seeing it on a letter",
                ),
                ("p103-kg1-word-write", "أتتبّع كلمتين قصيرتين", "Tracing two short words"),
                (
                    "p109-kg1-assessment",
                    "تقييم مهارات القلم مع الأهل أو المعلّمة",
                    "The pencil-skills check, with a parent or teacher",
                ),
                (
                    "p114-workbook-certificate",
                    "شهادة إنجاز باسم طفلكم وصورة شخصيته",
                    "A certificate with your child's name and character",
                ),
            ],
        ),
        _workbook(
            "kg2",
            1,
            [
                (
                    "p002-name-trace",
                    "اسمي: أتتبّعه ثم أكتبه وحدي",
                    "My name: tracing it, then writing it on my own",
                ),
                ("p008-unit-opener", "أنا وعالم الأرقام", "Me and the world of numbers"),
                ("p019-letter-trace", "أتتبّع حرف الألف: الكبير ثم الأصغر", "Tracing alif: big, then smaller"),
                (
                    "p029-en-letter",
                    "A a: أتتبّعه وأكتبه وألوّن صورة apple",
                    "A a: tracing it, writing it, coloring the apple",
                ),
                (
                    "p033-number-intro",
                    "العدد واحد: رقمه وكمّيته واسمه",
                    "The number one: numeral, amount and name",
                ),
                ("p050-dot-to-dot", "أصل النقاط من 1 إلى 10", "Joining the dots from 1 to 10"),
                (
                    "p085-cut-and-paste",
                    "أقصّ القطع وألصقها لأكمل الصورة",
                    "Cutting and pasting the pieces to finish the picture",
                ),
                ("p095-maze", "متاهة: أوصل القطة إلى الكرة", "A maze: getting the cat to the ball"),
                (
                    "p110-symmetry-drawing",
                    "أكمل النصف الناقص من الرسم",
                    "Finishing the missing half of the drawing",
                ),
                (
                    "p124-assessment",
                    "تقييم مهارات القلم مع الأهل أو المعلّمة",
                    "The pencil-skills check, with a parent or teacher",
                ),
            ],
        ),
        _workbook(
            "kg2",
            2,
            [
                ("p006-unit-opener", "أنا والحروف من جديد", "Me and the letters, once more"),
                (
                    "p007-letter-position",
                    "الباء والتاء والثاء في أول الكلمة ووسطها وآخرها",
                    "Baa, taa and thaa at the start, middle and end",
                ),
                (
                    "p009-number-intro-ten",
                    "العدد ستة: رقمه وكمّيته واسمه",
                    "The number six: numeral, amount and name",
                ),
                (
                    "p018-classify-category",
                    "أصنّف الصور في ثلاث مجموعات",
                    "Sorting pictures into three groups",
                ),
                ("p049-letter-dot-to-dot", "أصل النقاط بترتيب الحروف", "Joining the dots in alphabet order"),
                ("p051-hidden-pictures", "أبحث عن خمسة أشياء مخفية", "Finding five hidden things"),
                ("p056-place-words", "فوق وتحت، داخل وخارج", "Above and below, inside and outside"),
                ("p083-story-sequence", "أرتّب القصة وألصقها", "Putting the story in order and pasting it"),
                ("p108-number-train", "قطار الأعداد من 1 إلى 10", "The number train from 1 to 10"),
                (
                    "p120-assessment",
                    "تقييم مهارات القلم مع الأهل أو المعلّمة",
                    "The pencil-skills check, with a parent or teacher",
                ),
            ],
        ),
        _workbook(
            "kg2",
            3,
            [
                (
                    "p009-teen-quantity-match",
                    "عشرة وآحاد: الأعداد 11–15 بالصور",
                    "Tens and ones: 11–15 in pictures",
                ),
                (
                    "p046-picture-add",
                    "أجمع بالصور وأكتب جملة الجمع",
                    "Adding with pictures and writing the number sentence",
                ),
                ("p067-vocab-cards", "Numbers: من one إلى ten", "Numbers: one to ten"),
                ("p074-harakat", "الفتحة: أقرأ الحروف بالفتحة", "The fatha: reading letters with it"),
                ("p087-syllables", "مقاطع قصيرة: بَ بُ بِ", "Short syllables: ba, bu, bi"),
                ("p096-cause-effect", "السبب والنتيجة", "Cause and effect"),
                (
                    "p101-word-read",
                    "أقرأ كلمات وأصلها بصورها",
                    "Reading words and matching them to their pictures",
                ),
                ("p105-build-words", "أبني الكلمة من المقاطع", "Building the word from syllables"),
                ("p118-sentence-read", "أنا أقرأ: جمل عن نفسي", "I can read: sentences about me"),
                (
                    "p130-workbook-certificate",
                    "شهادة إنجاز باسم طفلكم وصورة شخصيته",
                    "A certificate with your child's name and character",
                ),
            ],
        ),
    ],
    # ---- «رحلتي الأولى للتعلّم»: three stages -----------------------------------------------------------
    "learning-journey": [
        _journey(
            1,
            [
                ("p002-journey-map", "خريطة الرحلة باسم طفلكم", "The journey map, with your child's name"),
                ("p003-journey-opener", "أفكّر: أدرّب عقلي", "Thinking: training my mind"),
                ("p021-maze", "متاهة: الأرنب الجائع", "A maze: the hungry rabbit"),
                ("p028-listen-rows", "من يصدر هذا الصوت؟ مع رمز QR", "Who makes this sound? With a QR code"),
                (
                    "p050-shape-journey",
                    "الدائرة: أراها وأتتبّعها وأرسمها",
                    "The circle: seeing it, tracing it, drawing it",
                ),
                ("p077-smart-coloring", "تلوين ذكي: ألوّن الدوائر فقط", "Smart coloring: only the circles"),
                ("p091-draw-myself", "أرسم نفسي", "Drawing myself"),
                ("p104-quantity-first", "كم تفاحة؟", "How many apples?"),
                ("p111-spot-difference", "ثلاثة فروق", "Three differences"),
                ("p118-certificate", "شهادة المحطة الأولى", "The stage one certificate"),
            ],
        ),
        _journey(
            2,
            [
                ("p002-journey-map", "خريطة الرحلة: المحطة الثانية", "The journey map: stage two"),
                ("p004-journey-story", "كعك العيد: أرتّب القصة", "Eid cookies: putting the story in order"),
                ("p014-journey-first-sound", "الصوت الأول: أسد", "The first sound: asad (lion)"),
                (
                    "p030-journey-finger-trace",
                    "حرف الألف: أسمع صوته وأتتبّعه بإصبعي",
                    "Alif: hearing its sound and tracing it with my finger",
                ),
                ("p031-journey-letter-trace", "الألف بالقلم", "Alif with a pencil"),
                ("p070-name-trace", "اسمي: أتتبّعه حرفًا حرفًا", "My name: tracing it letter by letter"),
                ("p080-journey-en-letter", "A a: الصوت والصورة", "A a: its sound and a picture"),
                ("p103-journey-number-trace", "أتتبّع الأرقام 1–5", "Tracing the numbers 1–5"),
                ("p116-journey-hidden-picture", "أبحث في السوق", "Searching the market"),
                ("p120-certificate", "شهادة المحطة الثانية", "The stage two certificate"),
            ],
        ),
        _journey(
            3,
            [
                ("p002-journey-map", "خريطة الرحلة: المحطة الثالثة", "The journey map: stage three"),
                ("p011-journey-rhyme", "كلمات تتشابه في آخرها", "Words that rhyme"),
                ("p018-journey-color-mix", "ألوان تمتزج", "Mixing colors"),
                ("p065-journey-harakat", "الفتحة", "The fatha"),
                ("p070-journey-syllables", "أركّب كلمة من مقاطعها", "Building a word from its syllables"),
                ("p071-journey-word-read", "أقرأ كلمات قصيرة", "Reading short words"),
                ("p081-journey-word-write", "أكتب الكلمة على السطر", "Writing the word on the line"),
                ("p105-journey-sentence-read", "My first sentences", "My first sentences"),
                ("p109-journey-picture-sum", "أجمع بالصور", "Adding with pictures"),
                ("p120-certificate", "شهادة إتمام الرحلة", "The certificate for completing the journey"),
            ],
        ),
    ],
    # ---- «مغامراتي مع عائلتي»: one book -----------------------------------------------------------------
    "family-adventures": [
        Scope(
            key="book",
            folder=ROOT / "out/family-book",
            cover=Page(
                "png-cover-21x28/cover-21x28-cover-front",
                "الغلاف باسم طفلكم وشخصيته",
                "The cover, with your child's name and character",
            ),
            pages=tuple(
                Page(f"png-book-21x28/{stem}", ar, en)
                for stem, ar, en in [
                    ("p003-passport", "جواز سفر المغامر الصغير", "The little adventurer's passport"),
                    ("p004-my-family", "عائلتي", "My family"),
                    ("p008-scavenger-hunt", "صيد الدوائر في المطبخ", "A circle hunt in the kitchen"),
                    ("p018-shopping-list", "قائمة مشترياتي", "My shopping list"),
                    (
                        "p026-recipe-steps",
                        "ساندويش زعتر وزيت: أرتّب الخطوات",
                        "A za'atar and oil sandwich: putting the steps in order",
                    ),
                    ("p037-nature-bingo", "بنغو الطبيعة", "Nature bingo"),
                    ("p057-chore-chart", "جدول إنجازاتي", "My chore chart"),
                    ("p064-feelings-thermometer", "ميزان مشاعري", "My feelings meter"),
                    ("p096-family-game-cards", "لعبة الذاكرة مع العائلة", "A memory game with the family"),
                    (
                        "p112-certificate-family",
                        "شهادة المغامر باسم طفلكم",
                        "The adventurer's certificate, in your child's name",
                    ),
                ]
            ),
            render=("qamra_workbook.render.family", "--book", "--no-inserts"),
        ),
    ],
    # ---- «قلبي يعرف الله»: five volumes and the Ramadan and Eid book (pages by their number in the volume)
    "islamic-series": [
        _islamic(
            "V1",
            [
                (6, "بداية وحدة «الله خلقني»", "Unit opener: Allah created me"),
                (7, "قصة مع ستّي هدى وريم وسالم", "A story with Grandma Huda, Reem and Salem"),
                (22, "أبحث عن نعم الله", "Looking for Allah's blessings"),
                (33, "بداية وحدة «نبيّنا محمد ﷺ»", "Unit opener: our Prophet Muhammad ﷺ"),
                (75, "ذكر في موقف: حين أستيقظ", "A dhikr for the moment: when I wake up"),
                (102, "ماذا كنت ستفعل؟", "What would you do?"),
                (106, "ألوّن: هدية لأمّي وأبي", "Coloring: a gift for Mom and Dad"),
                (19, "صفحة للأهل في آخر الوحدة", "A page for parents at the end of the unit"),
                (118, "بطاقة رحلة الإيمان", "The faith journey card"),
                (119, "شهادة باسم طفلكم", "A certificate in your child's name"),
            ],
        ),
        _islamic(
            "V2",
            [
                (6, "بداية وحدة «لماذا نصلّي؟»", "Unit opener: why do we pray?"),
                (9, "أرتّب صلوات يومي", "Putting my day's prayers in order"),
                (
                    22,
                    "أتوضّأ كما علّمنا النبي ﷺ: أرتّب الخطوات",
                    "Wudu as the Prophet ﷺ taught: putting the steps in order",
                ),
                (31, "قصة: أتعلّم الصلاة", "A story: learning to pray"),
                (41, "ألعب الدور", "Role play"),
                (77, "دعاء لأمّي وأبي", "A dua for Mom and Dad"),
                (92, "أبحث وأجد", "Search and find"),
                (101, "ماذا أفعل لو كذبت؟", "What do I do if I tell a lie?"),
                (99, "صفحة للأهل في آخر الوحدة", "A page for parents at the end of the unit"),
                (118, "شهادة باسم طفلكم", "A certificate in your child's name"),
            ],
        ),
        _islamic(
            "V3",
            [
                (6, "بداية وحدة «الشهادتان»", "Unit opener: the two testimonies"),
                (7, "بطاقة الركن", "A pillar card"),
                (19, "صلاة الفجر خطوة خطوة", "The Fajr prayer, step by step"),
                (31, "ماذا أفعل لو نسيت الصلاة؟", "What do I do if I forget a prayer?"),
                (44, "ماذا كنت ستفعل؟ في وحدة الزكاة", "What would you do? From the zakat unit"),
                (49, "بداية وحدة «الصيام»", "Unit opener: fasting"),
                (64, "أبحث وأجد: الحج", "Search and find: Hajj"),
                (74, "أركان الإيمان: بطاقة الركن", "Pillars of faith: a pillar card"),
                (94, "ألوّن وأفرح", "Coloring with joy"),
                (110, "شهادة باسم طفلكم", "A certificate in your child's name"),
            ],
        ),
        _islamic(
            "V4",
            [
                (6, "بداية وحدة «آدم عليه السلام»", "Unit opener: Adam, peace be upon him"),
                (7, "قصة نبي تحكيها ستّي هدى", "A prophet's story told by Grandma Huda"),
                (19, "متاهة في قصة نوح عليه السلام", "A maze from the story of Nuh, peace be upon him"),
                (24, "صفحة تلوين", "A coloring page"),
                (43, "من قصة يوسف عليه السلام", "From the story of Yusuf, peace be upon him"),
                (
                    58,
                    "أبحث وأجد: قصة موسى عليه السلام",
                    "Search and find: the story of Musa, peace be upon him",
                ),
                (68, "قصة يونس عليه السلام", "The story of Yunus, peace be upon him"),
                (79, "من حياة نبيّنا ﷺ", "From the life of our Prophet ﷺ"),
                (80, "ماذا كنت ستفعل؟", "What would you do?"),
                (97, "شهادة باسم طفلكم", "A certificate in your child's name"),
            ],
        ),
        _islamic(
            "V5",
            [
                (6, "بداية وحدة «أخلاقي أكبر»", "Unit opener: my manners grow"),
                (18, "ألوّن: أرفق بالحيوان", "Coloring: being kind to animals"),
                (29, "أرتّب آداب الطعام", "Putting mealtime manners in order"),
                (36, "ألعب الدور", "Role play"),
                (50, "دعاء لوالديّ", "A dua for my parents"),
                (55, "ماذا أفعل لو قالت أمّي: لا؟", "What do I do if Mom says no?"),
                (63, "قصة من وحدة «حلال وحرام»", "A story from the halal and haram unit"),
                (73, "ماذا أفعل لو وجدت شيئًا ليس لي؟", "What do I do if I find something that isn't mine?"),
                (107, "صباحي مع الله", "My morning with Allah"),
                (119, "شهادة باسم طفلكم", "A certificate in your child's name"),
            ],
        ),
        _islamic(
            "R",
            [
                (5, "بداية وحدة «ما هو رمضان؟»", "Unit opener: what is Ramadan?"),
                (6, "قصة رمضانية", "A Ramadan story"),
                (10, "ألوّن زينة رمضان", "Coloring Ramadan decorations"),
                (19, "ذكر في موقف: عند الإفطار", "A dhikr for the moment: breaking the fast"),
                (32, "ألوّن سلّة الخير", "Coloring the basket of giving"),
                (36, "بداية وحدة «ليلة القدر»", "Unit opener: Laylat al-Qadr"),
                (45, "بداية وحدة «صباح العيد»", "Unit opener: Eid morning"),
                (53, "صباح العيد خطوة خطوة", "Eid morning, step by step"),
                (63, "متاهة العيد", "An Eid maze"),
                (71, "شهادة باسم طفلكم", "A certificate in your child's name"),
            ],
        ),
    ],
}

DEFAULT = {  # the part a product shows first (and on cards and in link previews)
    "foundation-workbook": "kg2-1",
    "learning-journey": "1",
    "family-adventures": "book",
    "islamic-series": "V1",
}


def _source(scope: Scope, page: Page) -> Path:
    name, _, n = page.source.partition("#")
    return scope.folder / (name if n else f"{name}.png")


def _image(scope: Scope, page: Page) -> Image.Image:
    """The page as an RGB image cut to its trim (a PDF page is rasterized and its bleed cut off)."""
    path = _source(scope, page)
    n = page.source.partition("#")[2]
    if not n:
        with Image.open(path) as img:
            return img.convert("RGB")
    import pypdfium2 as pdfium  # only for the Islamic series' PDFs

    pdf = pdfium.PdfDocument(str(path))
    try:
        pdf_page = pdf[int(n) - 1]
        width_mm = pdf_page.get_width() / 72 * 25.4
        trim = WIDTH * width_mm / (width_mm - 2 * BLEED_MM)  # full width so that the trimmed page is WIDTH px
        img = pdf_page.render(scale=trim / pdf_page.get_width()).to_pil().convert("RGB")
    finally:
        pdf.close()
    cut = round(img.width * BLEED_MM / width_mm)
    trimmed: Image.Image = img.crop((cut, cut, img.width - cut, img.height - cut))
    return trimmed


def _webp(img: Image.Image, width: int) -> tuple[bytes, int, int]:
    out = img.copy()
    if out.width > width:
        out = out.resize((width, round(out.height * width / out.width)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, format="WEBP", quality=QUALITY, method=6)
    return buf.getvalue(), out.width, out.height


def _export(slug: str, scope: Scope, target: Path, name: str, page: Page) -> dict[str, object]:
    img = _image(scope, page)
    big, w, h = _webp(img, WIDTH)
    small, _, _ = _webp(img, SMALL)
    (target / f"{name}.webp").write_bytes(big)
    (target / f"{name}-sm.webp").write_bytes(small)
    base = f"/workbooks/{slug}/{scope.key}/{name}"
    digest = hashlib.sha1(big + small).hexdigest()[:8]  # a new export is never served from an old cache
    return {
        "src": f"{base}.webp?v={digest}",
        "sm": f"{base}-sm.webp?v={digest}",
        "w": w,
        "h": h,
        "title_ar": page.ar,
        "title_en": page.en,
    }


def _missing(scope: Scope) -> list[Path]:
    return [p for p in (_source(scope, x) for x in (scope.cover, *scope.pages)) if not p.exists()]


def render_missing(slugs: list[str]) -> None:
    """Run the engine for every scope whose sources are missing (local rendering only)."""
    for slug in slugs:
        for scope in SCOPES[slug]:
            if _missing(scope):
                print(f"{slug}/{scope.key}: rendering ({' '.join(scope.render)})", flush=True)
                subprocess.run(
                    [sys.executable, "-m", *scope.render], cwd=ROOT, check=True, env=os.environ.copy()
                )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--only", choices=list(SCOPES), help="export one product; the others keep their entries"
    )
    parser.add_argument("--render", action="store_true", help="render the sources that are missing first")
    args = parser.parse_args(argv)
    slugs = [args.only] if args.only else list(SCOPES)
    if args.render:
        render_missing(slugs)
    missing = {f"{s}/{c.key}": _missing(c) for s in slugs for c in SCOPES[s] if _missing(c)}
    if missing:
        for key, paths in missing.items():
            print(f"{key}: missing {', '.join(str(p.relative_to(ROOT)) for p in paths[:3])}", file=sys.stderr)
        raise SystemExit("sources are missing: render them first (--render)")

    listing: dict[str, object] = json.loads(MANIFEST.read_text()) if args.only and MANIFEST.exists() else {}
    for slug in slugs:
        product = OUT / slug
        if product.exists():
            shutil.rmtree(product)  # the old flat previews and any part no longer sold
        scopes: dict[str, object] = {}
        for scope in SCOPES[slug]:
            target = product / scope.key
            target.mkdir(parents=True)
            cover = _export(slug, scope, target, "cover", scope.cover)
            pages = [_export(slug, scope, target, f"{n:02d}", p) for n, p in enumerate(scope.pages, start=1)]
            scopes[scope.key] = {"cover": cover, "pages": pages}
            print(f"{slug}/{scope.key}: cover + {len(pages)} pages", flush=True)
        listing[slug] = {"default": DEFAULT[slug], "scopes": scopes}
    for stale in ("foundation-workbook-kg1", "foundation-workbook-v3"):  # the old per-volume folders
        listing.pop(stale, None)
        shutil.rmtree(OUT / stale, ignore_errors=True)
    ordered = {slug: listing[slug] for slug in SCOPES if slug in listing}
    MANIFEST.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n")
    # the newest cut-out of the sample character (older ones stay in the cache under their own digest)
    pose = max(CHARACTER.glob("character-*-pose1.png"), key=lambda p: p.stat().st_mtime, default=None)
    if pose is not None and args.only is None:
        with Image.open(pose) as img:
            rgba = img.convert("RGBA")
        rgba.thumbnail((320, 640), Image.Resampling.LANCZOS)
        rgba.save(OUT / "character.webp", format="WEBP", quality=85, method=6)
    total = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"apps/web/public/workbooks: {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
