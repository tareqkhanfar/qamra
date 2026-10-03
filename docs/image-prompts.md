# برومبتات الصور لقمرة

> لطارق: انسخ كل برومبت كما هو (هو كامل لحاله: الأسلوب والتكوين والقواعد كلها جوّاه) والصقه بأداة توليد صور قوية
> (Nano Banana Pro أو GPT Image أو Midjourney). ابعتلي الصور، أو حطّها بالمجلد اللي تحت، وأنا بقرّر وين تروح.
> البرومبتات بالإنجليزي لأن الأدوات بتفهمها أدق. أُنشئ الملف في 2026-10-02 (الإضافة 11).

## كيف تشتغل

1. **المكان والاسم:** احفظ كل صورة باسمها المكتوب بالعنوان داخل `design/incoming/` (مثلًا `design/incoming/C1-qamour-3d.png`). صيغة PNG أو JPG، وبأعلى دقة بتعطيها الأداة (2000 بكسل على الأقل بالضلع الطويل؛ أنا بكبّرها للطباعة إذا لزم).
2. **النسبة:** مكتوبة عند كل صورة. اختارها بالأداة قبل التوليد.
3. **ممنوع بكل الصور:** أي كتابة أو حروف أو أرقام أو شعارات أو ماركات أو أندية أو مشاهير. كل الكتابة بنحطها إحنا بالكود.
4. **الثبات:** للشخصيات، ولّد ورقة الشخصية أولًا، وبعدين استعملها كصورة مرجع (reference image) لما تولّد نفس الشخصية بأسلوب ثاني أو بمشهد، عشان يضل شكلها واحد.
5. **جرّب أكثر من نسخة:** خذ 2–4 نسخ من كل برومبت وابعتلي الأحلى (أو كلهم وأنا بختار).
6. **ما بدي:** صور فيها طفلنا القارئ. الطفل بنضيفه إحنا من صورته بالنظام. المكان الفاضي بالخلفيات مقصود.

## الأولويات

| الأولوية | شو | ليش | العدد |
|---|---|---|---|
| 1 (هلأ) | نماذج الكتاب (B)، قمّور والمعلّمة وزملاء الصف (C1–C6)، خلفيات غلاف التخرّج (D1–D6)، عناصر التصميم (E) | تجربة إعادة تصميم «يوم تخرّج ليان» | 21 |
| 2 | صور الموقع (A)، باقي الشخصيات (C7–C17)، أغلفة «أوّل يوم في الروضة» و«ضيفنا الصغير» (D7–D10) | الموقع وباقي الكتب الأساسية | 25 |
| 3 | «قلبي يعرف الله» (F)، أغلفة الدوسيات (G) | بعد موافقتك على المقترح وموافقة المشرف | 31 |

**المجموع: 77 صورة.** ابدأ بالأولوية 1.

## أسماء الأساليب (للتوضيح)

- **سينمائي ثلاثي الأبعاد (3D):** شكل أفلام الرسوم المتحركة ثلاثية الأبعاد، إضاءة سينمائية وألوان غنية.
- **مائي فاخر (watercolor):** ألوان مائية دافئة بتباين قوي وظلال عميقة، مش باهتة.
- **كرتون ملوّن (cartoon):** رسم ثنائي الأبعاد بخطوط واضحة وألوان مشبعة، لدوسيات الأنشطة و«قلبي يعرف الله».

## صور الموقع (A) · أولوية 2

صور واقعية (فوتوغرافية) لأماكن الموقع العشرة الموجودة بـ `apps/web/public/photos/README.md`. أي كتاب بالصورة لازم يكون
غلافه سادة، وأنا بركّب عليه غلافنا الحقيقي. الموقع ما بيقول إن اللي بالصور زبائن.

### A1 · `A1-hero-reading.png`

- **مكانها:** الصفحة الرئيسية، أول ما تفتح
- **النسبة والحجم:** 3:2 أفقي · 2400 بكسل أو أكثر

```text
Photorealistic lifestyle photograph, natural soft window light, shot on a full-frame camera with a 50 mm lens at f/2, shallow depth of field, gentle warm color grade (creams, honey, soft indigo accents), clean and uncluttered, premium editorial feel. Real-looking people with natural skin, modest clothing. A 5-year-old girl with dark curly hair sits cross-legged on embroidered floor cushions by a big arched window, holding a large square hardcover picture book open on her lap, looking at it with delighted surprise and a big smile. Her mother, in a soft dusty-rose hijab and a cream cardigan, sits just behind her, leaning in and smiling. Warm late-afternoon golden light from the window. The two of them sit slightly right of center; soft calm wall space on the left side. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Any book in the picture has a completely plain cover with no printing (our real cover is added later), and its open pages show only soft blurred colors, never readable text. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### A2 · `A2-first-day.png`

- **مكانها:** صفحة «كيف يعمل»، رأس الصفحة (على التابلت والكمبيوتر)
- **النسبة والحجم:** 3:2 أفقي · 2400 بكسل أو أكثر

```text
Photorealistic lifestyle photograph, natural soft window light, shot on a full-frame camera with a 50 mm lens at f/2, shallow depth of field, gentle warm color grade (creams, honey, soft indigo accents), clean and uncluttered, premium editorial feel. Real-looking people with natural skin, modest clothing. Morning of the first kindergarten day: a 4-year-old boy with a small navy backpack holds his father's hand in front of a green arched kindergarten gate set in an old stone wall covered with pink bougainvillea, a lemon tree beside it. Seen from slightly behind and to the side: the boy looks up at his father with a brave, excited face; the father (short beard, light-blue shirt) smiles down at him. Soft morning sun. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Any book in the picture has a completely plain cover with no printing (our real cover is added later), and its open pages show only soft blurred colors, never readable text. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### A3 · `A3-graduation-class.png`

- **مكانها:** صفحة الروضات (رأس الصفحة) وبطاقة الروضات بالرئيسية
- **النسبة والحجم:** 3:2 أفقي · 2400 بكسل أو أكثر

```text
Photorealistic lifestyle photograph, natural soft window light, shot on a full-frame camera with a 50 mm lens at f/2, shallow depth of field, gentle warm color grade (creams, honey, soft indigo accents), clean and uncluttered, premium editorial feel. Real-looking people with natural skin, modest clothing. Five kindergarten children aged 5–6 on a small wooden stage with sage-green curtains and colorful triangle bunting, wearing night-blue graduation gowns with gold sashes and night-blue caps with golden tassels; the girls' hair shows under their caps (no child wears a hijab). They cheer and toss their caps up, laughing. Warm stage light; the blurred backs of parents' heads and raised phones in the bottom foreground. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Any book in the picture has a completely plain cover with no printing (our real cover is added later), and its open pages show only soft blurred colors, never readable text. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### A4 · `A4-family-book-table.png`

- **مكانها:** صفحة منتج «مغامراتي مع عائلتي»
- **النسبة والحجم:** 3:2 أفقي · 2400 بكسل أو أكثر

```text
Photorealistic lifestyle photograph, natural soft window light, shot on a full-frame camera with a 50 mm lens at f/2, shallow depth of field, gentle warm color grade (creams, honey, soft indigo accents), clean and uncluttered, premium editorial feel. Real-looking people with natural skin, modest clothing. A family around a low round wooden table in a cozy living room: a mother in a sage-green hijab, a father, a 6-year-old girl and a 3-year-old boy, all leaning over an open spiral-bound activity book, laughing and pointing; crayons scattered, a plate of grapes, glasses of mint tea. Warm evening lamp light, patterned tile floor and embroidered cushions. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Any book in the picture has a completely plain cover with no printing (our real cover is added later), and its open pages show only soft blurred colors, never readable text. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### A5 · `A5-workbook-tracing.png`

- **مكانها:** صفحة «دوسية التأسيس» وقسم الأنشطة بصفحة «كيف يعمل»
- **النسبة والحجم:** 1:1 مربع · 2400 بكسل أو أكثر

```text
Photorealistic lifestyle photograph, natural soft window light, shot on a full-frame camera with a 50 mm lens at f/2, shallow depth of field, gentle warm color grade (creams, honey, soft indigo accents), clean and uncluttered, premium editorial feel. Real-looking people with natural skin, modest clothing. Close-up, top-down view of a 5-year-old's hand tracing dotted guide lines on a worksheet with a chunky green crayon. The worksheet shows only soft grey dotted curves and a small hand-drawn moon doodle, NO readable letters; the white wire spiral binding runs along the right edge. Light wooden table, a few crayons, a glass of milk at the corner, soft daylight. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Any book in the picture has a completely plain cover with no printing (our real cover is added later), and its open pages show only soft blurred colors, never readable text. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### A6 · `A6-journey-qr.png`

- **مكانها:** صفحة «رحلتي الأولى للتعلّم» (رمز QR للصوت)
- **النسبة والحجم:** 3:2 أفقي · 2400 بكسل أو أكثر

```text
Photorealistic lifestyle photograph, natural soft window light, shot on a full-frame camera with a 50 mm lens at f/2, shallow depth of field, gentle warm color grade (creams, honey, soft indigo accents), clean and uncluttered, premium editorial feel. Real-looking people with natural skin, modest clothing. A 4-year-old girl and her father at a kitchen table: the father holds a smartphone above an open spiral workbook as if scanning a small square printed on the page; the girl leans in with a huge smile, listening. The square on the page is a plain light-grey patch with no pattern (our real code is added later); the phone screen is a soft blank glow with no interface. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Any book in the picture has a completely plain cover with no printing (our real cover is added later), and its open pages show only soft blurred colors, never readable text. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### A7 · `A7-grandma-voice.png`

- **مكانها:** صفحة «كيف يعمل»، قسم «صوت أهلي»
- **النسبة والحجم:** 3:2 أفقي · 2400 بكسل أو أكثر

```text
Photorealistic lifestyle photograph, natural soft window light, shot on a full-frame camera with a 50 mm lens at f/2, shallow depth of field, gentle warm color grade (creams, honey, soft indigo accents), clean and uncluttered, premium editorial feel. Real-looking people with natural skin, modest clothing. Evening at home: a grandmother in her late sixties, in a white embroidered headscarf and a black thobe with red tatreez on the chest panel, holds a smartphone close and records her voice, smiling warmly, while her 5-year-old grandson cuddles against her shoulder with his eyes closed in happiness. Warm lamp light, floor cushions. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Any book in the picture has a completely plain cover with no printing (our real cover is added later), and its open pages show only soft blurred colors, never readable text. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### A8 · `A8-gift-box.png`

- **مكانها:** صفحة الأسعار، قسم الإضافات
- **النسبة والحجم:** 1:1 مربع · 2400 بكسل أو أكثر

```text
Photorealistic lifestyle photograph, natural soft window light, shot on a full-frame camera with a 50 mm lens at f/2, shallow depth of field, gentle warm color grade (creams, honey, soft indigo accents), clean and uncluttered, premium editorial feel. Real-looking people with natural skin, modest clothing. Three-quarter top-down view of a premium gift box (cream box with a night-blue satin ribbon) lying open on a wooden table; inside, a square hardcover book nestled in cream tissue paper with a small blank card tucked beside it; dried flowers, a small brass lantern and a sprig of olive leaves around it. Soft daylight. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Any book in the picture has a completely plain cover with no printing (our real cover is added later), and its open pages show only soft blurred colors, never readable text. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### A9 · `A9-books-stack.png`

- **مكانها:** صفحة دوسيات الأنشطة (رأسها) والشريط بالرئيسية
- **النسبة والحجم:** 1:1 مربع · 2400 بكسل أو أكثر

```text
Photorealistic lifestyle photograph, natural soft window light, shot on a full-frame camera with a 50 mm lens at f/2, shallow depth of field, gentle warm color grade (creams, honey, soft indigo accents), clean and uncluttered, premium editorial feel. Real-looking people with natural skin, modest clothing. A neat stack of four square hardcover picture books and two portrait spiral-bound activity books on a light wooden table against a cream wall; the plain covers and spines are night blue, sage green, coral and honey gold with no printing at all; a small potted plant and a cup of colored pencils beside them. Soft daylight, gentle shadows. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Any book in the picture has a completely plain cover with no printing (our real cover is added later), and its open pages show only soft blurred colors, never readable text. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### A10 · `A10-kindergarten-teacher.png`

- **مكانها:** صفحة الروضات، جنب نموذج طلب العرض
- **النسبة والحجم:** 3:2 أفقي · 2400 بكسل أو أكثر

```text
Photorealistic lifestyle photograph, natural soft window light, shot on a full-frame camera with a 50 mm lens at f/2, shallow depth of field, gentle warm color grade (creams, honey, soft indigo accents), clean and uncluttered, premium editorial feel. Real-looking people with natural skin, modest clothing. A kindergarten teacher in her early thirties, in a soft cream hijab and a long sage cardigan, sits on a small wooden chair reading a square picture book aloud to a semicircle of 4–5-year-olds sitting on a rug, who listen wide-eyed. Bright classroom with low wooden shelves of colorful wooden toys and big arched windows; nothing written anywhere in the room. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Any book in the picture has a completely plain cover with no printing (our real cover is added later), and its open pages show only soft blurred colors, never readable text. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

## نماذج الكتاب للعرض (B) · أولوية 1

صور منتج واقعية فيها كتاب **غلافه أبيض سادة**. أنا بركّب عليها غلاف كل طلب وكل قصة بالكود، فبتطلع صور عرض
للموقع والإعلانات تلقائيًا. المهم: حواف الغلاف حادة وواضحة، وكعب الكتاب على **اليمين** (كتاب عربي).

### B1 · `B1-mockup-hardcover-angle.png`

- **مكانها:** صورة الكتاب المقوّى بالموقع والإعلانات
- **النسبة والحجم:** 1:1 مربع · 3000 بكسل

```text
Professional product photograph: a single closed square hardcover children's book (21 × 21 cm, about 1.2 cm thick) lying on a soft cream linen tablecloth, rotated about 12° counter-clockwise, photographed from above at a gentle 25° angle. The front cover is completely blank, flat matte pure white, with sharp straight edges (it will be replaced by our cover art). It is an Arabic book, so the spine is on the RIGHT edge: show the rounded spine edge and the board thickness, with crisp page-block lines along the left and bottom edges. Soft natural window light from the upper left and a gentle realistic contact shadow. Minimal props: a small sprig of olive leaves and two crayons at the bottom-left corner. Sharp focus on the whole book. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### B2 · `B2-mockup-open-spread.png`

- **مكانها:** صورة الكتاب مفتوح على صفحتين
- **النسبة والحجم:** 3:2 أفقي · 3000 بكسل

```text
Professional product photograph: a square hardcover children's picture book lying open flat on a cream linen surface, seen from directly above with a very slight tilt. Both pages are completely blank matte white, with a natural soft curve and shadow at the center gutter; the hard cover's edges show around the pages. Soft even window light, gentle shadow under the book. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### B3 · `B3-mockup-stack.png`

- **مكانها:** صورة مجموعة كتب (للعروض)
- **النسبة والحجم:** 1:1 مربع · 3000 بكسل

```text
Professional product photograph, eye-level three-quarter view: three closed square hardcover children's books stacked loosely with slight rotation on a light oak table against a warm cream wall. The top book's front cover is completely blank flat white with sharp edges; the spines of the two lower books are plain night blue and plain sage green with no printing. Soft daylight, a small blurred potted olive tree in the background. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### B4 · `B4-mockup-spiral.png`

- **مكانها:** صورة الدوسية («رحلتي الأولى»، «التأسيس»، «قلبي يعرف الله»)
- **النسبة والحجم:** 1:1 مربع · 3000 بكسل

```text
Professional product photograph: a portrait spiral-bound activity book (21 × 28 cm) lying on a light wooden desk, rotated about 8°, photographed from above at a gentle angle. White double-loop wire binding along the RIGHT edge. The front cover is completely blank flat matte white with sharp edges. A few chunky crayons and a pencil beside it, soft daylight from the left, gentle realistic shadow. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

## شخصيات ثابتة لكتب القصص (C)

هاي الشخصيات بتنعاد بكل كتاب (مش طفلنا). لما يكون شكلها ثابت، المعلّمة ما بتتغيّر بين الصفحات وقمّور ما بيتحوّل من كرة
لهلال (مشاكل التجربة 8 و9). **ولّد نسخة 3D أولًا، وبعدين استعملها مرجعًا لنسخة الألوان المائية.**

### C1 · `C1-qamour-3d.png`

- **مكانها:** قمّور بكتب «قمرة سحري» (3D)
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 1

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. Qamour, a tiny friendly moon creature and the hero's companion: a soft, plump crescent-moon body (a thick C shape opening to the right), pale honey-gold, softly glowing from inside, about the size of a house cat. Its face sits on the thick middle of the crescent: two small shiny black dot eyes, a tiny happy smile, round rosy cheeks, and a small five-pointed star-shaped golden freckle on its left cheek. Two stubby little arms, no legs. It floats a few centimeters above the ground with a faint trail of golden sparkles. The crescent shape never changes. Style: polished 3D animated-film look — stylized proportions (slightly large head, big expressive eyes), soft subsurface-scattering skin, cinematic rim light and gentle volumetric glow, soft global illumination, rich saturated warm palette (night blue, honey gold, sage green, coral), clean stylized materials (soft fabric, matte painted wood, smooth limestone), shallow depth of field, a few floating golden light particles. Warm and family-friendly; not photorealistic, not glossy plastic dolls; do not imitate any existing film, studio, game or toy character. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C2 · `C2-qamour-watercolor.png`

- **مكانها:** قمّور بالكتب المائية
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 1 · استعمل C1 مرجعًا

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. Qamour, a tiny friendly moon creature and the hero's companion: a soft, plump crescent-moon body (a thick C shape opening to the right), pale honey-gold, softly glowing from inside, about the size of a house cat. Its face sits on the thick middle of the crescent: two small shiny black dot eyes, a tiny happy smile, round rosy cheeks, and a small five-pointed star-shaped golden freckle on its left cheek. Two stubby little arms, no legs. It floats a few centimeters above the ground with a faint trail of golden sparkles. The crescent shape never changes. Style: premium watercolor-and-gouache children's picture-book painting on warm textured paper — rich saturated color, deep indigo and violet shadows, glowing honey-gold highlights, strong contrast, golden-hour or moonlit light, soft wet edges with crisp detail on faces and hands, visible paper grain, atmospheric depth with soft foreground framing elements. No flat pale backgrounds, no harsh black outlines, no 3D-render look, no anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C3 · `C3-teacher-3d.png`

- **مكانها:** المعلّمة (أول يوم، التخرّج)
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 1

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. The kindergarten teacher: a kind woman in her early thirties, warm light-olive skin, a gentle round face, warm brown eyes and a soft smile, a sage-green hijab wrapped neatly, a long cream knitted cardigan over a dusty-rose ankle-length dress, a short wooden-bead necklace, flat brown shoes. Style: polished 3D animated-film look — stylized proportions (slightly large head, big expressive eyes), soft subsurface-scattering skin, cinematic rim light and gentle volumetric glow, soft global illumination, rich saturated warm palette (night blue, honey gold, sage green, coral), clean stylized materials (soft fabric, matte painted wood, smooth limestone), shallow depth of field, a few floating golden light particles. Warm and family-friendly; not photorealistic, not glossy plastic dolls; do not imitate any existing film, studio, game or toy character. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C4 · `C4-teacher-watercolor.png`

- **مكانها:** المعلّمة بالمائي
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 1 · استعمل C3 مرجعًا

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. The kindergarten teacher: a kind woman in her early thirties, warm light-olive skin, a gentle round face, warm brown eyes and a soft smile, a sage-green hijab wrapped neatly, a long cream knitted cardigan over a dusty-rose ankle-length dress, a short wooden-bead necklace, flat brown shoes. Style: premium watercolor-and-gouache children's picture-book painting on warm textured paper — rich saturated color, deep indigo and violet shadows, glowing honey-gold highlights, strong contrast, golden-hour or moonlit light, soft wet edges with crisp detail on faces and hands, visible paper grain, atmospheric depth with soft foreground framing elements. No flat pale backgrounds, no harsh black outlines, no 3D-render look, no anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C5 · `C5-classmates-3d.png`

- **مكانها:** زملاء الصف (أول يوم، التخرّج، كتاب الصف)
- **النسبة والحجم:** 3:2 أفقي · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 1

```text
Group character reference sheet on a pure white background, exactly four different children and no one else: top row, the four children full-body from the front, left to right in the order listed; middle row, the same four in the same order in three-quarter view; bottom row, the same four smiling head close-ups in the same order. Twelve figures in total, never a fifth child or a repeated one. Even neutral lighting; each child identical in every view; no scenery. Four kindergarten classmates aged 5–6 standing in a row, all with distinct, consistent designs: (1) a boy with short wavy black hair and round tortoiseshell glasses, mustard-yellow t-shirt and navy trousers; (2) a girl with a short dark bob and a lavender headband, coral long-sleeved dress and white sneakers; (3) a boy with straight light-brown hair and a cowlick, navy hoodie and gray trousers; (4) a girl with two neat low dark-brown braids tied with yellow ribbons, sky-blue pinafore dress over a white shirt. All four are Palestinian / Levantine Arab children: light-olive to warm-tan skin and dark-brown to black hair, with natural variety within that range. Style: polished 3D animated-film look — stylized proportions (slightly large head, big expressive eyes), soft subsurface-scattering skin, cinematic rim light and gentle volumetric glow, soft global illumination, rich saturated warm palette (night blue, honey gold, sage green, coral), clean stylized materials (soft fabric, matte painted wood, smooth limestone), shallow depth of field, a few floating golden light particles. Warm and family-friendly; not photorealistic, not glossy plastic dolls; do not imitate any existing film, studio, game or toy character. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C6 · `C6-classmates-watercolor.png`

- **مكانها:** زملاء الصف بالمائي
- **النسبة والحجم:** 3:2 أفقي · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 1 · استعمل C5 مرجعًا

```text
Group character reference sheet on a pure white background, exactly four different children and no one else: top row, the four children full-body from the front, left to right in the order listed; middle row, the same four in the same order in three-quarter view; bottom row, the same four smiling head close-ups in the same order. Twelve figures in total, never a fifth child or a repeated one. Even neutral lighting; each child identical in every view; no scenery. Four kindergarten classmates aged 5–6 standing in a row, all with distinct, consistent designs: (1) a boy with short wavy black hair and round tortoiseshell glasses, mustard-yellow t-shirt and navy trousers; (2) a girl with a short dark bob and a lavender headband, coral long-sleeved dress and white sneakers; (3) a boy with straight light-brown hair and a cowlick, navy hoodie and gray trousers; (4) a girl with two neat low dark-brown braids tied with yellow ribbons, sky-blue pinafore dress over a white shirt. All four are Palestinian / Levantine Arab children: light-olive to warm-tan skin and dark-brown to black hair, with natural variety within that range. Style: premium watercolor-and-gouache children's picture-book painting on warm textured paper — rich saturated color, deep indigo and violet shadows, glowing honey-gold highlights, strong contrast, golden-hour or moonlit light, soft wet edges with crisp detail on faces and hands, visible paper grain, atmospheric depth with soft foreground framing elements. No flat pale backgrounds, no harsh black outlines, no 3D-render look, no anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C7 · `C7-qamour-cartoon.png`

- **مكانها:** قمّور بكتب التلوين والكرتون
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 2 · استعمل C1 مرجعًا

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. Qamour, a tiny friendly moon creature and the hero's companion: a soft, plump crescent-moon body (a thick C shape opening to the right), pale honey-gold, softly glowing from inside, about the size of a house cat. Its face sits on the thick middle of the crescent: two small shiny black dot eyes, a tiny happy smile, round rosy cheeks, and a small five-pointed star-shaped golden freckle on its left cheek. Two stubby little arms, no legs. It floats a few centimeters above the ground with a faint trail of golden sparkles. The crescent shape never changes. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C8 · `C8-mother-3d.png`

- **مكانها:** الأم (حكايات البيت، «ضيفنا الصغير»)
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 2

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. The mother: a woman in her early thirties, warm light-olive skin, kind almond-shaped brown eyes, a dusty-rose hijab, a long navy cardigan over a cream ankle-length dress, small gold stud earrings hidden by the hijab, comfortable flat shoes. Style: polished 3D animated-film look — stylized proportions (slightly large head, big expressive eyes), soft subsurface-scattering skin, cinematic rim light and gentle volumetric glow, soft global illumination, rich saturated warm palette (night blue, honey gold, sage green, coral), clean stylized materials (soft fabric, matte painted wood, smooth limestone), shallow depth of field, a few floating golden light particles. Warm and family-friendly; not photorealistic, not glossy plastic dolls; do not imitate any existing film, studio, game or toy character. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C9 · `C9-mother-watercolor.png`

- **مكانها:** الأم بالمائي
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 2 · استعمل C8 مرجعًا

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. The mother: a woman in her early thirties, warm light-olive skin, kind almond-shaped brown eyes, a dusty-rose hijab, a long navy cardigan over a cream ankle-length dress, small gold stud earrings hidden by the hijab, comfortable flat shoes. Style: premium watercolor-and-gouache children's picture-book painting on warm textured paper — rich saturated color, deep indigo and violet shadows, glowing honey-gold highlights, strong contrast, golden-hour or moonlit light, soft wet edges with crisp detail on faces and hands, visible paper grain, atmospheric depth with soft foreground framing elements. No flat pale backgrounds, no harsh black outlines, no 3D-render look, no anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C10 · `C10-father-3d.png`

- **مكانها:** الأب
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 2

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. The father: a man in his mid-thirties, warm olive skin, short black hair, a short neat black beard, warm brown eyes and laugh lines, a light-blue button-up shirt with the sleeves rolled up, beige trousers, brown leather shoes, a simple wristwatch. Style: polished 3D animated-film look — stylized proportions (slightly large head, big expressive eyes), soft subsurface-scattering skin, cinematic rim light and gentle volumetric glow, soft global illumination, rich saturated warm palette (night blue, honey gold, sage green, coral), clean stylized materials (soft fabric, matte painted wood, smooth limestone), shallow depth of field, a few floating golden light particles. Warm and family-friendly; not photorealistic, not glossy plastic dolls; do not imitate any existing film, studio, game or toy character. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C11 · `C11-father-watercolor.png`

- **مكانها:** الأب بالمائي
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 2 · استعمل C10 مرجعًا

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. The father: a man in his mid-thirties, warm olive skin, short black hair, a short neat black beard, warm brown eyes and laugh lines, a light-blue button-up shirt with the sleeves rolled up, beige trousers, brown leather shoes, a simple wristwatch. Style: premium watercolor-and-gouache children's picture-book painting on warm textured paper — rich saturated color, deep indigo and violet shadows, glowing honey-gold highlights, strong contrast, golden-hour or moonlit light, soft wet edges with crisp detail on faces and hands, visible paper grain, atmospheric depth with soft foreground framing elements. No flat pale backgrounds, no harsh black outlines, no 3D-render look, no anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C12 · `C12-grandma-3d.png`

- **مكانها:** الجدّة
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 2

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. The grandmother (Sitti): a woman in her late sixties with gentle wrinkles and a warm smile, a white embroidered headscarf, a traditional black Palestinian thobe with red cross-stitch tatreez on the chest panel and sleeves, a string of olive-wood prayer beads in her hand. Style: polished 3D animated-film look — stylized proportions (slightly large head, big expressive eyes), soft subsurface-scattering skin, cinematic rim light and gentle volumetric glow, soft global illumination, rich saturated warm palette (night blue, honey gold, sage green, coral), clean stylized materials (soft fabric, matte painted wood, smooth limestone), shallow depth of field, a few floating golden light particles. Warm and family-friendly; not photorealistic, not glossy plastic dolls; do not imitate any existing film, studio, game or toy character. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C13 · `C13-grandma-watercolor.png`

- **مكانها:** الجدّة بالمائي
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 2 · استعمل C12 مرجعًا

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. The grandmother (Sitti): a woman in her late sixties with gentle wrinkles and a warm smile, a white embroidered headscarf, a traditional black Palestinian thobe with red cross-stitch tatreez on the chest panel and sleeves, a string of olive-wood prayer beads in her hand. Style: premium watercolor-and-gouache children's picture-book painting on warm textured paper — rich saturated color, deep indigo and violet shadows, glowing honey-gold highlights, strong contrast, golden-hour or moonlit light, soft wet edges with crisp detail on faces and hands, visible paper grain, atmospheric depth with soft foreground framing elements. No flat pale backgrounds, no harsh black outlines, no 3D-render look, no anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C14 · `C14-grandpa-3d.png`

- **مكانها:** الجدّ
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 2

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. The grandfather (Sido): a man in his late sixties, a short white beard and grey mustache, kind eyes behind thin round glasses, a white-and-black checkered keffiyeh draped over his shoulders, a brown wool vest over a white shirt, dark trousers, a wooden walking cane. Style: polished 3D animated-film look — stylized proportions (slightly large head, big expressive eyes), soft subsurface-scattering skin, cinematic rim light and gentle volumetric glow, soft global illumination, rich saturated warm palette (night blue, honey gold, sage green, coral), clean stylized materials (soft fabric, matte painted wood, smooth limestone), shallow depth of field, a few floating golden light particles. Warm and family-friendly; not photorealistic, not glossy plastic dolls; do not imitate any existing film, studio, game or toy character. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C15 · `C15-grandpa-watercolor.png`

- **مكانها:** الجدّ بالمائي
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 2 · استعمل C14 مرجعًا

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. The grandfather (Sido): a man in his late sixties, a short white beard and grey mustache, kind eyes behind thin round glasses, a white-and-black checkered keffiyeh draped over his shoulders, a brown wool vest over a white shirt, dark trousers, a wooden walking cane. Style: premium watercolor-and-gouache children's picture-book painting on warm textured paper — rich saturated color, deep indigo and violet shadows, glowing honey-gold highlights, strong contrast, golden-hour or moonlit light, soft wet edges with crisp detail on faces and hands, visible paper grain, atmospheric depth with soft foreground framing elements. No flat pale backgrounds, no harsh black outlines, no 3D-render look, no anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C16 · `C16-baby-3d.png`

- **مكانها:** المولود الجديد بـ«ضيفنا الصغير»
- **النسبة والحجم:** 3:2 أفقي · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 2

```text
Character reference sheet on a pure white background, four views of the same baby in a row, even neutral lighting, no scenery. The new baby: a three-month-old baby, gender-neutral, round rosy cheeks, a tiny tuft of dark hair, swaddled in a soft cream blanket with a thin blue-and-red tatreez border. Show the baby asleep, awake and smiling, yawning, and held up in a carrier basket. Style: polished 3D animated-film look — stylized proportions (slightly large head, big expressive eyes), soft subsurface-scattering skin, cinematic rim light and gentle volumetric glow, soft global illumination, rich saturated warm palette (night blue, honey gold, sage green, coral), clean stylized materials (soft fabric, matte painted wood, smooth limestone), shallow depth of field, a few floating golden light particles. Warm and family-friendly; not photorealistic, not glossy plastic dolls; do not imitate any existing film, studio, game or toy character. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### C17 · `C17-baby-watercolor.png`

- **مكانها:** المولود الجديد بالمائي
- **النسبة والحجم:** 3:2 أفقي · 2048 بكسل أو أكثر
- **ملاحظة:** أولوية 2 · استعمل C16 مرجعًا

```text
Character reference sheet on a pure white background, four views of the same baby in a row, even neutral lighting, no scenery. The new baby: a three-month-old baby, gender-neutral, round rosy cheeks, a tiny tuft of dark hair, swaddled in a soft cream blanket with a thin blue-and-red tatreez border. Show the baby asleep, awake and smiling, yawning, and held up in a carrier basket. Style: premium watercolor-and-gouache children's picture-book painting on warm textured paper — rich saturated color, deep indigo and violet shadows, glowing honey-gold highlights, strong contrast, golden-hour or moonlit light, soft wet edges with crisp detail on faces and hands, visible paper grain, atmospheric depth with soft foreground framing elements. No flat pale backgrounds, no harsh black outlines, no 3D-render look, no anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

## خلفيات أغلفة كتب القصص (D)

الغلاف الجديد طبقات: **خلفية** (هاي الصور) + **الطفل** (من صورته، بالنظام) + **العنوان** (بالكود، بخط مصمَّم). عشان هيك
الخلفية فيها مكان فاضي مضاء بالوسط، وأعلاها هادي للعنوان، وما فيها ولا شخص. لكل قصة بنستعمل نفس الخلفية لكل الأطفال،
فالغلاف بيطلع فخم وثابت وأرخص.

### D1 · `D1-graduation-stage-3d.png`

- **مكانها:** غلاف «يوم تخرّجي»: مسرح الحفل (3D)
- **النسبة والحجم:** 1:1 مربع · 2560 بكسل أو أكثر
- **ملاحظة:** أولوية 1

```text
Square 1:1 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. A kindergarten graduation hall turned magical at the moment of the ceremony: a small wooden stage in the center with sage-green velvet curtains pulled open on both sides, a warm golden spotlight making a soft glowing circle on the empty stage floor, strings of colorful triangle bunting and glowing paper lanterns overhead, golden confetti and tiny star sparkles floating in the air, a few night-blue graduation caps with golden tassels flying gently upward, rows of empty wooden chairs softly out of focus in the bottom-corner foreground, high arched windows showing a deep night-blue evening sky. Mood: proud, joyful, magical. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: polished 3D animated-film look — stylized proportions (slightly large head, big expressive eyes), soft subsurface-scattering skin, cinematic rim light and gentle volumetric glow, soft global illumination, rich saturated warm palette (night blue, honey gold, sage green, coral), clean stylized materials (soft fabric, matte painted wood, smooth limestone), shallow depth of field, a few floating golden light particles. Warm and family-friendly; not photorealistic, not glossy plastic dolls; do not imitate any existing film, studio, game or toy character. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### D2 · `D2-graduation-stage-watercolor.png`

- **مكانها:** غلاف «يوم تخرّجي»: مسرح الحفل (مائي)
- **النسبة والحجم:** 1:1 مربع · 2560 بكسل أو أكثر
- **ملاحظة:** أولوية 1

```text
Square 1:1 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. A kindergarten graduation hall turned magical at the moment of the ceremony: a small wooden stage in the center with sage-green velvet curtains pulled open on both sides, a warm golden spotlight making a soft glowing circle on the empty stage floor, strings of colorful triangle bunting and glowing paper lanterns overhead, golden confetti and tiny star sparkles floating in the air, a few night-blue graduation caps with golden tassels flying gently upward, rows of empty wooden chairs softly out of focus in the bottom-corner foreground, high arched windows showing a deep night-blue evening sky. Mood: proud, joyful, magical. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Full-bleed: the painting fills the whole canvas edge to edge, with no white paper margin, border, frame or torn edge. Style: premium watercolor-and-gouache children's picture-book painting on warm textured paper — rich saturated color, deep indigo and violet shadows, glowing honey-gold highlights, strong contrast, golden-hour or moonlit light, soft wet edges with crisp detail on faces and hands, visible paper grain, atmospheric depth with soft foreground framing elements. No flat pale backgrounds, no harsh black outlines, no 3D-render look, no anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### D3 · `D3-graduation-hill-3d.png`

- **مكانها:** غلاف «يوم تخرّجي»: تلّة المستقبل (3D)
- **النسبة والحجم:** 1:1 مربع · 2560 بكسل أو أكثر
- **ملاحظة:** أولوية 1

```text
Square 1:1 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. A sunset hilltop above a small kindergarten building of cream limestone with arched windows and a green door down in the valley; a winding path of glowing golden stepping stones climbs up to an empty, flat, softly lit spot on the hilltop; gnarled old olive trees frame the left and right foreground; in the huge sky, paper planes and kites drift toward a big soft rising moon, a warm orange-to-indigo gradient with the first stars, and a few graduation caps float like birds. Mood: the dream of first grade ahead. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: polished 3D animated-film look — stylized proportions (slightly large head, big expressive eyes), soft subsurface-scattering skin, cinematic rim light and gentle volumetric glow, soft global illumination, rich saturated warm palette (night blue, honey gold, sage green, coral), clean stylized materials (soft fabric, matte painted wood, smooth limestone), shallow depth of field, a few floating golden light particles. Warm and family-friendly; not photorealistic, not glossy plastic dolls; do not imitate any existing film, studio, game or toy character. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### D4 · `D4-graduation-hill-watercolor.png`

- **مكانها:** غلاف «يوم تخرّجي»: تلّة المستقبل (مائي)
- **النسبة والحجم:** 1:1 مربع · 2560 بكسل أو أكثر
- **ملاحظة:** أولوية 1

```text
Square 1:1 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. A sunset hilltop above a small kindergarten building of cream limestone with arched windows and a green door down in the valley; a winding path of glowing golden stepping stones climbs up to an empty, flat, softly lit spot on the hilltop; gnarled old olive trees frame the left and right foreground; in the huge sky, paper planes and kites drift toward a big soft rising moon, a warm orange-to-indigo gradient with the first stars, and a few graduation caps float like birds. Mood: the dream of first grade ahead. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Full-bleed: the painting fills the whole canvas edge to edge, with no white paper margin, border, frame or torn edge. Style: premium watercolor-and-gouache children's picture-book painting on warm textured paper — rich saturated color, deep indigo and violet shadows, glowing honey-gold highlights, strong contrast, golden-hour or moonlit light, soft wet edges with crisp detail on faces and hands, visible paper grain, atmospheric depth with soft foreground framing elements. No flat pale backgrounds, no harsh black outlines, no 3D-render look, no anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### D5 · `D5-graduation-garden-3d.png`

- **مكانها:** غلاف «يوم تخرّجي»: حديقة الروضة ليلًا (3D)
- **النسبة والحجم:** 1:1 مربع · 2560 بكسل أو أكثر
- **ملاحظة:** أولوية 1

```text
Square 1:1 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. The kindergarten yard transformed on graduation night: a grapevine pergola strung with warm fairy lights and glowing paper lanterns, a lemon tree and a small slide and swings softly lit at the sides, fireflies and golden sparkles in the air, a big glowing full moon rising behind the pergola, and a soft path of light leading to an empty glowing spot in the center under the pergola. Deep night blue, honey gold and sage palette. Mood: cozy, magical, celebratory. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: polished 3D animated-film look — stylized proportions (slightly large head, big expressive eyes), soft subsurface-scattering skin, cinematic rim light and gentle volumetric glow, soft global illumination, rich saturated warm palette (night blue, honey gold, sage green, coral), clean stylized materials (soft fabric, matte painted wood, smooth limestone), shallow depth of field, a few floating golden light particles. Warm and family-friendly; not photorealistic, not glossy plastic dolls; do not imitate any existing film, studio, game or toy character. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### D6 · `D6-graduation-garden-watercolor.png`

- **مكانها:** غلاف «يوم تخرّجي»: حديقة الروضة ليلًا (مائي)
- **النسبة والحجم:** 1:1 مربع · 2560 بكسل أو أكثر
- **ملاحظة:** أولوية 1

```text
Square 1:1 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. The kindergarten yard transformed on graduation night: a grapevine pergola strung with warm fairy lights and glowing paper lanterns, a lemon tree and a small slide and swings softly lit at the sides, fireflies and golden sparkles in the air, a big glowing full moon rising behind the pergola, and a soft path of light leading to an empty glowing spot in the center under the pergola. Deep night blue, honey gold and sage palette. Mood: cozy, magical, celebratory. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Full-bleed: the painting fills the whole canvas edge to edge, with no white paper margin, border, frame or torn edge. Style: premium watercolor-and-gouache children's picture-book painting on warm textured paper — rich saturated color, deep indigo and violet shadows, glowing honey-gold highlights, strong contrast, golden-hour or moonlit light, soft wet edges with crisp detail on faces and hands, visible paper grain, atmospheric depth with soft foreground framing elements. No flat pale backgrounds, no harsh black outlines, no 3D-render look, no anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### D7 · `D7-first-day-3d.png`

- **مكانها:** غلاف «أوّل يوم في الروضة» (3D)
- **النسبة والحجم:** 1:1 مربع · 2560 بكسل أو أكثر
- **ملاحظة:** أولوية 2

```text
Square 1:1 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. Morning of the first kindergarten day: a narrow sloping street of warm limestone houses leads to the kindergarten's green arched gate set in an old stone wall covered with pink bougainvillea, with a lemon tree beside it; colorful patterned tiles on the path, soft golden sunbeams, floating soap-bubble sparkles and paper butterflies; the empty glowing spot is on the path just in front of the gate. Mood: excited, brave, a new beginning. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: polished 3D animated-film look — stylized proportions (slightly large head, big expressive eyes), soft subsurface-scattering skin, cinematic rim light and gentle volumetric glow, soft global illumination, rich saturated warm palette (night blue, honey gold, sage green, coral), clean stylized materials (soft fabric, matte painted wood, smooth limestone), shallow depth of field, a few floating golden light particles. Warm and family-friendly; not photorealistic, not glossy plastic dolls; do not imitate any existing film, studio, game or toy character. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### D8 · `D8-first-day-watercolor.png`

- **مكانها:** غلاف «أوّل يوم في الروضة» (مائي)
- **النسبة والحجم:** 1:1 مربع · 2560 بكسل أو أكثر
- **ملاحظة:** أولوية 2

```text
Square 1:1 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. Morning of the first kindergarten day: a narrow sloping street of warm limestone houses leads to the kindergarten's green arched gate set in an old stone wall covered with pink bougainvillea, with a lemon tree beside it; colorful patterned tiles on the path, soft golden sunbeams, floating soap-bubble sparkles and paper butterflies; the empty glowing spot is on the path just in front of the gate. Mood: excited, brave, a new beginning. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Full-bleed: the painting fills the whole canvas edge to edge, with no white paper margin, border, frame or torn edge. Style: premium watercolor-and-gouache children's picture-book painting on warm textured paper — rich saturated color, deep indigo and violet shadows, glowing honey-gold highlights, strong contrast, golden-hour or moonlit light, soft wet edges with crisp detail on faces and hands, visible paper grain, atmospheric depth with soft foreground framing elements. No flat pale backgrounds, no harsh black outlines, no 3D-render look, no anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### D9 · `D9-new-sibling-3d.png`

- **مكانها:** غلاف «ضيفنا الصغير» (3D)
- **النسبة والحجم:** 1:1 مربع · 2560 بكسل أو أكثر
- **ملاحظة:** أولوية 2

```text
Square 1:1 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. Sunrise in the family home: a cozy room with a big arched window full of golden morning light, a wooden cradle with an embroidered blanket at one side, a felt mobile of little moons and stars hanging above it, rose petals and soft sparkles in the air, floor cushions with tatreez pillows in the foreground corners, and an empty glowing spot in the center of the patterned tile floor in front of the cradle. Mood: tender, a proud big sibling. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: polished 3D animated-film look — stylized proportions (slightly large head, big expressive eyes), soft subsurface-scattering skin, cinematic rim light and gentle volumetric glow, soft global illumination, rich saturated warm palette (night blue, honey gold, sage green, coral), clean stylized materials (soft fabric, matte painted wood, smooth limestone), shallow depth of field, a few floating golden light particles. Warm and family-friendly; not photorealistic, not glossy plastic dolls; do not imitate any existing film, studio, game or toy character. Never add a translucent overlay, white haze rectangle, panel or band across the top: the ceiling, wall and window continue naturally. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### D10 · `D10-new-sibling-watercolor.png`

- **مكانها:** غلاف «ضيفنا الصغير» (مائي)
- **النسبة والحجم:** 1:1 مربع · 2560 بكسل أو أكثر
- **ملاحظة:** أولوية 2

```text
Square 1:1 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. Sunrise in the family home: a cozy room with a big arched window full of golden morning light, a wooden cradle with an embroidered blanket at one side, a felt mobile of little moons and stars hanging above it, rose petals and soft sparkles in the air, floor cushions with tatreez pillows in the foreground corners, and an empty glowing spot in the center of the patterned tile floor in front of the cradle. Mood: tender, a proud big sibling. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Full-bleed: the painting fills the whole canvas edge to edge, with no white paper margin, border, frame or torn edge. Style: premium watercolor-and-gouache children's picture-book painting on warm textured paper — rich saturated color, deep indigo and violet shadows, glowing honey-gold highlights, strong contrast, golden-hour or moonlit light, soft wet edges with crisp detail on faces and hands, visible paper grain, atmospheric depth with soft foreground framing elements. No flat pale backgrounds, no harsh black outlines, no 3D-render look, no anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

> باقي القصص («رحلة إلى القمر»، «قارب الأحلام»، «حارس النجوم»، «موسم الزيتون»، «أصدقاء الحارة») بكتبلك خلفياتها بعد ما توافق على التجربة.

## عناصر تصميم للصفحات (E) · أولوية 1

عناصر بتنحط حوالين النص بصفحات القصة والإهداء والذكريات، عشان الصفحة تبيّن مصمَّمة مش قالب أبيض. الخلفية بيضاء
صافية عشان أقصّها.

### E1 · `E1-paper-cream.png`

- **مكانها:** خلفية هادية لصفحات النص والإهداء
- **النسبة والحجم:** 1:1 مربع · 3000 بكسل

```text
A flat, front-on, evenly lit scan of plain warm cream art paper (about #FBF4E6) with a subtle natural fiber grain, seamless and tileable, with no vignette, stains, folds or edges. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### E2 · `E2-watercolor-washes.png`

- **مكانها:** غيمة النص بالكتب المائية (بدل الصندوق الأبيض)
- **النسبة والحجم:** 3:2 أفقي · 3000 بكسل

```text
Six separate soft watercolor wash shapes isolated on pure white, arranged in a 3 × 2 grid with plenty of white space between them: two organic cloud shapes, two long horizontal scroll or ribbon shapes, one round blob and one soft speech-bubble shape. Colors: pale honey, light cream-gold, soft sky blue, light sage, pale coral, light lavender. Each has soft wet edges, a gentle bloom and a slightly darker pigment rim, with a smooth light interior that dark text can sit on. No outlines. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### E3 · `E3-moon-portrait-frame.png`

- **مكانها:** إطار صورة الطفل بصفحة الإهداء
- **النسبة والحجم:** 1:1 مربع · 3000 بكسل

```text
An ornate decorative portrait frame isolated on pure white: a large golden crescent moon wrapped around a circular frame, with delicate gold filigree inspired by Palestinian tatreez cross-stitch patterns and tiny five-pointed stars hanging from the crescent's tips; a subtle metallic gold sheen with warm highlights. The inside of the circle is empty pure white. Front view, centered, flat even lighting. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### E4 · `E4-polaroid-tape.png`

- **مكانها:** صفحة «ذكرياتنا»
- **النسبة والحجم:** 3:2 أفقي · 3000 بكسل

```text
Three blank instant-photo frames (white borders, thicker bottom border), slightly rotated, each held at the top by a strip of washi tape: pastel coral with tiny dots, sage green with stripes, honey yellow with tiny moons. The photo areas are empty light grey. Isolated on pure white with soft realistic shadows, top-down. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### E5 · `E5-crayon-doodles.png`

- **مكانها:** صفحة «ارسم أجمل لحظة»
- **النسبة والحجم:** 3:2 أفقي · 3000 بكسل

```text
A sheet of children's wax-crayon doodles isolated on pure white: stars, hearts, a smiling sun, a crescent moon, swirls, little flowers, a rainbow arc, zigzags and dots, in bright crayon colors (red, orange, yellow, green, blue, purple), with real waxy crayon texture and uneven pressure, spread out with space between them so each can be cut out. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

## «قلبي يعرف الله» (F) · أولوية 3

**قواعد السلسلة، لازم تتحقّق بكل صورة:** ما بنصوّر الله ولا أي نبي ولا ملَك ولا صحابي، ولا حتى بظلّ أو نور أو شكل
مغطّى. مشاهد قصص الأنبياء فاضية من الناس تمامًا. ولا آيات ولا خط عربي ولا أي كتابة. الشخصيات المتكرّرة: ريم (7 سنين)،
سالم (5 سنين)، ستّي هدى (الجدّة الحكّاءة)، والقطّة نعناع. الأسلوب: كرتون ملوّن، عشان يمشي مع صفحات الدوسية.
ولّد أوراق الشخصيات F1–F4 أولًا واستعملها مرجعًا بالمشاهد.

### F1 · `F1-reem.png`

- **مكانها:** شخصية ريم بكل المجلدات
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. Reem, a 7-year-old girl, curious and bright: warm light-olive skin, big brown eyes, dark-brown hair in a low ponytail with a coral hair clip, a mustard-yellow long-sleeved top under a teal pinafore dress, white socks and brown shoes, often holding a small notebook. Add a second full-body front view of the same girl at prayer time, wearing a simple white prayer scarf covering her hair and a long white prayer dress. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F2 · `F2-salem.png`

- **مكانها:** شخصية سالم بكل المجلدات
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. Salem, a 5-year-old boy, cheerful and a little mischievous: light-olive skin, a round face with freckles across his nose, short messy black hair, a sky-blue long-sleeved t-shirt, long navy trousers and red sneakers. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F3 · `F3-sitti-huda.png`

- **مكانها:** شخصية ستّي هدى بكل المجلدات
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر

```text
Character reference sheet on a pure white background: the same character shown full-body in three views side by side (front, three-quarter, back), and below them a row of four head close-ups with different expressions (big happy smile, surprised, proud, calm). Even neutral lighting; the design, colors and proportions are identical in every view; no scenery and no shadow on the background. Sitti Huda, the storytelling grandmother: late sixties, warm smiling eyes with laugh lines, round glasses on a beaded chain, a soft white headscarf, a long black Palestinian thobe with red tatreez on the chest panel and sleeves, a sage-green cardigan over it, olive-wood prayer beads in her hand. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F4 · `F4-naanaa.png`

- **مكانها:** شخصية القطّة نعناع بكل المجلدات
- **النسبة والحجم:** 1:1 مربع · 2048 بكسل أو أكثر

```text
Character reference sheet on a pure white background with four poses of the same cat in a row, even neutral lighting, no scenery. Naanaa, the family's lazy ginger cat: plump orange tabby with a cream belly and paws, sleepy half-closed green eyes, a mint-green collar with no tag. Show her curled up asleep, stretching, yawning and sitting. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### أغلفة المجلدات (خلفيات بدون أشخاص؛ طفلنا القارئ بنضيفه بالنظام)

### F5 · `F5-cover-v1.png`

- **مكانها:** غلاف المجلد 1 «أعرف ربّي وأحبّه»
- **النسبة والحجم:** 3:4 عمودي · 2480 × 3307 بكسل أو أكثر

```text
Portrait 3:4 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. A peaceful hillside garden at night under a huge sky full of stars and a soft glowing full moon: fireflies, wildflowers, a calm pond reflecting the stars, olive and fig trees framing both sides, and a smooth grassy spot in the center-bottom glowing softly. Mood: wonder at creation. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F6 · `F6-cover-v2.png`

- **مكانها:** غلاف المجلد 2 «أصلّي وأتعلّم»
- **النسبة والحجم:** 3:4 عمودي · 2480 × 3307 بكسل أو أكثر

```text
Portrait 3:4 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. Dawn in a calm home prayer corner: a big arched window filling with the first golden light, a mosque dome and minaret softly silhouetted on the distant horizon, a folded prayer mat with a geometric pattern on the patterned tile floor, a wooden book stand holding a closed book wrapped in green embroidered cloth, a small brass lantern and a pot of mint; an empty spot in warm light center-bottom on the floor. Mood: calm and gentle. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F7 · `F7-cover-v3.png`

- **مكانها:** غلاف المجلد 3 «أركان الإسلام وأركان الإيمان»
- **النسبة والحجم:** 3:4 عمودي · 2480 × 3307 بكسل أو أكثر

```text
Portrait 3:4 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. A sunny courtyard with five tall arched cream stone columns standing in a gentle arc, each topped with a glowing lantern, a small fountain behind them, jasmine and lemon trees, a bright blue sky with soft clouds, and an empty sunlit spot in the center front. Mood: strong, bright, welcoming. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F8 · `F8-cover-v4.png`

- **مكانها:** غلاف المجلد 4 «قصص الأنبياء وسيرة نبينا ﷺ»
- **النسبة والحجم:** 3:4 عمودي · 2480 × 3307 بكسل أو أكثر

```text
Portrait 3:4 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. A storybook landscape at dawn: on the left a calm sea with a wooden sailing ship, in the middle soft desert dunes and a palm oasis, on the right green hills; a big sky with fading stars and a rising sun; an old open book with blank pages lies in the foreground, with soft light rising from it like a path; an empty spot center-front beside the book. No people at all: no human figure, silhouette, face, hand or footprint anywhere. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F9 · `F9-cover-v5.png`

- **مكانها:** غلاف المجلد 5 «أخلاقي وآدابي وأحكامي»
- **النسبة والحجم:** 3:4 عمودي · 2480 × 3307 بكسل أو أكثر

```text
Portrait 3:4 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. A friendly neighborhood street in the morning: limestone houses with colorful doors and potted plants, a bench under an olive tree, a basket of fruit left as a gift on a neighbor's doorstep, a bicycle leaning on a wall, birds in the sky, tulips in the foreground corners, and an empty sunny spot center-front on the path. Mood: kind and warm. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F10 · `F10-cover-ramadan.png`

- **مكانها:** غلاف كتاب «رمضان والعيد»
- **النسبة والحجم:** 3:4 عمودي · 2480 × 3307 بكسل أو أكثر

```text
Portrait 3:4 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. A street at sunset in Ramadan: strings of glowing lanterns and small lights hung between limestone houses, a slim crescent moon in a violet-and-orange sky, a balcony with a low table set for iftar (dates, water, a bowl of soup), a tray of Eid cookies (ka'ak and ma'amoul), festive bunting and paper lanterns, and an empty glowing spot center-front. Mood: joyful, festive. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### افتتاحيات وحدات المجلد 1 (فيها ريم وسالم وستّي هدى؛ استعمل F1–F4 مرجعًا)

### F11 · `F11-unit-allah.png`

- **مكانها:** افتتاحية وحدة «اللهُ خَلَقَنِي»
- **النسبة والحجم:** 4:3 أفقي · 2400 بكسل أو أكثر

```text
Reem and Salem lie on a picnic blanket on the grass at night, pointing up in wonder at a sky full of stars and the Milky Way; Naanaa the cat is curled up between them; fireflies glow around them. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F12 · `F12-unit-blessings.png`

- **مكانها:** افتتاحية وحدة «نِعَمُ رَبِّي»
- **النسبة والحجم:** 4:3 أفقي · 2400 بكسل أو أكثر

```text
A sunny breakfast in the home courtyard under a fig tree: Reem pours a glass of water for Salem; the low table holds bread, olive oil, za'atar, dates and fruit; birds and sunshine; both children smile, thankful. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F13 · `F13-unit-prophet.png`

- **مكانها:** افتتاحية وحدة «نَبِيُّنَا مُحَمَّدٌ ﷺ»
- **النسبة والحجم:** 4:3 أفقي · 2400 بكسل أو أكثر

```text
Sitti Huda sits under an olive tree telling a story to Reem and Salem, who listen closely. Above them, the story appears as a soft glowing dream-cloud showing a peaceful palm oasis at dawn with date palms, a simple well and doves. The dream-cloud contains no people at all. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F14 · `F14-unit-follow.png`

- **مكانها:** افتتاحية وحدة «أَقْتَدِي بِنَبِيِّي ﷺ»
- **النسبة والحجم:** 4:3 أفقي · 2400 بكسل أو أكثر

```text
A garden path of golden footprints: along it, Salem kneels and gives a bowl of water to a thirsty kitten, and Reem smiles and waves hello to an elderly neighbor watering plants at his doorstep. Morning light, kindness. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F15 · `F15-unit-house.png`

- **مكانها:** افتتاحية وحدة «بَيْتُ الْإِسْلَامِ»
- **النسبة والحجم:** 4:3 أفقي · 2400 بكسل أو أكثر

```text
On the living-room rug, Reem and Salem build a toy house from big wooden blocks; the house stands firmly on five sturdy pillars, each a different bright color; Sitti Huda watches from the floor cushions, smiling; Naanaa sleeps nearby. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F16 · `F16-unit-myday.png`

- **مكانها:** افتتاحية وحدة «يَوْمِي مَعَ اللهِ»
- **النسبة والحجم:** 4:3 أفقي · 2400 بكسل أو أكثر

```text
One panoramic image that flows from sunrise on the right to night on the left along a gentle path: Salem waking up and stretching at sunrise, Reem and Salem eating lunch, both playing in the afternoon garden, and both asleep in bed under a starry window at night: four small moments of the same two children. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F17 · `F17-unit-adhkar.png`

- **مكانها:** افتتاحية وحدة «أَقُولُ وَأَذْكُرُ»
- **النسبة والحجم:** 4:3 أفقي · 2400 بكسل أو أكثر

```text
Evening on floor cushions: Sitti Huda holds her prayer beads and speaks gently; Reem and Salem sit close, repeating after her with bright faces; a warm lamp and a window showing the moon. No speech bubbles. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F18 · `F18-unit-manners.png`

- **مكانها:** افتتاحية وحدة «أَخْلَاقِي الْجَمِيلَةُ»
- **النسبة والحجم:** 4:3 أفقي · 2400 بكسل أو أكثر

```text
In a sunny room, Reem helps Salem pick up spilled crayons from the floor, and Salem hands Reem a red tulip as a thank-you; Naanaa watches from a chair; warm smiles. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### مشاهد صفحات العيّنة

### F19 · `F19-ship-at-sea.png`

- **مكانها:** قصة يونس عليه السلام، المشهد 1
- **النسبة والحجم:** 3:2 أفقي · 2400 بكسل أو أكثر

```text
A wooden sailing ship with white sails on a calm blue sea under a bright sky with soft clouds and seagulls; the deck is empty. No people at all: no human figure, silhouette, face, hand or footprint anywhere. The image will be cropped to a wide strip: keep the main subject inside the central horizontal band. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F20 · `F20-dark-sea-whale.png`

- **مكانها:** قصة يونس عليه السلام، المشهد 2
- **النسبة والحجم:** 3:2 أفقي · 2400 بكسل أو أكثر

```text
Deep under a dark night sea: a huge gentle blue whale swims calmly with its mouth closed, surrounded by little fish and softly glowing plankton, faint light rays from above in dark navy water. Nothing inside the whale is shown. No people at all: no human figure, silhouette, face, hand or footprint anywhere. The image will be cropped to a wide strip: keep the main subject inside the central horizontal band. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F21 · `F21-moonlit-sea.png`

- **مكانها:** قصة يونس عليه السلام، المشهد 3
- **النسبة والحجم:** 3:2 أفقي · 2400 بكسل أو أكثر

```text
A calm dark sea at night under a big crescent moon and stars; gentle ripples reflect the moonlight; the whale's smooth back shows just above the water as a dark hump with a small spout. No people at all: no human figure, silhouette, face, hand or footprint anywhere. The image will be cropped to a wide strip: keep the main subject inside the central horizontal band. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F22 · `F22-shore-gourd-sunrise.png`

- **مكانها:** قصة يونس عليه السلام، المشهد 4
- **النسبة والحجم:** 3:2 أفقي · 2400 بكسل أو أكثر

```text
A quiet beach at sunrise: golden sand, gentle waves, a broad-leaved gourd vine (yaqtin) with big heart-shaped green leaves and small yellow flowers climbing over a low wooden frame, a palm tree in the distance, a warm sunrise sky. No people at all: no human figure, silhouette, face, hand or footprint anywhere. The image will be cropped to a wide strip: keep the main subject inside the central horizontal band. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F23 · `F23-blessings-garden-coloring.png`

- **مكانها:** صفحة التلوين «نِعَم الله»
- **النسبة والحجم:** 3:4 عمودي · 2400 بكسل أو أكثر

```text
Black-and-white coloring page for a 4–6-year-old: a garden full of blessings — a big smiling sun, a tree with fruit, flowers, a little stream, a bird, a rabbit, a cloud with raindrops, and a basket of vegetables. Thick clean black outlines, large simple closed shapes that are easy to color, no shading, no grey, no hatching, pure white background. No people at all: no human figure, silhouette, face, hand or footprint anywhere. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F24 · `F24-blessings-hunt.png`

- **مكانها:** صفحة «ابحث عن نِعَم الله»
- **النسبة والحجم:** 4:3 أفقي · 2400 بكسل أو أكثر

```text
A busy, detailed find-the-objects scene for children: a family courtyard and garden on a sunny day, full of clearly drawn things to find — a water jug, a loaf of bread, a bowl of fruit, an orange tree, chickens, a sheep, a rain cloud over a green field, a well, books on a bench, a warm house with an open door. Reem and Salem stand in the middle pointing at things, Sitti Huda sits on a bench, Naanaa sleeps in a sunny corner. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F25 · `F25-family-meal.png`

- **مكانها:** صفحة ذكر «قبل الطعام»
- **النسبة والحجم:** 4:3 أفقي · 2400 بكسل أو أكثر

```text
Dinner on floor cushions around a low round table: Sitti Huda, a mother in a dusty-rose hijab, a father with a short beard, Reem and Salem; Salem is just about to take his first bite and pauses with a happy, thoughtful face (the moment before eating). Bread, hummus, salad and lentil soup; warm evening lamp light. No speech bubbles. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### F26 · `F26-kitchen-broken-cup.png`

- **مكانها:** صفحة «ماذا أفعل لو غضبت؟»
- **النسبة والحجم:** 4:3 أفقي · 2400 بكسل أو أكثر

```text
A bright kitchen: a cup lies broken on the patterned tile floor next to spilled juice; Salem stands beside it frowning with clenched fists and red cheeks, upset and angry in a gentle, child-friendly way (not scary); Reem watches from the doorway, concerned; Naanaa leaps away. Calm daylight. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Religious rule: do not depict God in any form, nor any prophet, angel or Companion — not even as a silhouette, shadow, light figure or veiled figure. No Quran pages, no calligraphy, no writing. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

> باقي الوحدات (35 وحدة) بكتبلك مشاهدها بعد ما يوافق المشرف على محتوى المجلدات.

## أغلفة الدوسيات (G) · أولوية 3

خلفيات أغلفة بنفس فكرة D: أعلاها هادي للعنوان، ومكان فاضي بالوسط لشخصية الطفل.

### G1 · `G1-journey-stage-1.png`

- **مكانها:** غلاف «رحلتي الأولى للتعلّم»، المحطة 1
- **النسبة والحجم:** 3:4 عمودي · 2480 × 3307 بكسل أو أكثر

```text
Portrait 3:4 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. Dawn at the start of a journey: a winding path through soft green hills toward a bright horizon, little blank wooden signposts and colorful flags along the path, a starting gate made of a flowery arch, birds, and an empty glowing spot center-front at the start of the path. Mood: getting ready, excited. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### G2 · `G2-journey-stage-2.png`

- **مكانها:** غلاف «رحلتي الأولى للتعلّم»، المحطة 2
- **النسبة والحجم:** 3:4 عمودي · 2480 × 3307 بكسل أو أكثر

```text
Portrait 3:4 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. Midday on the journey: the path crosses a little wooden bridge over a sparkling stream between green hills with flowers, butterflies and a few fluffy clouds, blank colorful flags along the way, and an empty sunny spot center-front on the bridge path. Mood: curious, growing. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### G3 · `G3-journey-stage-3.png`

- **مكانها:** غلاف «رحلتي الأولى للتعلّم»، المحطة 3
- **النسبة والحجم:** 3:4 عمودي · 2480 × 3307 بكسل أو أكثر

```text
Portrait 3:4 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. Golden afternoon at the journey's end: the path reaches the top of a hill with a big old tree, a hot-air balloon rising nearby, a view over all the hills and the stream behind, and an empty golden spot center-front under the tree. Mood: proud, ready for school. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### G4 · `G4-foundation-kg1.png`

- **مكانها:** غلاف «دوسية التأسيس» KG1
- **النسبة والحجم:** 3:4 عمودي · 2480 × 3307 بكسل أو أكثر

```text
Portrait 3:4 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. A cheerful learning corner in the morning: a low wooden desk with chunky crayons, a pencil case and plain colored wooden blocks (no letters), a potted plant, a big arched window with sunshine, soft pastel walls, and an empty spot center-front in front of the desk. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

### G5 · `G5-foundation-kg2.png`

- **مكانها:** غلاف «دوسية التأسيس» KG2
- **النسبة والحجم:** 3:4 عمودي · 2480 × 3307 بكسل أو أكثر

```text
Portrait 3:4 book-cover background. One single continuous scene: its upper third is naturally calm and simple (open sky, a soft ceiling glow or gently out-of-focus depth) so a big title can sit there later; it is part of the same scene, never a separate band, panel, frame or seam. Keep a clear, empty, well-lit spot in the lower-middle center where a child hero will be placed later (the spot is about 45% of the image height tall), with the light falling on that spot. Strong depth: detailed foreground elements in the bottom corners, the hero's spot in the midground, a glowing background. Keep everything important away from the outer 5% (print trim). No people, children or characters anywhere. A bright learning room: a low bookshelf with plain colorful book spines, a small globe, a desk with colored pencils and a notebook, a big arched window with sunshine and a lemon tree outside, and an empty spot center-front. Brighter and slightly more grown-up than KG1. Setting cues: Palestinian / Levantine — warm cream limestone, arched doorways and windows, olive trees, patterned cement tiles, tatreez cross-stitch embroidery on textiles, brass and paper lanterns. Style: bright 2D cartoon illustration for a children's activity book — clean, confident dark-brown outlines of even weight, bold flat color blocks with soft cel shading, cheerful saturated palette, simple rounded readable shapes, warm friendly faces, crisp print-ready edges. Not 3D, not photorealistic, not anime. Absolutely no text, letters, numbers, calligraphy, signs, labels, logos, brand marks, watermarks or signatures anywhere in the image.
```

## بعد ما تخلص

- ابعتلي الصور (أو حطّها بـ `design/incoming/`) وأنا بفحصها: الثبات، الكتابة المخفية، القصّ، الدقة، وبقرّر وين تروح.
- إذا صورة طلعت فيها كتابة أو شعار، ولّدها مرة ثانية. ما بنصلّح الكتابة بالفوتوشوب.
- الصور اللي فيها أشخاص (A) بتضل للعرض فقط، والموقع ما بيقول إنهم زبائن.
