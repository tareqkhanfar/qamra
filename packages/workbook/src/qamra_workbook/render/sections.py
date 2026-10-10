"""Section styles: the color, icon, grayscale pattern and edge position of each section's tab.

The journey sections (Addendum 6 §4) and the «دوسية التأسيس» subjects (Addendum 5 §4) share one table, so
both books navigate the same way; «مغامراتي مع عائلتي» (Addendum 7 §4) has its own, in its adventures'
order. Tabs sit on the outer edge at a height set by `slot` (a thumb index over the book's `slots`), and
their pattern keeps them apart in black-and-white print.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SectionStyle:
    id: str
    name_ar: str
    icon: str  # a key of render.art.ICONS
    color: str  # tab and accents
    tint: str  # light backgrounds (never behind work areas that need a white page)
    deep: str  # text on the tint
    pattern: str  # a key of PATTERNS
    slot: int  # thumb-index position, 0 at the top
    slots: int = 14  # positions in this book's thumb index


# In the journey's order (content/journey/plan.yaml), so the tabs step down the edge section by section.
_TABLE = (
    ("intro", "البداية", "flag", "#E9A62B", "#FCEFD2", "#8A5A08", "sparkle"),
    ("think", "أدرّب عقلي", "brain", "#8C79C9", "#EEEAF8", "#4F4090", "diagonal"),
    ("eye-hand", "عيني تقود يدي", "eye", "#3B9E90", "#DDF1EC", "#1D625A", "dots"),
    ("listening", "أسمع وأميّز", "ear", "#4A95D3", "#E1EEFA", "#215A8C", "rings"),
    ("hand", "أدرّب يدي", "hand", "#E27D63", "#FBE5DD", "#9A3E28", "waves"),
    ("shapes-colors", "الأشكال والألوان", "shapes", "#EB9036", "#FDECD9", "#94500E", "zigzag"),
    ("patterns", "الأنماط والتسلسل", "pattern", "#5A79CF", "#E5EAF8", "#2F4390", "checks"),
    ("smart-coloring", "التلوين الذكي", "crayon", "#D96B93", "#FBE4EC", "#93294F", "backslash"),
    ("arabic", "الحروف العربية", "letter-ba", "#D9961B", "#FCEFD2", "#7E5206", "vertical"),
    ("writing", "الكتابة", "write", "#A26AB6", "#F3E7F7", "#653576", "grid"),
    ("english", "الإنجليزية", "letter-a", "#D65E54", "#F9E2DF", "#983027", "horizontal"),
    ("math", "الرياضيات", "abacus", "#5A9E6C", "#E1EFE4", "#2C6440", "plus"),
    ("games", "ألعاب التفكير", "puzzle", "#6B6ECF", "#E8E8FA", "#383B96", "diamonds"),
    ("finale", "المراجعة والشهادة", "star", "#E2A32A", "#FCEFD2", "#8A5A08", "stars"),
)
SECTIONS: dict[str, SectionStyle] = {
    row[0]: SectionStyle(*row, slot=i, slots=len(_TABLE)) for i, row in enumerate(_TABLE)
}
# «دوسية التأسيس» subjects and other names that share a journey style
ALIASES = {
    "pen": "hand",
    "thinking": "think",
    "mixed": "finale",
    "review": "finale",
    "coloring": "smart-coloring",
}
SLOTS = len(_TABLE)

# «مغامراتي مع عائلتي» (Addendum 7 §4, reordered by Tareq's decisions of 28 Sep 2026): the front pages, the
# twelve adventures in the book's order, the back pages. Cheerful and far apart on the color wheel; the
# pattern tells neighbours apart in grayscale. Names follow content/family-book/plan.yaml and may carry
# {masc/fem} variants (personalized on the page).
_FAMILY_TABLE = (
    ("front", "البِدايَةُ", "passport", "#3C468F", "#E3E6F5", "#242A63", "sparkle"),
    ("home", "بَيْتي مَدْرَسَةٌ", "home", "#F08A3E", "#FDE9D8", "#94470F", "diagonal"),
    ("market", "مُغامَرَةُ السّوقِ", "cart", "#2FA36B", "#DAF1E4", "#17643F", "dots"),
    ("chef", "{الطَّبّاخُ الصَّغيرُ/الطَّبّاخَةُ الصَّغيرَةُ}", "chef", "#E4675A", "#FBE1DD", "#962C22", "rings"),
    ("nature", "{مُسْتَكْشِفُ/مُسْتَكْشِفَةُ} الطَّبيعَةِ", "leaf", "#5DAF4A", "#E2F2DC", "#2F6A22", "vertical"),
    ("day", "يَوْمي الجَميلُ", "sun-moon", "#F2B21E", "#FDF0CC", "#855A00", "waves"),
    ("responsible", "{أَنا مَسْؤولٌ/أَنا مَسْؤولَةٌ}", "check-list", "#23A094", "#D8F0ED", "#11635B", "backslash"),
    ("feelings", "مَشاعِري", "heart", "#E4769D", "#FBE3EC", "#962A52", "checks"),
    ("talk", "{احْكِ لي/احْكي لي}", "talk", "#2E9FD6", "#DCEFFA", "#155F87", "zigzag"),
    ("jobs", "مِهَنُ عائِلَتي", "briefcase", "#8C6CCB", "#ECE6F8", "#4E3590", "grid"),
    ("shop", "مَتْجَري الصَّغيرُ", "shop", "#9BBF2E", "#EEF5D6", "#566B0A", "horizontal"),
    ("games", "لَيْلَةُ الأَلْعابِ العائِلِيَّةِ", "dice", "#4F79D9", "#E3EAFA", "#274A9C", "plus"),
    ("act", "نُمَثِّلُ وَنَحْكي", "mask", "#B45FC4", "#F3E4F6", "#6B2A7A", "diamonds"),
    ("back", "الخِتامُ", "trophy", "#D9486B", "#FAE0E6", "#8E2240", "stars"),
)
FAMILY: dict[str, SectionStyle] = {
    row[0]: SectionStyle(*row, slot=i, slots=len(_FAMILY_TABLE)) for i, row in enumerate(_FAMILY_TABLE)
}
# «دوسية التأسيس» (Addendum 5 §4): one tab per subject of the curriculum plan, in the journey's colors and
# patterns for the same kind of work, so parents navigate by subject (Arabic / Math / English / Thinking).
_FOUNDATION_TABLE = (
    ("intro", "البداية", "flag", "#E9A62B", "#FCEFD2", "#8A5A08", "sparkle"),
    ("pen", "مهارات القلم", "pencil", "#E27D63", "#FBE5DD", "#9A3E28", "waves"),
    ("arabic", "العربية", "letter-ba", "#D9961B", "#FCEFD2", "#7E5206", "vertical"),
    ("math", "الرياضيات", "abacus", "#5A9E6C", "#E1EFE4", "#2C6440", "plus"),
    ("english", "الإنجليزية", "letter-a", "#D65E54", "#F9E2DF", "#983027", "horizontal"),
    ("thinking", "التفكير والتركيز", "brain", "#8C79C9", "#EEEAF8", "#4F4090", "diagonal"),
    ("mixed", "مراجعة شاملة", "star", "#E2A32A", "#FCEFD2", "#8A5A08", "stars"),
)
FOUNDATION: dict[str, SectionStyle] = {
    row[0]: SectionStyle(*row, slot=i, slots=len(_FOUNDATION_TABLE))
    for i, row in enumerate(_FOUNDATION_TABLE)
}
# each product's table
BOOK_SECTIONS: dict[str, dict[str, SectionStyle]] = {
    "journey": SECTIONS,
    "foundation": FOUNDATION,
    "family": FAMILY,
}
TAB_H = 26.0  # mm
TAB_MARGIN = 18.0  # mm from the trim at the top and bottom of the thumb index


def tab_top(style: SectionStyle, trim_h: float, bleed: float) -> float:
    """Top of the section's tab from the page edge: the tabs step down the edge like a thumb index."""
    step = (trim_h - 2 * TAB_MARGIN - TAB_H) / (style.slots - 1)
    return bleed + TAB_MARGIN + style.slot * step


def section_style(section_id: str, product: str = "journey") -> SectionStyle:
    table = BOOK_SECTIONS.get(product, SECTIONS)
    key = ALIASES.get(section_id, section_id) if table is SECTIONS else section_id
    if key not in table:
        raise KeyError(f"no style for section {section_id!r} ({product}); add it to render.sections")
    return table[key]


# Tab patterns: white marks over the tab color, one per section, readable in grayscale. Each is drawn in a
# 6 × 6 mm tile.
PATTERNS: dict[str, str] = {
    "sparkle": '<path d="M3 1 L3.5 2.5 L5 3 L3.5 3.5 L3 5 L2.5 3.5 L1 3 L2.5 2.5 Z" fill="#fff"/>',
    "diagonal": '<path d="M-1 1 L1 -1 M0 6 L6 0 M5 7 L7 5" stroke="#fff" stroke-width="1.1"/>',
    "backslash": '<path d="M-1 5 L1 7 M0 0 L6 6 M5 -1 L7 1" stroke="#fff" stroke-width="1.1"/>',
    "dots": '<circle cx="1.5" cy="1.5" r="0.9" fill="#fff"/><circle cx="4.5" cy="4.5" r="0.9" fill="#fff"/>',
    "waves": '<path d="M0 3 Q1.5 1 3 3 T6 3" stroke="#fff" stroke-width="0.9" fill="none"/>',
    "checks": '<rect x="0" y="0" width="3" height="3" fill="#fff" opacity="0.7"/>'
    '<rect x="3" y="3" width="3" height="3" fill="#fff" opacity="0.7"/>',
    "zigzag": '<path d="M0 4 L1.5 2 L3 4 L4.5 2 L6 4" stroke="#fff" stroke-width="0.9" fill="none"/>',
    "plus": '<path d="M3 1.2 L3 4.8 M1.2 3 L4.8 3" stroke="#fff" stroke-width="0.9"/>',
    "rings": '<circle cx="3" cy="3" r="1.6" stroke="#fff" stroke-width="0.8" fill="none"/>',
    "vertical": '<path d="M1.5 0 L1.5 6 M4.5 0 L4.5 6" stroke="#fff" stroke-width="1"/>',
    "grid": '<path d="M0 0.5 L6 0.5 M0.5 0 L0.5 6" stroke="#fff" stroke-width="0.8"/>',
    "horizontal": '<path d="M0 1.5 L6 1.5 M0 4.5 L6 4.5" stroke="#fff" stroke-width="1"/>',
    "diamonds": '<path d="M3 0.8 L5.2 3 L3 5.2 L0.8 3 Z" fill="#fff" opacity="0.8"/>',
    "stars": (
        '<path d="M3 0.8 L3.6 2.3 L5.2 2.4 L4 3.4 L4.4 5 L3 4.1 L1.6 5 L2 3.4 L0.8 2.4 L2.4 2.3 Z" '
        'fill="#fff"/>'
    ),
}
