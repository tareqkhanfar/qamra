/**
 * Pictures of the add-ons and of what each product already includes (Tareq, 2026-10-07: «أي إضافات لازم
 * تذكرها من ضمن المنتج مع صور إلهم»). docs/plans/order-flows.md, «Add-ons: what is deactivated».
 *
 * Every picture shows a thing we really make: pages rendered by our own engines (the story pipeline, the
 * activity-book engine and its inserts) for invented sample children, set as product mockups. No AI, no
 * stock photos. WebP, 640 × 480, in `public/addons/<slug>.webp` and `public/included/<product>/<item>.webp`.
 *
 *   addonMedia[addon.slug]         → { src, alt_ar, alt_en } | undefined (only the add-ons we can deliver)
 *   includedItems[product.slug]    → [{ src, title_ar, title_en, desc_ar, desc_en }] | undefined
 *
 * No imports, so `node --test` can load it. The texts describe the printed thing only: no delivery times,
 * no stock, nothing a product does not have.
 */

export type AddonMedia = { src: string; alt_ar: string; alt_en: string };

export type IncludedItem = {
  src: string;
  title_ar: string;
  title_en: string;
  desc_ar: string;
  desc_en: string;
};

/** The add-ons that stay on sale (2026-10-07). A hidden add-on has no entry. */
export const addonMedia: Readonly<Record<string, AddonMedia | undefined>> = {
  "hardcover-upgrade": {
    src: "/addons/hardcover-upgrade.webp",
    alt_ar: "كتاب «ليلى في أوّل يوم بالروضة» بغلاف مقوّى",
    alt_en: "“Layla’s First Day at Kindergarten” as a hardcover book",
  },
  "dedication-page": {
    src: "/addons/dedication-page.webp",
    alt_ar: "صفحة الإهداء في أوّل الكتاب، وعليها كلمات الأهل لطفلتهم",
    alt_en: "The dedication page at the start of the book, with the parents’ own words to their daughter",
  },
  "drawing-companion": {
    src: "/addons/drawing-companion.webp",
    alt_ar: "رسمة طفل على ورقة، وسهم منها إلى الكتاب: تصبح الرسمة صاحبًا يرافقه في الحكاية",
    alt_en: "A child’s drawing on paper, with an arrow to the book: the drawing becomes a companion in the story",
  },
  "family-voice": {
    src: "/addons/family-voice.webp",
    alt_ar: "صفحة من الكتاب عليها رمز QR، وعلى الهاتف صفحة الاستماع إلى الحكاية بأصوات العائلة",
    alt_en:
      "A book page with a QR code, and a phone showing the page for listening to the story in family members’ voices",
  },
  "extra-copy": {
    src: "/addons/extra-copy.webp",
    alt_ar: "نسختان من الكتاب نفسه",
    alt_en: "Two copies of the same book",
  },
  "digital-copy": {
    src: "/addons/digital-copy.webp",
    alt_ar: "الكتاب المطبوع، والكتاب نفسه في صفحة القراءة على الهاتف",
    alt_en: "The printed book, and the same book in the reader on a phone",
  },
  "printed-answer-key": {
    src: "/addons/printed-answer-key.webp",
    alt_ar: "كتاب «رحلتي الأولى للتعلّم»، ومعه كتيّب مفتاح الإجابات مطبوعًا",
    alt_en: "“My First Learning Journey” with its printed answer key booklet",
  },
  "printed-parent-guide": {
    src: "/addons/printed-parent-guide.webp",
    alt_ar: "مجلد من «قلبي يعرف الله»، ومعه كتيّب إجابات الأنشطة مطبوعًا",
    alt_en: "A volume of “My Heart Knows Allah” with its printed booklet of activity answers",
  },
};

const DEDICATION: IncludedItem = {
  src: "/included/classic-book/dedication.webp",
  title_ar: "صفحة العنوان والإهداء",
  title_en: "Title and dedication page",
  desc_ar: "في أوّل الكتاب: اسم طفلكم وصورته المرسومة، وإهداء له.",
  desc_en: "At the start of the book: your child’s name, their drawn portrait and a dedication to them.",
};

const PARENTS: IncludedItem = {
  src: "/included/classic-book/parents.webp",
  title_ar: "صفحة «للأهل»",
  title_en: "“For parents” page",
  desc_ar: "ما تُعلّمه الحكاية، وأسئلة تتحاورون فيها مع طفلكم بعد القراءة.",
  desc_en: "What the story teaches, and questions to talk about with your child after reading.",
};

const MAGIC: IncludedItem[] = [
  {
    src: "/addons/drawing-companion.webp",
    title_ar: "صاحبي من رسمتي",
    title_en: "Drawing companion",
    desc_ar: "يرسم طفلكم صاحبًا له، فنحوّل رسمته إلى شخصية ترافقه في الحكاية.",
    desc_en: "Your child draws a friend, and we turn the drawing into a character who joins them in the story.",
  },
  {
    src: "/addons/dedication-page.webp",
    title_ar: "إهداء بكلماتكم",
    title_en: "A dedication in your own words",
    desc_ar: "تكتبون لطفلكم كلمات قصيرة، فنطبعها في أوّل الكتاب.",
    desc_en: "You write a short message to your child, and we print it at the start of the book.",
  },
  PARENTS,
];

/** What each product's price already includes, verified in its renderer (order-flows.md, same section). */
export const includedItems: Readonly<Record<string, IncludedItem[] | undefined>> = {
  "classic-book": [DEDICATION, PARENTS],
  "magic-book": MAGIC,
  "magic-custom-story": MAGIC,
  "learning-journey": [
    {
      src: "/included/learning-journey/owner-page.webp",
      title_ar: "صفحة «هذا الكتاب لـ…»",
      title_en: "“This book belongs to…” page",
      desc_ar: "اسم طفلكم وشخصيته المرسومة، ومكان يرسم فيه حول كفّه.",
      desc_en: "Your child’s name and drawn character, and a space to trace around their hand.",
    },
    {
      src: "/included/learning-journey/journey-map.webp",
      title_ar: "خريطة الرحلة",
      title_en: "Journey map",
      desc_ar: "يتابع عليها طفلكم رحلته محطّةً بعد محطّة.",
      desc_en: "Your child follows the journey on it, stop by stop.",
    },
    {
      src: "/included/learning-journey/audio-qr.webp",
      title_ar: "رموز QR صوتية",
      title_en: "Audio QR codes",
      desc_ar: "على صفحات الأصوات والكلمات رموزٌ تمسحونها بالهاتف ليسمع طفلكم النطق.",
      desc_en:
        "Pages with sounds and words have codes you scan with your phone, so your child hears the pronunciation.",
    },
    {
      src: "/included/learning-journey/certificate.webp",
      title_ar: "شهادة إنجاز",
      title_en: "Certificate of achievement",
      desc_ar: "في آخر الكتاب، باسم طفلكم وشخصيته.",
      desc_en: "At the end of the book, with your child’s name and character.",
    },
  ],
  "family-adventures": [
    {
      src: "/included/family-adventures/sticker-sheet.webp",
      title_ar: "ورقة ملصقات",
      title_en: "Sticker sheet",
      desc_ar: "تُطبع على ورق لاصق: أختام المغامرات، وملصقات المكافآت، ورموز الروتين اليومي.",
      desc_en: "Printed on sticker paper: adventure stamps, reward stickers and daily routine icons.",
    },
    {
      src: "/included/family-adventures/money-recipe-cards.webp",
      title_ar: "نقود اللعب وبطاقات الوصفات",
      title_en: "Play money and recipe cards",
      desc_ar: "على كرتون سميك للقصّ، لمغامرتَي السوق والمطبخ.",
      desc_en: "On thick card to cut out, for the market and kitchen adventures.",
    },
    {
      src: "/included/family-adventures/game-cards.webp",
      title_ar: "بطاقات الألعاب ودمى الأصابع",
      title_en: "Game cards and finger puppets",
      desc_ar: "بطاقات للذاكرة والأسئلة والأدوار، ودمى أصابع، على كرتون سميك للقصّ.",
      desc_en: "Memory, question and role cards, and finger puppets, on thick card to cut out.",
    },
    {
      src: "/included/family-adventures/passport.webp",
      title_ar: "جواز سفر المغامرات",
      title_en: "Adventure passport",
      desc_ar: "في أوّل الكتاب: يُلصق فيه طفلكم ختم كل مغامرة من ورقة الملصقات.",
      desc_en: "At the start of the book: your child sticks in a stamp from the sticker sheet after each adventure.",
    },
    {
      src: "/included/family-adventures/certificate.webp",
      title_ar: "شهادة المغامرة",
      title_en: "Adventure certificate",
      desc_ar: "في آخر الكتاب، باسم طفلكم وعائلته.",
      desc_en: "At the end of the book, with the names of your child and your family.",
    },
  ],
  "islamic-series": [
    {
      src: "/included/islamic-series/this-is-me.webp",
      title_ar: "صفحة «هذا أنا»",
      title_en: "“This is me” page",
      desc_ar: "في أوّل كل مجلد: اسم طفلكم وشخصيته، وأسطر يكتب فيها عن نفسه، ومساحة يرسم فيها أسرته.",
      desc_en:
        "At the start of each volume: your child’s name and character, lines to write about themselves, and a space to draw their family.",
    },
    {
      src: "/included/islamic-series/passport.webp",
      title_ar: "جواز السفر",
      title_en: "Passport",
      desc_ar: "باسم طفلكم وشخصيته، وفيه دائرة لكل وحدة ونجوم للتحدّيات.",
      desc_en: "With your child’s name and character, a circle for each unit and stars for the challenges.",
    },
    {
      src: "/included/islamic-series/parents-page.webp",
      title_ar: "صفحة «للأهل»",
      title_en: "“For parents” page",
      desc_ar: "بعد كل وحدة: ما تعلّمه طفلكم، وكيف تشرحونه له، وسؤال ونشاط وعادة للبيت.",
      desc_en:
        "After each unit: what your child learned, how to explain it, a question, an activity and a habit for home.",
    },
    {
      src: "/included/islamic-series/certificate.webp",
      title_ar: "الشهادة",
      title_en: "Certificate",
      desc_ar: "في آخر كل مجلد، باسم طفلكم وشخصيته.",
      desc_en: "At the end of each volume, with your child’s name and character.",
    },
  ],
  "foundation-workbook": [
    {
      src: "/included/foundation-workbook/owner-page.webp",
      title_ar: "صفحة «هذا الكتاب لـ…»",
      title_en: "“This book belongs to…” page",
      desc_ar: "في أوّل كل جزء: اسم طفلكم وشخصيته، ومكان يرسم فيه حول كفّه.",
      desc_en: "At the start of each volume: your child’s name and character, and a space to trace around their hand.",
    },
    {
      src: "/included/foundation-workbook/name-tracing.webp",
      title_ar: "صفحتا «اسمي»",
      title_en: "“My name” pages",
      desc_ar: "في كل جزء يتتبّع طفلكم اسمه بالعربية، ثم بالإنجليزية.",
      desc_en: "In every volume, your child traces their name in Arabic, then in English.",
    },
    {
      src: "/included/foundation-workbook/certificate.webp",
      title_ar: "شهادة إنجاز",
      title_en: "Certificate of achievement",
      desc_ar: "في آخر الجزء الثالث، باسم طفلكم وشخصيته.",
      desc_en: "At the end of Volume 3, with your child’s name and character.",
    },
  ],
};
