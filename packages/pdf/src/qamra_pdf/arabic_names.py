"""A typed name inside an Arabic sentence: «أبو» and «ذو» change with the case (الأسماء الخمسة).

A name prints as the parent typed it, except in the accusative, where a name that starts with «أبو» or «ذو»
takes «أبا» / «ذا» (Fusha): «يا أبا بكر», «ساعِدْ أبا بكر», never «يا أبو بكر». The templates of every
product (story themes, activity books, certificates, covers) fill names through `fill_name`:

- after «يا» the name is a vocative (منادى مضاف, منصوب): `يا {child}` fills «يا أبا بكر» with no mark in the
  template, so every greeting («رائِعٌ يا {child}!», «أَحْسَنْتَ يا {child}!», «أَهْلًا يا {name}») is right;
- an accusative slot that has no «يا» before it is marked in the template, `{child:acc}`: an object
  («{ساعِدْ/ساعِدي} {child:acc} لِلْوُصولِ», «وَضَمَّتْ {name:acc}») or a call without «يا» («{name:acc}!»);
- every other slot (`{child}`) prints the name as typed.

`accusative(name)` changes only a name whose first word is «أبو», «ابو» or «ذو» followed by another word:
«أبو بكر» → «أبا بكر», «ابو بكر» → «ابا بكر» (the parent's hamza kept), «ذو الفقار» → «ذا الفقار», and with
the parent's tashkeel «أَبُو بَكْر» → «أَبَا بَكْر». Left as typed, on purpose:

- a one-word «أبوبكر»: the name is never split or respelled (we cannot tell a joined kunya from a name);
- a name that does not start with «أبو» («محمد أبو بكر», «سلمى أبو غوش»): the first name takes the case, and
  the family part after it is a surname printed as the family writes it;
- the family's name (`{family_name}`, «عائلة أبو غوش»): a surname, never inflected;
- genitive slots (after a preposition or a possessed noun, «لِـ{child}», «كِتابُ {child}»): not handled
  here; they print the name as typed.

AI-written story text cannot carry marks, so its vocatives are fixed after the model writes them
(`fix_vocatives`), and the story prompts ask the model to inflect the name itself.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

_ARABIC = "؀-ۿ"  # letters and marks: «يا» must not be the end of a longer word («هَيّا»)
_M = "[ً-ْٰ]"  # tashkeel: tanween, harakat, shadda, sukun, dagger alif
_FATHA = "َ"

# the first word «أبو» / «ابو» / «ذو» (tashkeel allowed) when another word follows it
_HEAD = re.compile(f"^(\\s*(?:[أا]{_M}*ب|ذ))({_M}*)و{_M}*(?=\\s+\\S)")
# «يا» as a word of its own, and the spaces after it
_YA = f"(?<![{_ARABIC}])ي{_M}*ا{_M}*\\s+"
_YA_AT_END = re.compile(f"{_YA}$")
ACC = ":acc"  # the mark of an accusative slot: `{child:acc}`


def accusative(name: str) -> str:
    """The name in the accusative and after «يا»: «أبو بكر» → «أبا بكر», «ذو الفقار» → «ذا الفقار»; every
    other name is returned as typed."""
    return _HEAD.sub(lambda m: m.group(1) + (_FATHA if m.group(2) else "") + "ا", name, count=1)


def vocative(name: str) -> str:
    """The name after «يا» (a vocative of a construct name is accusative): the same as `accusative`."""
    return accusative(name)


def after(before: str, name: str) -> str:
    """The name as printed right after `before`: accusative when `before` ends with «يا», else as typed (for
    a title set in pieces: «…يا» + the name in its own color)."""
    return accusative(name) if _YA_AT_END.search(before) else name


def fill_name(text: str, slot: str, name: str) -> str:
    """`{slot}` and `{slot:acc}` filled with `name`: accusative at `{slot:acc}` and right after «يا», as typed
    everywhere else. `slot` is the bare placeholder name («child», «name», «adult»)."""
    plain, marked = "{" + slot + "}", "{" + slot + ACC + "}"
    if plain not in text and marked not in text:
        return text
    form = accusative(name)
    text = text.replace(marked, form)
    if form != name:
        text = re.sub(f"({_YA})" + re.escape(plain), lambda m: m.group(1) + form, text)
    return text.replace(plain, name)


def fill_names(text: str, names: Mapping[str, str]) -> str:
    """Every slot of `names` ({slot: name}) filled with `fill_name`."""
    for slot, name in names.items():
        text = fill_name(text, slot, name)
    return text


def unmark(text: str, slots: tuple[str, ...]) -> str:
    """`{slot:acc}` → `{slot}`: the text as it was before the case marks (to keep a cached text's key)."""
    for slot in slots:
        text = text.replace("{" + slot + ACC + "}", "{" + slot + "}")
    return text


def remark(text: str, template: str, slots: tuple[str, ...]) -> str:
    """The case marks of `template` put back on `text`, slot by slot in order. `text` is `template` with its
    marks removed and only diacritics added (a cached vowelization), so their slots line up; when the slot
    names do not line up the text is returned as it is."""
    pattern = re.compile("\\{(" + "|".join(map(re.escape, slots)) + ")(?:" + ACC + ")?\\}")
    marks = list(pattern.finditer(template))
    if [m.group(1) for m in marks] != [m.group(1) for m in pattern.finditer(text)]:
        return text
    it = iter(m.group(0) for m in marks)
    return pattern.sub(lambda _: next(it), text)


def _loose(word: str) -> str:
    """A regex for `word` with any tashkeel between and after its letters."""
    return "".join(re.escape(c) + f"{_M}*" for c in word)


def fix_vocatives(text: str, name: str) -> str:
    """AI-written text: «يا أبو بكر» → «يا أبا بكر» for the child's own name, with or without tashkeel
    («يَا أَبُو بَكْرٍ» → «يَا أَبَا بَكْرٍ»). Other names and other cases are left to the model."""
    words = name.split()
    if len(words) < 2 or accusative(name) == name:
        return text
    head = re.compile(f"({_YA})((?:[أا]{_M}*ب|ذ))({_M}*)و{_M}*(?=\\s+{_loose(re.sub(_M, '', words[1]))})")
    return head.sub(lambda m: m.group(1) + m.group(2) + (_FATHA if m.group(3) else "") + "ا", text)
