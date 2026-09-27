"""Fixed book copy per language (brand name always comes from config)."""

STRINGS: dict[str, dict[str, str]] = {
    "ar": {
        "keepsake_title": "وَهٰكَذا وُلِدَ صاحِبي",
        "drawing_label": "رَسْمَةُ {name}",
        "companion_label": "{companion} في الكِتاب",
        "keepsake_note": "رَسَمَهُ {name} بِيَدَيْهِ… وَصارَ بَطَلًا في حِكايَتِهِ.",
        "keepsake_note_f": "رَسَمَتْهُ {name} بِيَدَيْها… وَصارَ بَطَلًا في حِكايَتِها.",
        "watermark": "مُعايَنَة · {brand}",
        "dedication_label": "إهداء",
        "made_by": "صُنِعَ بِحُبٍّ في {brand}",
    },
    "en": {
        "keepsake_title": "And that's how my friend was born",
        "drawing_label": "Drawn by {name}",
        "companion_label": "{companion} in the book",
        "keepsake_note": "Drawn by {name}'s own hands… now a hero in the story.",
        "keepsake_note_f": "Drawn by {name}'s own hands… now a hero in the story.",
        "watermark": "Preview · {brand}",
        "dedication_label": "Dedication",
        "made_by": "Made with love by {brand}",
    },
}
