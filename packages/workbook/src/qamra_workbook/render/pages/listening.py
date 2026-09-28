"""Listening pages (Addendum 6 §4.8): a QR code plays the sound; the child circles what they hear."""

from __future__ import annotations

from qamra_workbook.pictures import get as picture
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render.pages.thinking import ring
from qamra_workbook.render.registry import Built, PageContext, page_type


@page_type("listen-and-choose")
def listen_and_choose(ctx: PageContext) -> Built:
    params = ctx.page.params
    choices = [str(c) for c in params.get("choices", ["cow", "cat", "sheep", "duck"])]
    answer = str(params.get("answer", choices[0]))
    problems = []
    if not 3 <= len(choices) <= 4:
        problems.append("listen-and-choose shows 3–4 pictures")
    if choices.count(answer) != 1:
        problems.append(f"the sound ({answer}) must match exactly one picture")
    if not ctx.page.audio:
        problems.append("a listening page carries an audio QR (audio: true)")
    data = {
        "cards": [
            {"pic": ctx.pic(c), "word": strip_tashkeel(picture(c).word_ar), "hit": c == answer}
            for c in choices
        ],
        "ring": ring,
        "url": ctx.book.audio_url(ctx.page),
    }
    word = strip_tashkeel(picture(answer).word_ar)
    sound = str(params.get("sound", ""))
    key = [f"الصوت: {word}" + (f" ({sound})" if sound else "")]
    return Built(data, key, problems)
