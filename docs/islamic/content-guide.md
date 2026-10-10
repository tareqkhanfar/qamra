# «قلبي يعرف الله» — writing the pages of a volume

For the writers of the volumes' content (people or agents). One file per volume:
`content/islamic/pages/<v>.yaml` (`v1` … `v5`, `r`). The engine reads it, puts every page in its place, checks
it and renders the book. Everything you write is **AI-drafted until the scholar approves it** (Addendum 10 §3);
nothing prints or sells before that.

```
uv run python -m qamra_workbook.render.islamic_volume --volume v1 --keys        # the places and their keys (✓ = written)
uv run python -m qamra_workbook.render.islamic_volume --volume v1 --check       # what is missing or wrong (fast, no PDF)
uv run python -m qamra_workbook.render.islamic_volume --volume v1 --vocab       # scenes, backdrops, icons, pictures
uv run python -m qamra_workbook.render.islamic_volume --volume v1 --only u-allah/   # render a few pages to look at them
uv run python -m qamra_workbook.render.islamic_volume --volume v1               # the whole preview (out/islamic/v1/)
uv run python -m qamra_workbook.render.islamic_volume --volume v1 --gender m --name يوسف   # the boy's copy
```

`--check` must end with `0 error(s)` before you hand a volume over. `--print` (the real print build) also needs
every source `scholar_approved` and every unit of the volume approved in the scholar's review export
(`$QAMRA_ISLAMIC_REVIEW_FILE`, or `content/islamic/review-status.json` from `qamra islamic-review-export`); until
then it refuses and writes nothing — that is expected while you write. Missing pages are listed as "to write"
(they print as a marked placeholder page in a preview); `--check --complete` also counts them as errors.
Open `out/islamic/<v>/contact-sheet.png` (or the PNGs in `png/`) after rendering and look at your pages.

## 1. The rules (P0 — the build refuses a page that breaks them)

1. **Never type Quran, hadith or dhikr.** Not a verse, not a dua, not «بسم الله», not «الحمد لله». A page asks
   for wording by a source id from `content/islamic/sources.yaml` (+ `sources.d/*.yaml`):
   * a block of wording: `quote: {source: h-bukhari-6094}`, `verse: {source: q-112}`, `dhikr: {source: d-eat-start}`
     (a stretch of a hadith: `span: {start: "الصدق يهدي", end: "البر"}` — search markers, never printed);
   * an option or a match side that *is* wording: `{source: d-wake, ok: true}`;
   * wording inside a sentence: `{src:d-eat-start}` (e.g. `"نَقُولُ {src:d-eat-start} قَبْلَ الطَّعَامِ."`).

   The check folds every text to its letters and refuses one that contains a register dhikr or ayah. If an id you
   need does not exist, **do not invent one and do not type the text**: write the page without it and list the
   missing source in your report (Tareq adds it to the register for the scholar).
2. **Every religious statement cites its source ids** (`sources: [...]`): a story line or scene that tells what a
   prophet did, a lesson, a ruling, a true/false statement, a question, a step of wudu or prayer. Cite the ids the
   lesson plans in `content/islamic/volumes/<v>.yaml` (`s:`); another id gives a warning (fine when it is right).
3. **No depiction.** Never Allah, a prophet, an angel or a Companion — no face, figure, silhouette, shadow, light
   or symbol standing for them. People appear **only** as the cast: `huda` (سِتِّي هُدَى), `reem`, `salem`,
   `naanaa` (the cat) and `reader` (the child's own character). A library picture of a person (boy, mother,
   grandfather…) is never a prop. Prophets' stories (`prophet-story`) and the Prophet's ﷺ life (`sira-story`)
   are told by Sitti Huda to the children (the narrator panel) while every scene shows **only places, nature and
   objects** — no figure at all, not even the cast, not a body part.
4. **Pages that get coloured, cut, drawn on or thrown away carry no sacred text and no source**: `coloring`,
   `maze`, `draw`, `cut-paste`, `home-challenge`, `passport`, `certificate`. No verse, hadith, dhikr, `{src:…}`.
   (The Name of Allah or ﷺ inside an ordinary sentence is not a source; whether the certificate's sentence may
   carry them is a scholar decision.)
5. **Love before fear.** No hellfire, punishment, threats or scary pictures. A mistake is met with an apology,
   repentance and trying again; a wrong option's feedback is gentle («{جَرِّبْ/جَرِّبِي} مَرَّةً أُخْرَى!»).
6. **Honorifics, always**: «نَبِيُّنَا مُحَمَّدٌ ﷺ» (the ligature ﷺ, one character), «يُونُسُ عَلَيْهِ السَّلَامُ»,
   «إِبْرَاهِيمُ وَإِسْمَاعِيلُ عَلَيْهِمَا السَّلَامُ». Companions: «رَضِيَ اللهُ عَنْهُ / عَنْهَا».
7. **Only what is established.** Prophets' stories keep to what the Quran or authentic sunnah says (the source's
   `scholar_decision` note says where to stop). No «يُقال إنّ…» stories, no famous-but-weak sayings (see the
   proposal's «ما لن نستعمله»). Where scholars differ, do not choose: use the register's wording and its
   `scholar_decision` goes to the scholar.
8. **Arabic must be perfect.** Children's text (everything except the parents' page and parents' notes) is
   **fully vowelized**, including case endings: «ذَهَبَ سَالِمٌ إِلَى الْمَسْجِدِ». Parents' text is plain modern
   standard Arabic, lightly vowelized where it helps. Write the Name as the samples do: «اللهُ / اللهِ / اللهَ».
   Numbers in text are plain digits (`٧` or `7`): the book prints them in the family's choice of numerals.
9. **Gender.** The child is addressed in their gender with `{masculine/feminine}`:
   `{رَتِّبْ/رَتِّبِي}`, `{أَنْتَ/أَنْتِ}`, `{أُمِّكَ/أُمِّكِ}`, `{أَحْسَنْتَ يَا بَطَلُ/أَحْسَنْتِ يَا بَطَلَةُ}`.
   Put the whole agreeing phrase in the variant when more than one word changes. `{child}` is the child's name;
   it never goes inside a variant, and a variant never holds another `{…}`: write `{أَحْسَنْتَ/أَحْسَنْتِ} يَا {child}`.
   Text in the child's own voice (first person: «أُرَتِّبُ سَرِيرِي») usually needs no variant — but adjectives
   and participles do: «أَقِفُ {مُتَّجِهًا/مُتَّجِهَةً} إِلَى الْقِبْلَةِ».
10. **Mark drafts.** Every page you write has `ai_drafted: true`. A line that explains a source in simple words
    (a lesson, a scene's sentence, a «why») has `ai_drafted: true` and its `sources`. The explanation never replaces
    the source's wording: the wording is printed by id, the explanation beside it.
11. **The parents' pages** (`parent-guide`, the `tip` of a role-play, `care_note`) speak to the family: warm,
    short, practical, no pressure («نشجّع ولا نُلزم»).

## 2. The keys: where a page goes

`--keys` lists them. A volume's places, in book order:

| key | the place |
|---|---|
| `front/1` … `front/5` | the front pages: title, the cast, how to use + caring for the book, the passport, «هذا أنا» (R has 4: no passport) |
| `<unit>/opener` | the unit's first page |
| `<unit>/l<i>-<j>` | lesson *i* of the unit (from 1, in the order of `volumes/<v>.yaml`), its *j*-th page (from 1, in the order of its `p:` list) |
| `<unit>/closing-1`, `<unit>/closing-2` | the unit's two closing pages |
| `<unit>/parent` | the unit's parent page |
| `<unit>/review-<k>` | the k-th cumulative review page placed after the unit (`cumulative:` in the volume file) |
| `end/<k>` | the final pages in the order of `back:` (V1: `end/1`, `end/2` assessment, `end/3` passport/journey card, `end/4` certificate, `end/5` the back page) |

Example: V1 lesson 1 of `u-allah` is «مَنْ خَلَقَنِي؟» with `p: [story, find-objects, choose]` → keys
`u-allah/l1-1` (story), `u-allah/l1-2` (find-objects), `u-allah/l1-3` (choose).

An entry **does not write** `id`, `unit` or `volume`: the engine derives them (`id` = `v1-u-allah-l1-1`, used for
the page's seed and its audio QR link). `title` is optional: it defaults to the lesson's title (lesson pages),
the unit's title (opener), or the type's default title below. Write a `title` only when the page needs its own.

**What may fill a place** — the plan's type (in `volumes/<v>.yaml` or automatic) → the content types you may use:

| plan type | content `type` | default title when none is given |
|---|---|---|
| story | `story` | the lesson's |
| prophet-story | `prophet-story` | the lesson's |
| sira-story | `sira-story` | the lesson's |
| pillar-card | `pillar-card` | the lesson's |
| coloring | `coloring` | the lesson's |
| maze | `maze` | the lesson's |
| find-objects / blessings-hunt | `find-objects` or `blessings-hunt` | the lesson's |
| order-steps | `order-steps` (wudu, with card art) or `prayer-steps` | the lesson's |
| match | `match` | the lesson's |
| draw | `draw` | the lesson's |
| surah | `surah` | the lesson's |
| true-false | `true-false` | the lesson's |
| choose | `choose` | the lesson's |
| dhikr | `dhikr` | the lesson's |
| wwyd | `wwyd` | the lesson's |
| wdif | `wdif` | the lesson's |
| role-play | `role-play` | the lesson's |
| day | `day` | the lesson's |
| unit-opener (automatic) | `unit-opener` | the unit's |
| unit-closing (automatic, ×2) | `unit-closing` | خِتَامُ الْوَحْدَةِ |
| parent-guide (automatic) | `parent-guide` | لِلْأَهْلِ: + the unit's title |
| self-test (cumulative) | `self-test`, `quiz` or `unit-review` | {اخْتَبِرْ نَفْسَكَ/اخْتَبِرِي نَفْسَكِ} (unit-review: مَاذَا أَتَذَكَّرُ؟) |
| front | `front-title`, `front-characters`, `front-how-to-use`, `passport`, `front-this-is-me`, `back-page` | the volume's / أَصْدِقَائِي فِي الرِّحْلَةِ / كَيْفَ نَسْتَعْمِلُ هَذَا الْكِتَابَ؟ / جَوَازُ … / هَذَا أَنَا / إِلَى اللِّقَاءِ |
| assessment | `assessment` (or the older `final-assessment`) | مَاذَا تَعَلَّمْتُ فِي رِحْلَتِي؟ |
| passport | `passport` (`layout: journey-card` for the second one at the end) | {جَوَازُ الْمُسْلِمِ الصَّغِيرِ/جَوَازُ الْمُسْلِمَةِ الصَّغِيرَةِ} |
| certificate | `certificate` | {شَهَادَةُ الْمُسْلِمِ الصَّغِيرِ/شَهَادَةُ الْمُسْلِمَةِ الصَّغِيرَةِ} |
| cut-paste, home-challenge | `cut-paste`, `home-challenge` | no volume places them yet: a lesson must list them in `volumes/<v>.yaml` first (ask Tareq) |

## 3. Pictures

* **`scene`** (a story, a dhikr, a wwyd, a role-play, a choose page) is either a drawn scene
  `{art: family-meal}` or a composed one `{backdrop: kitchen, props: [cup, loaf, dates], figures: [reader, huda]}`.
  * drawn scenes (`art`): `ship-at-sea`, `dark-sea-whale`, `moonlit-sea`, `shore-gourd-sunrise` (no people),
    `family-meal`, `kitchen-broken-cup`, `blessings-scene` (with the cast), `blessings-garden` (line art to colour);
  * backdrops: `home`, `kitchen`, `table` (the cast sit behind it, props stand on it), `bedroom-night`,
    `bedroom-morning`, `garden`, `night-sky`, `mosque`, `mosque-inside`, `classroom`, `street`, `market`, `sea`,
    `desert`; up to 4–6 props (each backdrop has its own places for them) and up to 4 figures;
  * props and every `pic`: an id of the picture library (`--vocab` lists them: `cup`, `loaf`, `dates`, `lamp`,
    `door`, `book`, `palm`, `moon`, `water`, `soap`, `toothbrush`…) or a series icon `isl:lantern`, `isl:prayer-mat`,
    `isl:dome`, `isl:book-stand`, `isl:beads`, `isl:crescent`, `isl:cube`, `isl:water-drop`, `isl:gift`…
* The picture library draws simple things; pick props a child recognises. Never a person picture.
* `figures` are the cast only (`huda`, `reem`, `salem`, `naanaa`, `reader`); on a `prophet-story` or `sira-story`
  page a scene has **no** figures and no body parts. In a unit that tells a prophet's story or the Prophet's ﷺ
  life, the colouring, maze, find, cut and drawing pages follow the same rule (the check enforces it): picture
  objects (the ship, the sea, the whale, the cave), not the children.

## 4. Length (what fits the layout)

Counted in words on the printed text (both genders). `--check` reports `too-long`. Keep children's sentences
short: one idea per line.

| field | max words | | field | max words |
|---|---|---|---|---|
| `title` | 8 | | `instruction`, `stars`, `tracker`, `draw_box`, `role_play` | 7 |
| `t` (a line, an option, a statement, a step, a moment) | 16 | | `text` (a lesson, a question, a «why») | 24 |
| `scenario` | 24 | | narrator `intro` | 26 |
| `feedback` | 12 | | `word` (find-objects) | 3 |
| `when` | 6 | | `question` (unit opener) | 18 |
| `prompt` (draw) | 16 | | `challenge` | 24 |
| `learned` (each), `apply` | 14 | | `apply_choices` (each) | 8 |
| `message` (back page) | 30 | | `skill` | 4 |
| `prompts` (each, «هذا أنا») | 6 | | `steps` (home challenge, each) | 12 |
| `role`, `by`, `boxes`, `slots` | 4 | | parents' `text` (parent-guide) | 42 |
| `tip` (role-play, for the grown-up) | 30 | | `care_note` | 40 |

Counts per page: a story has 1–6 lines (4 when it also has a quote or a question); true/false 2–6 statements;
choose 1–4 questions of 2–4 choices with exactly one right; match 3–5 pairs; find-objects 2–8 things and up to 10
others; a prophet's/sira story 1–4 scenes (2 or 4 look best); wwyd exactly 3 choices, one right.

## 5. One valid example of every type

Every block below is checked by the tests (`packages/workbook/tests/test_islamic_volume.py`): it parses, passes
the checks and builds. Copy, then change the content. The sample pages of `content/islamic/samples.yaml` are
already placed in V1 (see `content/islamic/pages/v1.yaml`); V2/V4's samples go to the keys shown here
(`u-wudu/l2-1`, `u-whatif1/l3-1`, `u-surahs1/l2-1`, `u-yunus/l1-1`). The examples carry the language review's
corrections; copy their wording, not the older wording of `samples.yaml`.

### story

```yaml
- key: u-allah/l1-1
  type: story
  ai_drafted: true
  scene: {backdrop: garden, props: [bird, flower], figures: [huda, reem, salem]}
  lines:
    - {who: salem, t: "سِتِّي، مَنْ خَلَقَ الشَّمْسَ وَالشَّجَرَ؟"}
    - {who: huda, t: "اللهُ خَلَقَهَا يَا سَالِمُ، وَخَلَقَكَ أَنْتَ أَيْضًا.", sources: [q-39-62], ai_drafted: true}
    - {who: reem, t: "وَخَلَقَ الطُّيُورَ الَّتِي تُغَرِّدُ فَوْقَنَا!"}
  lesson: {text: "اللهُ هُوَ الَّذِي خَلَقَنَا وَخَلَقَ كُلَّ شَيْءٍ.", sources: [q-39-62], ai_drafted: true}
  question:
    text: "مَنْ خَلَقَ الشَّمْسَ؟"
    choices: [{t: "اللهُ", ok: true}, {t: "النَّاسُ"}]
    sources: [q-6-1]
```

`who` is `huda`, `reem`, `salem`, `naanaa`, `reader` or `narrator` (no picture). Optional: `quote` (a source's
wording), `lesson`, `question`.

### prophet-story (V4; the sample s01)

```yaml
- key: u-yunus/l1-1
  type: prophet-story
  ai_drafted: true
  title: يُونُسُ عَلَيْهِ السَّلَامُ وَالْحُوتُ
  narrator:
    figures: [huda, reem, salem]
    intro: "جَلَسَتْ رِيمُ وَسَالِمٌ بِجَانِبِ سِتِّي هُدَى، فَقَالَتْ لَهُمَا: سَأَحْكِي لَكُمَا حِكَايَةَ نَبِيٍّ مِنْ أَنْبِيَاءِ اللهِ."
  scenes:
    - {art: ship-at-sea, text: "رَكِبَ يُونُسُ عَلَيْهِ السَّلَامُ سَفِينَةً فِي الْبَحْرِ.", sources: [q-37-139-148], ai_drafted: true}
    - {art: dark-sea-whale, text: "ثُمَّ الْتَقَمَهُ حُوتٌ كَبِيرٌ، فَصَارَ فِي بَطْنِ الْحُوتِ فِي الظُّلُمَاتِ.", sources: [q-37-139-148], ai_drafted: true}
    - {art: moonlit-sea, text: "فَنَادَى يُونُسُ عَلَيْهِ السَّلَامُ رَبَّهُ، وَاللهُ قَرِيبٌ يَسْمَعُ.", sources: [q-21-87, q-2-186], ai_drafted: true}
    - {art: shore-gourd-sunrise, text: "فَاسْتَجَابَ اللهُ لَهُ وَنَجَّاهُ، وَأَنْبَتَ عَلَيْهِ شَجَرَةَ يَقْطِينٍ.", sources: [q-21-88, q-37-139-148], ai_drafted: true}
  verse: {source: q-21-87, label: دُعَاءُ يُونُسَ عَلَيْهِ السَّلَامُ}
  lesson: {text: "نَدْعُو اللهَ فِي كُلِّ وَقْتٍ، وَهُوَ يَسْمَعُنَا وَيُحِبُّ أَنْ نَرْجِعَ إِلَيْهِ إِذَا أَخْطَأْنَا.", sources: [q-2-186, q-2-222], ai_drafted: true}
  question:
    text: "مَنْ نَجَّى يُونُسَ عَلَيْهِ السَّلَامُ؟"
    choices: [{t: "اللهُ", ok: true}, {t: "السَّفِينَةُ"}, {t: "الْحُوتُ"}]
    sources: [q-21-88, q-37-139-148]
```

The scenes show places and objects only (`art` without people, or a `backdrop` with props and **no** figures).

### sira-story

```yaml
- key: u-prophet/l2-1
  type: sira-story
  ai_drafted: true
  narrator:
    figures: [huda, reem, salem]
    intro: "قَالَتْ سِتِّي هُدَى: كَانَ نَبِيُّنَا ﷺ رَحِيمًا بِالْأَطْفَالِ، فَاسْمَعَا هَذِهِ الْحِكَايَةَ."
  scenes:
    - {backdrop: mosque-inside, text: "كَانَ النَّبِيُّ ﷺ يُصَلِّي بِالنَّاسِ فِي الْمَسْجِدِ.", sources: [h-bukhari-707], ai_drafted: true}
    - {backdrop: mosque, props: ["isl:lantern"], text: "فَسَمِعَ بُكَاءَ طِفْلٍ صَغِيرٍ.", sources: [h-bukhari-707], ai_drafted: true}
    - {backdrop: mosque-inside, props: ["isl:prayer-mat"], text: "فَخَفَّفَ الصَّلَاةَ رَحْمَةً بِالطِّفْلِ وَبِأُمِّهِ.", sources: [h-bukhari-707], ai_drafted: true}
  quote: {source: q-21-107}
  lesson: {text: "نَرْحَمُ الصِّغَارَ كَمَا رَحِمَهُمْ نَبِيُّنَا ﷺ.", sources: [h-bukhari-5997], ai_drafted: true}
  question:
    text: "لِمَاذَا خَفَّفَ النَّبِيُّ ﷺ الصَّلَاةَ؟"
    choices: [{t: "رَحْمَةً بِالطِّفْلِ", ok: true}, {t: "لِأَنَّ الْمَطَرَ نَزَلَ"}]
    sources: [h-bukhari-707]
```

`quote` is optional (a hadith span or a verse by id). Same no-person rule as a prophet's story.

### role-play

```yaml
- key: u-manners2/l3-2
  type: role-play
  ai_drafted: true
  instruction: "{مَثِّلِ الْمَوْقِفَ مَعَ أَهْلِكَ/مَثِّلِي الْمَوْقِفَ مَعَ أَهْلِكِ}"
  scenario: "{تُرِيدُ أَنْ تَدْخُلَ غُرْفَةَ وَالِدَيْكَ/تُرِيدِينَ أَنْ تَدْخُلِي غُرْفَةَ وَالِدَيْكِ}، وَالْبَابُ مُغْلَقٌ."
  scene: {backdrop: home, props: [door], figures: [reader]}
  roles:
    - {role: "الطَّارِقُ", by: "{أَنْتَ/أَنْتِ}"}
    - {role: "صَاحِبُ الْغُرْفَةِ", by: "{أَبُوكَ أَوْ أُمُّكَ/أَبُوكِ أَوْ أُمُّكِ}"}
  script:
    - {role: "الطَّارِقُ", t: "أَطْرُقُ الْبَابَ بِلُطْفٍ، وَأُسَلِّمُ، ثُمَّ أَسْأَلُ: هَلْ أَدْخُلُ؟", sources: [q-24-27]}
    - {role: "صَاحِبُ الْغُرْفَةِ", t: "{تَفَضَّلْ، شُكْرًا لِأَنَّكَ اسْتَأْذَنْتَ/تَفَضَّلِي، شُكْرًا لِأَنَّكِ اسْتَأْذَنْتِ}."}
  tip: "تبادلوا الأدوار بعد ذلك: يطرق أحدكم الباب ويستأذن، ويجيب الطفل."
  stars: "كَمْ نَجْمَةً نَسْتَحِقُّ؟"
```

### find-objects

```yaml
- key: u-blessings/l2-2
  type: find-objects
  ai_drafted: true
  instruction: "{ابْحَثْ/ابْحَثِي} عَنِ الطَّعَامِ وَالشَّرَابِ"
  find:
    - {pic: loaf, word: الْخُبْزُ}
    - {pic: dates, word: التَّمْرُ}
    - {pic: apple, word: التُّفَّاحَةُ}
    - {pic: milk, word: الْحَلِيبُ}
    - {pic: water, word: الْمَاءُ}
  others: [car, ball, chair, lamp, shoe, kite]
  closing: {text: "الطَّعَامُ وَالشَّرَابُ مِنْ نِعَمِ اللهِ عَلَيْنَا.", sources: [q-2-172], ai_drafted: true}
```

The things are scattered on a board among the `others`; the child rings them and ticks each word.

### blessings-hunt (the sample s07)

```yaml
- key: u-blessings/l1-2
  type: blessings-hunt
  ai_drafted: true
  title: أَبْحَثُ عَنْ نِعَمِ اللهِ
  instruction: "{ضَعْ/ضَعِي} دَائِرَةً حَوْلَ كُلِّ نِعْمَةٍ"
  art: blessings-scene
  find: [الشَّمْسُ, الْمَاءُ, الشَّجَرَةُ, الثَّمَرَةُ, الطَّائِرُ, الْخُبْزُ, الْقَمَرُ, الْأُسْرَةُ]
  closing: {text: "وَهَذِهِ بَعْضُ نِعَمِ اللهِ عَلَيْنَا، وَهِيَ أَكْثَرُ مِنْ أَنْ نَعُدَّهَا!", sources: [q-16-18], ai_drafted: true}
  draw_box: "هَلْ {تَرَى/تَرَيْنَ} نِعْمَةً أُخْرَى؟ {ارْسُمْهَا/ارْسُمِيهَا} هُنَا"
```

Only the scene `blessings-scene` and these eight words exist for this type; for anything else use `find-objects`.

### match

```yaml
- key: u-house/l4-2
  type: match
  ai_drafted: true
  instruction: "{صِلْ/صِلِي} كُلَّ رُكْنٍ بِصُورَتِهِ"
  pairs:
    - {a: {t: "الشَّهَادَتَانِ"}, b: {pic: "isl:key"}}
    - {a: {t: "الصَّلَاةُ"}, b: {pic: "isl:prayer-mat"}}
    - {a: {t: "الصِّيَامُ"}, b: {pic: "isl:crescent"}}
    - {a: {t: "الزَّكَاةُ"}, b: {pic: "isl:coin-heart"}}
    - {a: {t: "الْحَجُّ"}, b: {pic: "isl:cube"}}
```

A side is a picture (`pic`), a word (`t`), both, or a source's wording (`source`, on a page that may carry it):

```yaml
- key: u-adhkar1/l1-3
  type: match
  ai_drafted: true
  instruction: "{صِلْ/صِلِي} كُلَّ وَقْتٍ بِمَا نَقُولُهُ فِيهِ"
  pairs:
    - {a: {pic: plate, t: "قَبْلَ الطَّعَامِ"}, b: {source: d-eat-start}}
    - {a: {pic: fruit-bowl, t: "بَعْدَ الطَّعَامِ"}, b: {source: d-after-eat}}
    - {a: {pic: bed, t: "حِينَ أَسْتَيْقِظُ"}, b: {source: d-wake}}
```

The right-hand column (`a`) prints in order, the left-hand one (`b`) shuffled; the answer key lists the pairs.

### choose

```yaml
- key: u-allah/l1-3
  type: choose
  ai_drafted: true
  instruction: "{اخْتَرِ/اخْتَارِي} الْجَوَابَ الصَّحِيحَ"
  questions:
    - text: "مَنْ خَلَقَ السَّمَاءَ وَالْأَرْضَ؟"
      pic: cloud
      choices: [{t: "اللهُ", ok: true}, {t: "النَّاسُ"}]
      sources: [q-6-1]
    - text: "مَنْ خَلَقَنِي وَخَلَقَ أُسْرَتِي؟"
      choices: [{t: "اللهُ", ok: true}, {t: "لَا أَحَدَ"}]
      sources: [q-39-62]
```

Optional `scene` at the top. Each question has exactly one `ok: true`.

### true-false

```yaml
- key: u-allah/l2-3
  type: true-false
  ai_drafted: true
  instruction: "{ضَعْ/ضَعِي} دَائِرَةً حَوْلَ الْجَوَابِ"
  statements:
    - {t: "اللهُ خَلَقَ الْبَحْرَ وَالسَّمَكَ.", ok: true, sources: [q-39-62]}
    - {t: "اللهُ وَاحِدٌ.", ok: true, sources: [q-112]}
    - {t: "النَّاسُ خَلَقُوا الشَّمْسَ.", ok: false, sources: [q-39-62]}
```

### pillar-card

```yaml
- key: u-allah/l3-1
  type: pillar-card
  ai_drafted: true
  pillar: "الرَّزَّاقُ"
  idea: {text: "اللهُ هُوَ الرَّزَّاقُ: يُعْطِينَا الطَّعَامَ وَالْمَاءَ وَكُلَّ مَا نَحْتَاجُ إِلَيْهِ.", sources: [q-51-58], ai_drafted: true}
  question:
    text: "مَنْ يَرْزُقُنَا؟"
    choices: [{t: "اللهُ", ok: true}, {t: "لَا أَحَدَ"}]
    sources: [q-51-58]
```

### coloring

```yaml
- key: u-allah/l2-2
  type: coloring
  sacred_text: none
  instruction: "{لَوِّنْ/لَوِّنِي} مَا {تُحِبُّ/تُحِبِّينَ}"
  pics: [sun, tree, fish, flower]
```

`pics` (1–6 library pictures or `isl:` icons, drawn as line art) or `art: blessings-garden` (the one line-art
scene). Always `sacred_text: none`; never a source.

### maze

```yaml
- key: u-eid2/l3-1
  type: maze
  ai_drafted: true
  instruction: "{اذْهَبْ/اذْهَبِي} إِلَى بَيْتِ سِتِّي هُدَى"
  runner: reader
  goal: house
  goal_word: "بَيْتُ سِتِّي"
  size: medium
  collect: [gift, balloon, candy]
```

`runner`: `reader` (the child) or a picture id; on a prophets' unit use a picture (`ship`, `boat`, `whale`).
`size`: `small` (4×4), `medium` (5×5), `large` (6×6). `collect`: up to 4 pictures on the right path.

### draw

```yaml
- key: u-follow/l3-2
  type: draw
  ai_drafted: true
  instruction: "{ارْسُمْ وَلَوِّنْ/ارْسُمِي وَلَوِّنِي}"
  prompt: "{ارْسُمْ نَفْسَكَ وَأَنْتَ تُسَاعِدُ أَهْلَكَ/ارْسُمِي نَفْسَكِ وَأَنْتِ تُسَاعِدِينَ أَهْلَكِ} فِي الْبَيْتِ."
  hints: [broom, plate, watering-can]
```

`boxes: ["قَبْلُ", "بَعْدُ"]` splits the page into two labelled boxes; `lines: 1`–`3` adds writing lines.

### day

```yaml
- key: u-myday1/l1-1
  type: day
  ai_drafted: true
  instruction: "{ضَعْ/ضَعِي} عَلَامَةً عَلَى مَا {فَعَلْتَهُ/فَعَلْتِهِ} الْيَوْمَ"
  moments:
    - {when: "حِينَ أَسْتَيْقِظُ", t: "أَحْمَدُ اللهَ الَّذِي أَيْقَظَنِي.", picture: sun, sources: [h-bukhari-6312]}
    - {when: "ثُمَّ", t: "أَغْسِلُ وَجْهِي وَأُنَظِّفُ أَسْنَانِي.", picture: toothbrush}
    - {when: "عَلَى الْفَطُورِ", t: "أُسَمِّي اللهَ وَآكُلُ بِيَدِي الْيُمْنَى.", picture: loaf, sources: [h-bukhari-5376]}
    - {when: "قَبْلَ أَنْ أَخْرُجَ", t: "أُسَلِّمُ عَلَى أَهْلِي بِابْتِسَامَةٍ.", picture: house}
```

2–10 moments; `picture` is a library id or an `isl:` icon. `tick: false` hides the circles to tick.

### dhikr (the sample s03)

```yaml
- key: u-adhkar1/l1-1
  type: dhikr
  ai_drafted: true
  title: قَبْلَ الطَّعَامِ
  when: حِينَ أَبْدَأُ الْأَكْلَ
  dhikr: {source: d-eat-start}
  why: {text: "لِأَنَّ اللهَ هُوَ الَّذِي رَزَقَنَا هَذَا الطَّعَامَ، فَنَذْكُرُ اسْمَهُ وَنَشْكُرُهُ.", sources: [q-2-172], ai_drafted: true}
  manner: {text: "وَآكُلُ بِيَدِي الْيُمْنَى مِمَّا يَلِينِي.", sources: [h-bukhari-5376], ai_drafted: true}
  scene: {art: family-meal, figures: [reader, reem, salem, huda]}
  home: "نَقُولُهَا مَعًا قَبْلَ كُلِّ وَجْبَةٍ هَذَا الْأُسْبُوعَ، وَنُلَوِّنُ نَجْمَةً فِي آخِرِ كُلِّ يَوْمٍ."
  audio: {kind: human-voice, note: "بصوت بشري مسجّل؛ لا TTS لنص ديني"}
```

The frame is introduced by «أَقُولُ»: it holds what the child says. When the framed wording is a verse that
commands the dhikr rather than the words the child says (the salawat page: 33:56), give `heading: قَالَ اللهُ تَعَالَى`
and let `manner` say what the child says.

### wwyd (the sample s04)

```yaml
- key: u-manners1/l1-2
  type: wwyd
  ai_drafted: true
  title: "{مَاذَا كُنْتَ سَتَفْعَلُ؟/مَاذَا كُنْتِ سَتَفْعَلِينَ؟}"
  scenario: "{كَسَرْتَ/كَسَرْتِ} كَأْسًا فِي الْمَطْبَخِ دُونَ قَصْدٍ، وَلَيْسَ فِي الْمَطْبَخِ أَحَدٌ."
  scene: {art: kitchen-broken-cup, figures: [reader]}
  choices:
    - {t: "أُخْبِرُ أُمِّي بِالصِّدْقِ وَأَعْتَذِرُ", ok: true, feedback: "{أَحْسَنْتَ يَا بَطَلُ/أَحْسَنْتِ يَا بَطَلَةُ}! الصِّدْقُ شَجَاعَةٌ جَمِيلَةٌ."}
    - {t: "أُخَبِّئُ الْقِطَعَ حَتَّى لَا يَرَاهَا أَحَدٌ", feedback: "لَيْسَ هَذَا أَجْمَلَ اخْتِيَارٍ. {جَرِّبْ/جَرِّبِي} مَرَّةً أُخْرَى!"}
    - {t: "أَقُولُ إِنَّ الْقِطَّةَ هِيَ الَّتِي كَسَرَتْهَا", feedback: "لَيْسَ هَذَا أَجْمَلَ اخْتِيَارٍ. {جَرِّبْ/جَرِّبِي} مَرَّةً أُخْرَى!"}
  quote: {source: h-bukhari-6094, span: {start: "الصدق يهدي", end: "البر"}}
  sources: [h-bukhari-6094]
  role_play: "{مَثِّلِ/مَثِّلِي} الْمَوْقِفَ مَعَ {أُمِّكَ/أُمِّكِ} بِصَوْتٍ هَادِئٍ."
```

Exactly three choices, one right; the wrong ones get a gentle feedback.

### wdif (V2; the sample s05)

```yaml
- key: u-whatif1/l3-1
  type: wdif
  ai_drafted: true
  title: مَاذَا أَفْعَلُ لَوْ غَضِبْتُ؟
  intro: {text: "الْغَضَبُ شُعُورٌ يَمُرُّ بِكُلِّ النَّاسِ، وَنَتَعَلَّمُ مَعًا كَيْفَ نَهْدَأُ.", ai_drafted: true}
  steps:
    - {n: 1, t: "أَتَوَقَّفُ وَآخُذُ نَفَسًا عَمِيقًا."}
    - {n: 2, t: "أَقُولُ دُعَاءَ الِاسْتِعَاذَةِ.", dua: d-anger-refuge, sources: [h-bukhari-3282]}
    - {n: 3, t: "أَجْلِسُ حَتَّى أَهْدَأَ.", sources: [h-abudawud-4782]}
    - {n: 4, t: "أَتَكَلَّمُ بِلُطْفٍ، وَأَعْتَذِرُ إِنْ أَخْطَأْتُ.", sources: [q-41-34]}
  quote: {source: h-bukhari-6114, span: {start: "ليس الشديد", end: "الغضب"}}
  meaning: {text: "الْقَوِيُّ حَقًّا هُوَ مَنْ يَهْدَأُ حِينَ يَغْضَبُ، وَلَا يُؤْذِي أَحَدًا.", sources: [h-bukhari-6114], ai_drafted: true}
  tracker: "هَلْ {جَرَّبْتَهَا/جَرَّبْتِهَا} هَذَا الْأُسْبُوعَ؟ {لَوِّنْ/لَوِّنِي} نَجْمَةً"
```

### order-steps (wudu, V2; the sample s02)

```yaml
- key: u-wudu/l2-1
  type: order-steps
  ai_drafted: true
  title: أَتَوَضَّأُ كَمَا عَلَّمَنَا نَبِيُّنَا ﷺ
  instruction: "{رَتِّبِ/رَتِّبِي} الْخُطُوَاتِ مِنْ ١ إِلَى ٨"
  steps:
    - {n: 1, t: "أَبْدَأُ بِذِكْرِ اسْمِ اللهِ", art: speech-bubble, sources: [h-abudawud-101], scholar_decision: true}
    - {n: 2, t: "أَغْسِلُ كَفَّيَّ", times: 3, art: hands, sources: [h-bukhari-159]}
    - {n: 3, t: "أَتَمَضْمَضُ", art: mouth, sources: [h-bukhari-159]}
    - {n: 4, t: "أَسْتَنْشِقُ الْمَاءَ وَأُخْرِجُهُ", art: nose, sources: [h-bukhari-159]}
    - {n: 5, t: "أَغْسِلُ وَجْهِي", times: 3, art: face, sources: [q-5-6, h-bukhari-159]}
    - {n: 6, t: "أَغْسِلُ يَدَيَّ إِلَى الْمِرْفَقَيْنِ", times: 3, art: arms, sources: [q-5-6, h-bukhari-159]}
    - {n: 7, t: "أَمْسَحُ رَأْسِي وَأُذُنَيَّ", art: head, sources: [q-5-6, h-bukhari-159], scholar_decision: true}
    - {n: 8, t: "أَغْسِلُ قَدَمَيَّ إِلَى الْكَعْبَيْنِ", times: 3, art: feet, sources: [q-5-6, h-bukhari-159]}
  scholar_points: [h-abudawud-101, h-bukhari-159]
  parent_line: "رَاجِعُوا الْخُطُوَاتِ مَعًا أَمَامَ الْحَوْضِ، ثُمَّ يُجَرِّبُ الطِّفْلُ بِنَفْسِهِ وَأَنْتُمْ بِجَانِبِهِ."
```

Card art (`art`): `speech-bubble`, `hands`, `mouth`, `nose`, `face`, `arms`, `head`, `feet` (a body part with
water, never a person). For other orderings use `prayer-steps`:

```yaml
- key: u-prayer/l1-2
  type: prayer-steps
  ai_drafted: true
  instruction: "{رَتِّبِ/رَتِّبِي} الْخُطُوَاتِ مِنْ ١ إِلَى ٤"
  steps:
    - {n: 1, t: "أَتَوَضَّأُ.", sources: [q-5-6]}
    - {n: 2, t: "أَلْبَسُ ثِيَابًا نَظِيفَةً سَاتِرَةً.", sources: [s-prayer-clothing]}
    - {n: 3, t: "أَقِفُ عَلَى سَجَّادَتِي {مُتَّجِهًا/مُتَّجِهَةً} إِلَى الْقِبْلَةِ.", sources: [h-bukhari-631]}
    - {n: 4, t: "أُكَبِّرُ وَأَبْدَأُ صَلَاتِي.", sources: [h-bukhari-631]}
```

### surah (V2; the sample s12)

```yaml
- key: u-surahs1/l2-1
  type: surah
  ai_drafted: true
  title: سُورَةُ الْإِخْلَاصِ
  verse: {source: q-112, frame: dignified}
  meaning: {text: "تُعَلِّمُنَا هَذِهِ السُّورَةُ أَنَّ اللهَ وَاحِدٌ، وَهُوَ الَّذِي نَقْصِدُهُ فِي كُلِّ حَاجَاتِنَا.", sources: [q-112], ai_drafted: true}
  audio_qr: {kind: licensed-recitation, note: "تسجيل بصوت قارئ مجاز أو بتسجيلنا مع قارئ مؤهَّل؛ لا TTS للقرآن أبدًا"}
  tracker: {ayahs: 4, days: 7}
  care_note: "هَذِهِ الصَّفْحَةُ فِيهَا كَلَامُ اللهِ تَعَالَى. نَحْفَظُهَا فِي مَكَانٍ نَظِيفٍ، وَلَا نَرْمِيهَا."
  flags: [never_cut, never_colored]
```

### unit-opener (automatic place)

```yaml
- key: u-allah/opener
  type: unit-opener
  ai_drafted: true
  hello: {who: reem, t: "{تَعَالَ نَتَعَرَّفْ/تَعَالَيْ نَتَعَرَّفْ} إِلَى رَبِّنَا الَّذِي خَلَقَنَا وَخَلَقَ كُلَّ شَيْءٍ!"}
  question: "{هَلْ تَعْرِفُ/هَلْ تَعْرِفِينَ} مَنْ خَلَقَ النُّجُومَ؟"
```

The page shows the unit's icon and colour, its picture (`content/assets/F<n>-unit-<name>.jpg` when there is one;
`art:` names another), the lessons inside (from the plan) and the reader's character.

### unit-closing (automatic places: two pages)

```yaml
- key: u-allah/closing-1
  type: unit-closing
  ai_drafted: true
  learned:
    - "اللهُ خَلَقَنِي وَخَلَقَ كُلَّ شَيْءٍ."
    - "مِنْ أَسْمَاءِ اللهِ: الْخَالِقُ وَالرَّحْمَنُ وَالرَّزَّاقُ."
    - "اللهُ قَرِيبٌ مِنِّي، يَسْمَعُنِي وَيُحِبُّنِي."
  apply: "أَخْتَارُ مَا سَأَفْعَلُهُ هَذَا الْأُسْبُوعَ:"
  apply_choices: ["أَنْظُرُ إِلَى السَّمَاءِ وَأَتَفَكَّرُ فِي خَلْقِ اللهِ.", "أَشْكُرُ اللهَ عَلَى نِعَمِهِ.", "أَدْعُو اللهَ قَبْلَ النَّوْمِ."]

- key: u-allah/closing-2
  type: unit-closing
  ai_drafted: true
  dhikr: {source: q-112, label: "سُورَةُ الْإِخْلَاصِ"}
  dhikr_when: "أَقْرَؤُهَا كُلَّ يَوْمٍ مَعَ أَهْلِي."
  challenge: "أَعُدُّ مَعَ أَهْلِي خَمْسَةَ أَشْيَاءَ خَلَقَهَا اللهُ فِي الْحَدِيقَةِ."
```

Between them the two pages carry all four endings: `learned` («ماذا تعلّمت؟»), `apply` («ماذا سأطبّق؟»),
`dhikr` (the unit's dua or dhikr, by id) and `challenge` («تحدٍّ صغير مع أمي وأبي», with a week of stars).

### parent-guide (automatic place; the sample s09)

```yaml
- key: u-blessings/parent
  type: parent-guide
  ai_drafted: true
  title: "لِلْأَهْلِ: نِعَمُ اللهِ حَوْلَنَا"
  learned: {text: "تعلّم طفلكم في هذه الوحدة أنّ الله هو الخالق المنعم، وأنّ نعمه كثيرة حولنا، وأنّ شكره يكون بالقول والعمل.", sources: [q-39-62, q-16-18, q-2-172], ai_drafted: true}
  explain: {text: "ابدؤوا ممّا يراه: «من خلق الشمس؟ ومن أعطانا الماء؟»، ثم قولوا: «هذا من حبّ الله لنا». اجعلوا الشرح قصيرًا ودافئًا، واتركوا للطفل أن يسأل.", ai_drafted: true}
  ask: "ما أجمل شيء أعطاك الله إيّاه اليوم؟"
  together: "جولة امتنان: قبل النوم يذكر كل فرد من الأسرة ثلاث نِعَم، ونرسم واحدة منها في دفتر العائلة."
  habit: {text: "قولوا «{src:d-sneeze-1}» بعد الوجبات وعند ذكر أيّ نعمة، وكرّروها أمام الطفل ليقلّدكم.", sources: [q-1-2, q-14-7], ai_drafted: true}
  care_note: "في الكتاب صفحات فيها كلام الله تعالى وأذكار ودعوات؛ نرجو حفظ الكتاب في مكان نظيف مرتفع، وعدم رميه أو وضع شيء فوقه."
```

The five parts: what the child learned, how to explain the idea, a question to ask, an activity together, how
to make it a daily habit. Plain modern Arabic (not vowelized), warm and short.

### self-test (a cumulative review place)

```yaml
- key: u-manners1/review-1
  type: self-test
  ai_drafted: true
  instruction: "{أَجِبْ ثُمَّ لَوِّنِ/أَجِيبِي ثُمَّ لَوِّنِي} النُّجُومَ"
  true_false:
    - {t: "نَقُولُ {src:d-eat-start} قَبْلَ الطَّعَامِ.", ok: true, sources: [h-bukhari-5376]}
    - {t: "اللهُ يُحِبُّ الصِّدْقَ.", ok: true, sources: [h-bukhari-6094]}
    - {t: "نَأْكُلُ بِالْيَدِ الْيُسْرَى.", ok: false, sources: [h-bukhari-5376]}
  questions:
    - text: "مَاذَا نَقُولُ حِينَ نَسْتَيْقِظُ؟"
      choices: [{source: d-wake, ok: true}, {source: d-sleep}]
      sources: [h-bukhari-6312]
  stars: "كَمْ نَجْمَةً {تَسْتَحِقُّ/تَسْتَحِقِّينَ}؟"
```

`quiz` is the same page. A `unit-review` (the sample s08: true/false + one `choose` + stars) may fill a review
place too — V1's `u-follow/review-1` has it.

### assessment (the final pages)

```yaml
- key: end/1
  type: assessment
  ai_drafted: true
  instruction: "{الْعَبْ وَأَجِبْ/الْعَبِي وَأَجِيبِي}"
  intro: "هَذِهِ لُعْبَةٌ وَلَيْسَتِ امْتِحَانًا، {أَجِبْ مَعَ أُمِّكَ أَوْ أَبِيكَ/أَجِيبِي مَعَ أُمِّكِ أَوْ أَبِيكِ}."
  true_false:
    - {t: "اللهُ خَلَقَ الشَّمْسَ وَالْقَمَرَ.", ok: true, sources: [q-39-62]}
    - {t: "كَانَ نَبِيُّنَا مُحَمَّدٌ ﷺ صَادِقًا أَمِينًا.", ok: true, sources: [h-bukhari-4770]}
  questions:
    - text: "كَمْ مَرَّةً نُصَلِّي فِي الْيَوْمِ؟"
      choices: [{t: "خَمْسَ مَرَّاتٍ", ok: true}, {t: "مَرَّةً وَاحِدَةً"}, {t: "عَشْرَ مَرَّاتٍ"}]
      sources: [h-bukhari-46]
  situations:
    - t: "رَأَتْ رِيمُ صَدِيقَتَهَا تَبْكِي. مَاذَا تَفْعَلُ؟"
      choices: [{t: "تُوَاسِيهَا وَتُسَاعِدُهَا", ok: true}, {t: "تَضْحَكُ عَلَيْهَا"}, {t: "تَتْرُكُهَا وَتَذْهَبُ"}]
      sources: [h-muslim-2699]

- key: end/2
  type: assessment
  ai_drafted: true
  instruction: "لَاحِظُوا طِفْلَكُمْ وَلَوِّنُوا النُّجُومَ"
  skills:
    - {skill: "ذِكْرُ اللهِ", t: "{يَذْكُرُ/تَذْكُرُ} اللهَ قَبْلَ الطَّعَامِ وَعِنْدَ النَّوْمِ وَالِاسْتِيقَاظِ."}
    - {skill: "الصِّدْقُ", t: "{يَقُولُ الْحَقَّ وَلَوْ أَخْطَأَ/تَقُولُ الْحَقَّ وَلَوْ أَخْطَأَتْ}."}
    - {skill: "بِرُّ الْوَالِدَيْنِ", t: "{يُسَاعِدُ أَهْلَهُ وَيُطِيعُهُمْ/تُسَاعِدُ أَهْلَهَا وَتُطِيعُهُمْ}."}
    - {skill: "الْمُشَارَكَةُ", t: "{يُشَارِكُ غَيْرَهُ فِي أَلْعَابِهِ/تُشَارِكُ غَيْرَهَا فِي أَلْعَابِهَا}."}
  note: "نَجْمَةٌ: بِدَايَةٌ، نَجْمَتَانِ: تَقَدُّمٌ، ثَلَاثُ نَجَمَاتٍ: عَادَةٌ ثَابِتَةٌ."
```

A game, not an exam: the child plays with a parent; the parents colour the stars of what they observe.

### front pages and the back page

```yaml
- key: front/1
  type: front-title

- key: front/2
  type: front-characters
  ai_drafted: true
  intros:
    - {who: huda, t: "سِتِّي هُدَى تَحْكِي لَنَا أَجْمَلَ الْحِكَايَاتِ، وَتُجِيبُ عَنْ أَسْئِلَتِنَا بِحُبٍّ."}
    - {who: reem, t: "رِيمُ أُخْتٌ كَبِيرَةٌ تُحِبُّ أَنْ تَسْأَلَ: لِمَاذَا؟"}
    - {who: salem, t: "سَالِمٌ أَخُوهَا الصَّغِيرُ، يَلْعَبُ وَيُخْطِئُ وَيَتَعَلَّمُ."}
    - {who: naanaa, t: "نَعْنَاعُ قِطَّتُهُمُ الْكَسُولُ، تُحِبُّ النَّوْمَ فِي الشَّمْسِ."}
    - {who: reader, t: "وَ{أَنْتَ/أَنْتِ} يَا {child} {بَطَلُ/بَطَلَةُ} هَذَا الْكِتَابِ!"}

- key: front/3
  type: front-how-to-use
  ai_drafted: true
  steps:
    - {icon: book, t: "أَقْرَأُ صَفْحَةً أَوْ صَفْحَتَيْنِ كُلَّ يَوْمٍ مَعَ أُمِّي أَوْ أَبِي."}
    - {icon: pencil, t: "أُلَوِّنُ وَأَرْسُمُ وَأَصِلُ وَأَخْتَارُ بِنَفْسِي."}
    - {icon: star, t: "أُلَوِّنُ نَجْمَةً كُلَّمَا أَنْهَيْتُ تَحَدِّيًا."}
    - {icon: stamp, t: "أُلْصِقُ خَتْمَ الْوَحْدَةِ فِي جَوَازِي حِينَ أُنْهِيهَا."}
  care_note: "في هذا الكتاب آيات من القرآن الكريم وأحاديث وأذكار؛ نرجو حفظه في مكان نظيف مرتفع، وعدم رميه أو وضع شيء فوقه، وأن يلمس الطفل صفحاته بيدين نظيفتين."

- key: front/5
  type: front-this-is-me
  ai_drafted: true
  prompts: ["اسْمِي:", "عُمْرِي:", "أُحِبُّ:", "أَصْدِقَائِي:"]
  draw_box: "{ارْسُمْ أُسْرَتَكَ/ارْسُمِي أُسْرَتَكِ} هُنَا"

- key: end/5
  type: back-page
  ai_drafted: true
  message: "{أَحْسَنْتَ/أَحْسَنْتِ} يَا {child}! {أَنْهَيْتَ رِحْلَتَكَ/أَنْهَيْتِ رِحْلَتَكِ} الْأُولَى مَعَنَا، وَنَلْتَقِي فِي الْكِتَابِ الْقَادِمِ إِنْ شَاءَ اللهُ."
  next: "الْكِتَابُ الثَّانِي: أُصَلِّي وَأَتَعَلَّمُ"
```

`icon` is an engine icon: `book`, `pencil`, `star`, `stamp`, `sticker`, `heart`, `family`, `speaker`, `crayon`,
`scissors`, `check`, `home`, `clock`, `talk`, `bulb`, `trophy`.

### passport, journey card, certificate (the samples s10, s11)

```yaml
- key: front/4
  type: passport
  ai_drafted: true
  gendered_title: "{جَوَازُ الْمُسْلِمِ الصَّغِيرِ/جَوَازُ الْمُسْلِمَةِ الصَّغِيرَةِ}"
  photo_slot: reader
  stamps_from: units.yaml
  challenge_stars: 8

- key: end/3
  type: passport
  ai_drafted: true
  title: بِطَاقَةُ رِحْلَةِ الْإِيمَانِ
  layout: journey-card
  challenge_stars: 8

- key: end/4
  type: certificate
  ai_drafted: true
  statement: "{أَنَا مُسْلِمٌ صَغِيرٌ/أَنَا مُسْلِمَةٌ صَغِيرَةٌ} أُحِبُّ اللهَ وَأَقْتَدِي بِنَبِيِّي مُحَمَّدٍ ﷺ"
  fields: [name, character, date, parent_signature]
  reviewed_by_line: false
```

The passport shows a stamp for each unit of the volume (from `units.yaml`) and the reader's character; the
certificate the child's name, character and the date. `reviewed_by_line` stays `false` until the scholar agrees.

### home-challenge and cut-paste (no volume places them yet)

```yaml
- key: u-family1/l1-2
  type: home-challenge
  ai_drafted: true
  instruction: "{لَوِّنْ/لَوِّنِي} نَجْمَةً كُلَّ يَوْمٍ"
  challenge: "أُسَاعِدُ أَهْلِي فِي عَمَلٍ وَاحِدٍ كُلَّ يَوْمٍ."
  steps: ["أُرَتِّبُ سَرِيرِي.", "أَضَعُ الصُّحُونَ فِي مَكَانِهَا.", "أَسْقِي النَّبَاتَاتِ."]
  days: 7
  reward: "{بَطَلُ/بَطَلَةُ} الْبَيْتِ!"

- key: u-blessings/l1-3
  type: cut-paste
  ai_drafted: true
  instruction: "{قُصَّ وَأَلْصِقْ/قُصِّي وَأَلْصِقِي} بِالتَّرْتِيبِ"
  pieces:
    - {pic: seed, t: "بَذْرَةٌ"}
    - {pic: sprout, t: "نَبْتَةٌ"}
    - {pic: tree, t: "شَجَرَةٌ"}
    - {pic: apple, t: "ثَمَرَةٌ"}
```

Write `pieces` in the right order: the strip to cut prints them shuffled, the board above has a numbered slot
for each (or `slots: [...]` labels them). No sacred text and no source on either type.

### Older thin types

`final-assessment` (`skills` only) and `my-day-with-allah` (= `day`) still work; prefer `assessment` and `day`.

## 6. Before you hand over

1. `--check` → `0 error(s)`; read every warning (an unplanned source is fine when it is the right one).
2. Render the pages you wrote (`--only u-allah/`) for a girl and a boy and look at them; nothing may be cut off
   (the render refuses text that does not fit — shorten it).
3. List in your report: sources you needed that are not in the register, every `scholar_decision` point the
   pages touch, and any wording you were unsure of. Have a language reviewer check every child-facing line.
