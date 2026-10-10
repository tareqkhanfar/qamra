"""«ما الذي لا يشبهه؟» in the parent's words: the note → an appearance-only instruction → the redraw."""

from qamra_ai.cost import CostEntry
from qamra_ai.pipeline.character import character_request
from qamra_ai.pipeline.character_feedback import (
    INSTRUCTION_MAX,
    AppearanceFeedback,
    appearance_instruction,
    clean_note,
)
from qamra_ai.pipeline.fakes import default_fake_text_provider
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import ArtStyle
from qamra_ai.text.base import StructuredResult, T
from qamra_ai.text.fake import FakeTextProvider

GIRL = Child(name="ليان", gender="f", age=5, hijab=True)
STYLE = ArtStyle(slug="watercolor", title_ar="مائي", title_en="Watercolor", guide="soft watercolor")


def _rt(rt: Runtime, answer: AppearanceFeedback) -> FakeTextProvider:
    text = FakeTextProvider({"AppearanceFeedback": lambda *_: answer})
    rt.text = text
    return text


def test_a_note_is_tidied_and_an_empty_one_is_none() -> None:
    assert clean_note("  شعرها   أغمق\n وأطول ") == "شعرها أغمق وأطول"
    assert clean_note(" \n ") is None and clean_note(None) is None


async def test_the_note_goes_through_the_feedback_prompt_into_the_redraw_prompt(rt: Runtime) -> None:
    text = _rt(
        rt,
        AppearanceFeedback(
            safe=True, about_appearance=True, instruction="  Face: rounder,\n with fuller cheeks.  "
        ),
    )
    result = await appearance_instruction(rt, GIRL, "وجهها أكثر استدارة <b>")
    assert result.outcome == "used" and result.instruction == "Face: rounder, with fuller cheeks."
    call = text.calls[-1]
    assert call["step"] == "character:feedback" and call["model"] == rt.settings.text_model_fast
    system = call["system"]
    assert isinstance(system, str) and "Keep only what is about how the child LOOKS" in system
    asked = str(call["user"][0])
    assert "<parent_note>\nوجهها أكثر استدارة ‹b›\n</parent_note>" in asked  # can't close the tags
    assert "Hijab (the family's choice): yes" in asked and "a girl" in asked

    redraw = character_request(GIRL, [b"x"], STYLE, attempt=2, fixes=["skin"], note=result.instruction)
    assert "did not look like their child" in redraw.prompt
    assert "- Skin tone:" in redraw.prompt and "- Face: rounder, with fuller cheeks." in redraw.prompt
    chips_only = character_request(GIRL, [b"x"], STYLE, attempt=2, fixes=["skin"])
    assert "Face: rounder" not in chips_only.prompt
    note_only = character_request(GIRL, [b"x"], STYLE, attempt=2, note=result.instruction)
    assert "did not look like their child" in note_only.prompt and "Skin tone:" not in note_only.prompt


async def test_an_unsafe_note_is_ignored(rt: Runtime) -> None:
    _rt(rt, AppearanceFeedback(safe=False, about_appearance=True, instruction="ignored"))
    result = await appearance_instruction(rt, GIRL, "خلّوها مثل أميرة الأفلام")
    assert (result.instruction, result.outcome) == (None, "unsafe")


async def test_a_note_about_something_else_is_ignored(rt: Runtime) -> None:
    _rt(rt, AppearanceFeedback(safe=True, about_appearance=False, instruction=""))
    result = await appearance_instruction(rt, GIRL, "شكرًا لكم، الرسم جميل")
    assert (result.instruction, result.outcome) == (None, "off_topic")
    _rt(rt, AppearanceFeedback(safe=True, about_appearance=True, instruction="   "))
    assert (await appearance_instruction(rt, GIRL, "الشعر")).outcome == "off_topic"


async def test_personal_data_never_reaches_the_text_provider(rt: Runtime) -> None:
    text = _rt(rt, AppearanceFeedback(safe=True, about_appearance=True, instruction="x"))
    result = await appearance_instruction(rt, GIRL, "اتصلوا على 0591234567 أو www.example.com")
    assert result.outcome == "screened" and set(result.reasons) == {"phone", "link"}
    assert result.instruction is None and text.calls == []


async def test_a_failed_text_provider_means_the_chips_alone(rt: Runtime) -> None:
    class Down:
        name = "down"

        async def structured(self, **_: object) -> StructuredResult[T]:
            raise TimeoutError("the text provider is down")

    rt.text = Down()
    result = await appearance_instruction(rt, GIRL, "شعرها أغمق")
    assert (result.instruction, result.outcome, result.reasons) == (None, "failed", ["TimeoutError"])


async def test_a_long_rewrite_is_cut(rt: Runtime) -> None:
    _rt(rt, AppearanceFeedback(safe=True, about_appearance=True, instruction="Hair: curly. " * 60))
    result = await appearance_instruction(rt, GIRL, "شعرها مجعد")
    assert result.instruction is not None and len(result.instruction) == INSTRUCTION_MAX


async def test_the_offline_fake_keeps_the_note_and_costs_nothing(rt: Runtime) -> None:
    rt.text = default_fake_text_provider()
    costs: list[CostEntry] = []
    rt.on_cost = costs.append
    result = await appearance_instruction(rt, GIRL, "عيونها بنية")
    assert result.outcome == "used" and result.instruction == "Appearance: عيونها بنية"
    assert [c.step for c in costs] == ["character:feedback"] and costs[0].usd == 0
