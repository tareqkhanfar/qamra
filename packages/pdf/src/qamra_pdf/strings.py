"""Fixed book copy per language (brand name always comes from config)."""

AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def page_count(n: int, lang: str) -> str:
    """«٢٤ صَفْحَةً» with the number's agreement (3–10: صَفَحاتٍ, 11–99: صَفْحَةً, 100+: صَفْحَةٍ), "24 pages"."""
    if lang != "ar":
        return f"{n} page" if n == 1 else f"{n} pages"
    digits = str(n).translate(AR_DIGITS)
    if n == 1:
        return "صَفْحَةٌ واحِدَةٌ"
    if n == 2:
        return "صَفْحَتانِ"
    rest = n % 100
    if 3 <= rest <= 10:
        return f"{digits} صَفَحاتٍ"
    if rest == 0 or rest in (1, 2):
        return f"{digits} صَفْحَةٍ"
    return f"{digits} صَفْحَةً"


STRINGS: dict[str, dict[str, str]] = {
    "ar": {
        "keepsake_title": "وَهٰكَذا وُلِدَ صاحِبي",
        "drawing_label": "رَسْمَتي",
        "companion_label": "{companion} في الحِكايَة",
        "keepsake_note": "رَسَمَهُ {name} بِيَدَيْهِ… وَصارَ بَطَلًا في حِكايَتِهِ.",
        "keepsake_note_f": "رَسَمَتْهُ {name} بِيَدَيْها… وَصارَ بَطَلًا في حِكايَتِها.",
        "watermark": "مُعايَنَة · {brand}",
        "dedication_label": "إهْداء",
        "made_for": "حِكايَةٌ كُتِبَتْ وَرُسِمَتْ خِصّيصًا لِـ{name:gen}",  # «لِأبي بكر» (`arabic_names.fill_name`)
        "the_end": "النِّهايَة",
        "parents_title": "لِلأَهْل",
        "parents_lesson_label": "ماذا تُعَلِّمُ هذِهِ الحِكايَة؟",
        "parents_questions_label": "سُؤالانِ بَعْدَ القِراءَة",
        "activity_title_m": "ارْسُمْ أَجْمَلَ لَحْظَةٍ في حِكايَتِكَ",
        "activity_title_f": "ارْسُمي أَجْمَلَ لَحْظَةٍ في حِكايَتِكِ",
        "memories_title": "ذِكْرَيَاتُنَا",
        "memories_photo": "صُورَةٌ مِنْ هٰذَا الْيَوْمِ",
        "memories_with_love": "صُورَةٌ مَعَ مَنْ أُحِبُّ",
        "memories_first_day": "أَوَّلُ يَوْمٍ",
        "memories_last_day": "آخِرُ يَوْمٍ",
        "memories_date": "التَّارِيخُ:",
        "memories_prompt": "ذِكْرَى لَا أَنْسَاهَا:",
        "back_voice": "امْسَحوا الرَّمْزَ لِتَسْمَعوا الحِكايَةَ بِصَوْتِ العائِلَة",
        "scan_listen": "امْسَحوا وَاسْمَعوا",  # to the family, like back_voice (never a boy-only «امْسَحْ»)
        "made_by": "صُنِعَ بِحُبٍّ في {brand}",
        # cover ribbon (Addendum 11 §2.3): «بطولة البطل الرائع» / «بطولة البطلة الرائعة», then the name in the
        # genitive (it follows «البطلِ»: «بطولة البطل الرائع أبي بكر»)
        "ribbon_m": "بُطُولَةُ الْبَطَلِ الرَّائِعِ",
        "ribbon_f": "بُطُولَةُ الْبَطَلَةِ الرَّائِعَةِ",
        # the companion's bubble on the drawing page (addresses the child)
        "activity_bubble_m": "أَنَا أَنْتَظِرُ رَسْمَتَكَ!",
        "activity_bubble_f": "أَنَا أَنْتَظِرُ رَسْمَتَكِ!",
        # cover: the series after the brand name (front pill), the facts on the back, the personal line
        "series_classic": "كلاسيك",
        "series_magic": "سحري",
        "series_custom": "حكاية خاصّة",
        "series_class": "كتاب الصفّ",
        "made_for_copy": "نُسْخَةٌ خاصَّةٌ بِـ{name:gen}",
        "ages": "لِلأَعْمارِ {low}–{high}",
        "vowelized": "الحِكايَةُ مُشَكَّلَةٌ بِالكامِل",
    },
    "en": {
        "keepsake_title": "And that's how my friend was born",
        "drawing_label": "My drawing",
        "companion_label": "{companion} in the story",
        "keepsake_note": "Drawn by {name}'s own hands… now a hero in the story.",
        "keepsake_note_f": "Drawn by {name}'s own hands… now a hero in the story.",
        "watermark": "Preview · {brand}",
        "dedication_label": "Dedication",
        "made_for": "A story written and illustrated especially for {name}",
        "the_end": "The End",
        "parents_title": "For parents",
        "parents_lesson_label": "What this story teaches",
        "parents_questions_label": "Two questions after reading",
        "activity_title_m": "Draw your favorite moment from the story",
        "activity_title_f": "Draw your favorite moment from the story",
        "memories_title": "Our memories",
        "memories_photo": "A photo from this day",
        "memories_with_love": "A photo with someone I love",
        "memories_first_day": "First day",
        "memories_last_day": "Last day",
        "memories_date": "Date:",
        "memories_prompt": "A memory I'll never forget:",
        "back_voice": "Scan to hear the story in your family's voice",
        "scan_listen": "Scan & listen",
        "made_by": "Made with love by {brand}",
        "ribbon_m": "Starring the amazing hero",
        "ribbon_f": "Starring the amazing heroine",
        "activity_bubble_m": "I can't wait to see your drawing!",
        "activity_bubble_f": "I can't wait to see your drawing!",
        "series_classic": "Classic",
        "series_magic": "Magic",
        "series_custom": "Custom story",
        "series_class": "Class book",
        "made_for_copy": "A special edition for {name}",
        "ages": "Ages {low}–{high}",
    },
}
