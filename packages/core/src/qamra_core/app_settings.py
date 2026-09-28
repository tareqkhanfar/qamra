"""Admin-managed system settings: the registry (types, limits, defaults) and validation.

Everything an operator may change without a deploy lives here: prices, contact details, AI keys and
models, notifications, site behaviour and privacy retention (within the privacy rules' bounds).
Infrastructure secrets (database, JWT, encryption keys) stay in the environment, never in the admin.

- `public` settings are served to the website (`GET /api/settings/public`).
- `secret` settings are encrypted at rest and never returned in full (only "set" + last 4 chars).
- `example=True` marks a default that is a placeholder to replace (the admin shows a badge).
"""

import enum
import ipaddress
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


class Kind(enum.StrEnum):
    text = "text"
    number = "number"  # integer
    money = "money"  # decimal, 2 places
    decimal = "decimal"  # decimal, 1 place (e.g. millimetres)
    boolean = "boolean"
    choice = "choice"
    secret = "secret"  # nosec B105  (a setting kind, not a password)
    phone = "phone"
    email = "email"
    url = "url"


@dataclass(frozen=True)
class Group:
    id: str
    label_ar: str
    label_en: str


GROUPS: tuple[Group, ...] = (
    Group("pricing", "الأسعار", "Pricing"),
    Group("contact", "التواصل والمعلومات", "Contact & company"),
    Group("site", "الموقع والتسجيل", "Site & sign-up"),
    Group("ai_keys", "مفاتيح الذكاء الاصطناعي", "AI keys"),
    Group("ai_models", "نماذج الذكاء الاصطناعي", "AI models"),
    Group("quality", "الجودة والتكلفة", "Quality & cost"),
    Group("print", "الطباعة", "Print"),
    Group("notifications", "البريد والواتساب", "Email & WhatsApp"),
    Group("privacy", "الخصوصية والحذف", "Privacy & retention"),
    Group("security", "الأمان", "Security"),
)


@dataclass(frozen=True)
class SettingDef:
    key: str
    group: str
    kind: Kind
    default: Any
    label_ar: str
    label_en: str
    help_ar: str = ""
    help_en: str = ""
    public: bool = False
    example: bool = False
    choices: tuple[str, ...] = ()
    min: float | None = None
    max: float | None = None
    max_length: int = 200


def _money(key: str, label_ar: str, label_en: str, default: str, public: bool = True) -> SettingDef:
    return SettingDef(
        key, "pricing", Kind.money, default, label_ar, label_en, public=public, example=True, min=0, max=10000
    )


_DEFS: list[SettingDef] = [
    # ---- pricing
    _money("price_digital_ils", "نسخة رقمية (₪)", "Digital copy (₪)", "49"),
    _money("price_softcover_ils", "غلاف ورقي (₪)", "Softcover (₪)", "89"),
    _money("price_hardcover_ils", "غلاف مقوّى (₪)", "Hardcover (₪)", "119"),
    _money("delivery_fee_ils", "رسوم التوصيل (₪)", "Delivery fee (₪)", "20"),
    _money("price_digital_jod", "نسخة رقمية (دينار)", "Digital copy (JOD)", "9"),
    _money("price_softcover_jod", "غلاف ورقي (دينار)", "Softcover (JOD)", "16"),
    _money("price_hardcover_jod", "غلاف مقوّى (دينار)", "Hardcover (JOD)", "22"),
    _money("delivery_fee_jod", "رسوم التوصيل (دينار)", "Delivery fee (JOD)", "3"),
    # ---- store costs and margins (Addendum 4 §6)
    SettingDef(
        "usd_ils",
        "pricing",
        Kind.money,
        "3.70",
        "سعر الدولار بالشيكل",
        "USD → ILS rate",
        "لتحويل تكلفة الذكاء الاصطناعي (بالدولار) عند حساب الهامش.",
        "Converts AI costs (in USD) when margins are computed.",
        example=True,
        min=0.5,
        max=20,
    ),
    SettingDef(
        "jod_ils",
        "pricing",
        Kind.money,
        "5.22",
        "سعر الدينار بالشيكل",
        "JOD → ILS rate",
        "لمقارنة طلبات الأردن بالتكاليف بالشيكل.",
        "Compares Jordanian orders with costs kept in ILS.",
        example=True,
        min=1,
        max=20,
    ),
    SettingDef(
        "margin_floor_pct",
        "pricing",
        Kind.number,
        35,
        "أدنى هامش ربح مقبول (%)",
        "Margin floor (%)",
        "المنتجات والطلبات تحت هذا الهامش تظهر بالأحمر.",
        "Products and orders below this margin show in red.",
        min=0,
        max=90,
    ),
    SettingDef(
        "cod_cost_ils",
        "pricing",
        Kind.money,
        "0",
        "رسوم شركة التوصيل على الدفع عند الاستلام (₪)",
        "Courier COD fee we pay (₪)",
        "تكلفة علينا لكل طرد يُدفع عند الاستلام.",
        "What each cash-on-delivery parcel costs us.",
        example=True,
        min=0,
        max=100,
    ),
    SettingDef(
        "classic_budget_ils",
        "quality",
        Kind.money,
        "2.00",
        "سقف تكلفة الذكاء الاصطناعي لكتاب كلاسيك (₪)",
        "AI budget per Classic book (₪)",
        "يتوقف توليد الكتاب عند تجاوزه ويُحال للمراجعة.",
        "A Classic book stops and goes to review when it would pass this.",
        min=0.5,
        max=20,
    ),
    # ---- contact
    SettingDef(
        "support_whatsapp",
        "contact",
        Kind.phone,
        "+970590000000",
        "واتساب الدعم",
        "Support WhatsApp",
        "يظهر في الأسئلة الشائعة للأهالي.",
        "Shown to parents in the FAQ.",
        public=True,
        example=True,
    ),
    SettingDef(
        "sales_whatsapp",
        "contact",
        Kind.phone,
        "+970590000001",
        "واتساب المبيعات (الروضات)",
        "Sales WhatsApp (kindergartens)",
        "يظهر في صفحة الروضات.",
        "Shown on the kindergartens page.",
        public=True,
        example=True,
    ),
    SettingDef(
        "support_email",
        "contact",
        Kind.email,
        "support@example.com",
        "بريد الدعم",
        "Support email",
        public=True,
        example=True,
    ),
    SettingDef(
        "sales_email",
        "contact",
        Kind.email,
        "sales@example.com",
        "بريد المبيعات",
        "Sales email",
        public=True,
        example=True,
    ),
    SettingDef(
        "company_name",
        "contact",
        Kind.text,
        "",
        "اسم الشركة المسجّلة",
        "Registered company name",
        "يظهر في أسفل الموقع. اتركه فارغاً لإخفائه.",
        "Shown in the footer. Leave empty to hide.",
        public=True,
        max_length=120,
    ),
    SettingDef(
        "company_address",
        "contact",
        Kind.text,
        "",
        "عنوان الشركة (للفواتير)",
        "Company address (for invoices)",
        max_length=200,
    ),
    SettingDef(
        "company_tax_id",
        "contact",
        Kind.text,
        "",
        "الرقم الضريبي (للفواتير)",
        "Tax number (for invoices)",
        "يظهر على الفواتير عند تعبئته.",
        "Printed on invoices when filled in.",
        max_length=40,
    ),
    SettingDef("instagram_url", "contact", Kind.url, "", "رابط إنستغرام", "Instagram URL", public=True),
    SettingDef("facebook_url", "contact", Kind.url, "", "رابط فيسبوك", "Facebook URL", public=True),
    # ---- site
    SettingDef(
        "registration_open",
        "site",
        Kind.boolean,
        True,
        "التسجيل مفتوح",
        "Sign-up open",
        "أغلقه لإيقاف إنشاء حسابات جديدة مؤقتاً.",
        "Turn off to pause new accounts.",
        public=True,
    ),
    SettingDef(
        "music_enabled",
        "site",
        Kind.boolean,
        True,
        "موسيقى الخلفية",
        "Background music",
        "تبدأ بعد أول لمسة من الزائر، ويمكنه كتمها.",
        "Starts after the visitor's first tap; they can mute it.",
        public=True,
    ),
    SettingDef(
        "music_volume",
        "site",
        Kind.number,
        30,
        "مستوى صوت الموسيقى (0–100)",
        "Music volume (0–100)",
        public=True,
        min=0,
        max=100,
    ),
    SettingDef(
        "animations_enabled",
        "site",
        Kind.boolean,
        True,
        "الحركات والتأثيرات",
        "Animations",
        "تُعطَّل تلقائياً لمن يطلب تقليل الحركة في جهازه.",
        "Always off for visitors who ask for reduced motion.",
        public=True,
    ),
    SettingDef(
        "google_login_enabled",
        "site",
        Kind.boolean,
        False,
        "تسجيل الدخول عبر Google",
        "Google sign-in",
        "يحتاج معرّف العميل والسر أدناه.",
        "Needs the client ID and secret below.",
        public=True,
    ),
    SettingDef(
        "google_client_id", "site", Kind.text, "", "Google Client ID", "Google client ID", max_length=200
    ),
    SettingDef(
        "google_client_secret", "site", Kind.secret, "", "Google Client Secret", "Google client secret"
    ),
    # ---- AI keys (paid tiers only: no training on our data)
    SettingDef(
        "anthropic_api_key",
        "ai_keys",
        Kind.secret,
        "",
        "مفتاح Anthropic (Claude)",
        "Anthropic (Claude) key",
        "لكتابة القصة والتشكيل ومراجعة الأمان.",
        "Story writing, vowelization and safety review.",
    ),
    SettingDef("gemini_api_key", "ai_keys", Kind.secret, "", "مفتاح Google Gemini", "Google Gemini key"),
    SettingDef("openai_api_key", "ai_keys", Kind.secret, "", "مفتاح OpenAI", "OpenAI key"),
    SettingDef(
        "fal_key",
        "ai_keys",
        Kind.secret,
        "",
        "مفتاح fal.ai (الرسم والتكبير)",
        "fal.ai key (images + upscaling)",
        "للرسم (Nano Banana 2 والبديل FLUX.2) وتكبير الصور للطباعة.",
        "Page art (Nano Banana 2, FLUX.2 fallback) and print upscaling.",
    ),
    # ---- AI models (Addendum 3 §1; exact IDs verified on the providers' docs, 2026-09-28)
    SettingDef(
        "image_provider",
        "ai_models",
        Kind.choice,
        "fal",
        "مزوّد الرسم",
        "Image provider",
        "fal هو الافتراضي. Gemini وOpenAI يعملان فقط إذا اخترتهما ووضعت مفاتيحهما.",
        "fal is the default. Gemini and OpenAI run only when selected and keyed.",
        choices=("fal", "gemini", "openai"),
    ),
    SettingDef(
        "fal_image_model",
        "ai_models",
        Kind.text,
        "fal-ai/nano-banana-2",
        "نموذج fal الأساسي",
        "fal primary model",
        "أي نقطة نهاية على fal. نسخة /edit تُستخدم تلقائيًا مع الصور المرجعية.",
        "Any fal endpoint. The /edit variant is used automatically with reference images.",
        max_length=120,
    ),
    SettingDef(
        "fal_fallback_model",
        "ai_models",
        Kind.text,
        "fal-ai/flux-2-pro/edit",
        "نموذج fal الاحتياطي",
        "fal fallback model",
        "يُستخدم فقط بعد فشل النموذج الأساسي مرّتين، ويُسجَّل ذلك.",
        "Used only after two failed attempts on the primary; every switch is logged.",
        max_length=120,
    ),
    SettingDef(
        "fal_upscale_model",
        "ai_models",
        Kind.text,
        "fal-ai/seedvr/upscale/image",
        "نموذج التكبير للطباعة",
        "Print upscaler",
        max_length=120,
    ),
    SettingDef(
        "fallback_after_failures",
        "ai_models",
        Kind.number,
        2,
        "محاولات قبل التحويل للبديل",
        "Attempts before switching to the fallback",
        min=1,
        max=5,
    ),
    SettingDef(
        "text_model",
        "ai_models",
        Kind.text,
        "claude-sonnet-5",
        "نموذج كتابة القصة والتشكيل",
        "Story & vowelization model",
        "Sonnet هو الافتراضي. يمكن اختيار claude-opus-5 لكنه أغلى بنحو 2.5 مرة.",
        "Sonnet is the default. claude-opus-5 is selectable but costs about 2.5×.",
        max_length=80,
    ),
    SettingDef(
        "text_model_fast",
        "ai_models",
        Kind.text,
        "claude-haiku-4-5-20251001",
        "نموذج الفحص والأمان",
        "QA & safety model",
        "لفحص الصفحات بالرؤية ومراجعة الأمان.",
        "Page vision QA and safety review.",
        max_length=80,
    ),
    SettingDef(
        "story_effort",
        "ai_models",
        Kind.choice,
        "medium",
        "عمق التفكير عند كتابة القصة",
        "Story thinking effort",
        choices=("low", "medium", "high"),
    ),
    SettingDef(
        "gemini_image_model",
        "ai_models",
        Kind.text,
        "gemini-3.1-flash-image",
        "نموذج Gemini للرسم",
        "Gemini image model",
        max_length=80,
    ),
    SettingDef(
        "openai_image_model",
        "ai_models",
        Kind.text,
        "gpt-image-2.5-sunburst",
        "نموذج OpenAI للرسم",
        "OpenAI image model",
        max_length=80,
    ),
    SettingDef(
        "openai_image_quality",
        "ai_models",
        Kind.choice,
        "high",
        "جودة OpenAI",
        "OpenAI quality",
        choices=("low", "medium", "high", "xhigh", "max", "auto"),
    ),
    # ---- quality & cost (Addendum 3 §2)
    SettingDef(
        "preview_resolution",
        "quality",
        Kind.choice,
        "0.5K",
        "دقة المعاينة",
        "Preview resolution",
        "أقل دقة متاحة، مع علامة مائية.",
        "The lowest the model offers, watermarked.",
        choices=("0.5K", "1K"),
    ),
    SettingDef(
        "final_mode",
        "quality",
        Kind.choice,
        "1k_upscale",
        "طريقة الصفحات النهائية",
        "Final pages",
        "1K ثم تكبير للطباعة (أرخص)، أو 2K ثم تكبير. القرار في docs/decisions.md.",
        "1K then upscale (cheaper), or 2K then upscale. Decision in docs/decisions.md.",
        choices=("1k_upscale", "2k_upscale"),
    ),
    SettingDef(
        "preview_pages",
        "quality",
        Kind.number,
        4,
        "صفحات المعاينة (مع الغلاف)",
        "Preview pages (incl. cover)",
        min=2,
        max=8,
    ),
    SettingDef(
        "image_concurrency",
        "quality",
        Kind.number,
        4,
        "صفحات تُرسم بالتوازي",
        "Pages drawn in parallel",
        min=1,
        max=8,
    ),
    SettingDef(
        "page_max_regenerations",
        "quality",
        Kind.number,
        2,
        "إعادات الرسم التلقائية للصفحة",
        "Automatic redraws per page",
        "بعدها تُعلَّم الصفحة لمراجعة بشرية.",
        "After that the page is flagged for human review.",
        min=0,
        max=3,
    ),
    SettingDef(
        "qa_threshold",
        "quality",
        Kind.number,
        75,
        "حدّ النجاح في الفحص الآلي (٪)",
        "Automatic QA pass mark (%)",
        min=40,
        max=100,
    ),
    SettingDef(
        "book_budget_usd",
        "quality",
        Kind.money,
        "3.00",
        "سقف تكلفة الكتاب ($)",
        "Budget cap per book ($)",
        "يتوقف التوليد عند تجاوزه ويُعلَّم الكتاب في لوحة الإدارة.",
        "Generation stops at the cap and the book is flagged in admin.",
        min=0.5,
        max=20,
    ),
    # ---- print (Addendum 3 §4; confirm with the print partner's template)
    SettingDef(
        "print_spine_mm",
        "print",
        Kind.decimal,
        "8.0",
        "عرض الكعب (مم)",
        "Spine width (mm)",
        "من قالب المطبعة: يعتمد على عدد الصفحات ونوع الورق والغلاف.",
        "From the printer's template: depends on page count, paper and binding.",
        example=True,
        min=0,
        max=40,
    ),
    SettingDef(
        "print_signature",
        "print",
        Kind.number,
        4,
        "مضاعف عدد الصفحات",
        "Page-count multiple (signature)",
        min=2,
        max=32,
    ),
    # ---- notifications (used from Phase 2 / 5)
    SettingDef("smtp_host", "notifications", Kind.text, "", "خادم SMTP", "SMTP host", max_length=120),
    SettingDef("smtp_port", "notifications", Kind.number, 587, "منفذ SMTP", "SMTP port", min=1, max=65535),
    SettingDef(
        "smtp_username", "notifications", Kind.text, "", "مستخدم SMTP", "SMTP username", max_length=120
    ),
    SettingDef("smtp_password", "notifications", Kind.secret, "", "كلمة مرور SMTP", "SMTP password"),
    SettingDef(
        "mail_from",
        "notifications",
        Kind.email,
        "no-reply@example.com",
        "بريد المُرسِل",
        "Sender email",
        example=True,
    ),
    SettingDef(
        "twilio_account_sid",
        "notifications",
        Kind.text,
        "",
        "Twilio Account SID",
        "Twilio account SID",
        max_length=64,
    ),
    SettingDef(
        "twilio_auth_token", "notifications", Kind.secret, "", "Twilio Auth Token", "Twilio auth token"
    ),
    SettingDef(
        "twilio_whatsapp_from",
        "notifications",
        Kind.phone,
        "",
        "رقم واتساب المُرسِل (Twilio)",
        "Twilio WhatsApp sender",
    ),
    # ---- privacy (bounded by the privacy rules: never longer than the spec allows)
    SettingDef(
        "photo_retention_hours",
        "privacy",
        Kind.number,
        24,
        "حذف الصور الأصلية بعد (ساعات)",
        "Delete original photos after (hours)",
        "بعد اعتماد الشخصية. الحد الأقصى 24 ساعة.",
        "After character approval. At most 24 hours.",
        min=1,
        max=24,
    ),
    SettingDef(
        "draft_retention_days",
        "privacy",
        Kind.number,
        30,
        "حذف المسودّات المهملة بعد (أيام)",
        "Delete abandoned drafts after (days)",
        min=1,
        max=30,
    ),
    # ---- security (Addendum 3 §6)
    SettingDef(
        "admin_ip_allowlist",
        "security",
        Kind.text,
        "",
        "عناوين IP المسموح لها بالإدارة",
        "Admin IP allowlist",
        "اختياري. عناوين أو شبكات مفصولة بفواصل (مثل 203.0.113.7, 198.51.100.0/24). فارغ = بلا قيود.",
        "Optional. Comma-separated addresses or networks (e.g. 203.0.113.7, 198.51.100.0/24)."
        " Empty = no limit.",
        max_length=500,
    ),
]

REGISTRY: dict[str, SettingDef] = {d.key: d for d in _DEFS}
if len(REGISTRY) != len(_DEFS):
    raise RuntimeError("duplicate setting key in the registry")
if any(d.group not in {g.id for g in GROUPS} for d in _DEFS):
    raise RuntimeError("setting with an unknown group in the registry")

_PHONE = re.compile(r"^\+?[0-9]{7,15}$")
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,24}$")


class SettingError(ValueError):
    def __init__(self, key: str, reason: str) -> None:
        super().__init__(f"{key}: {reason}")
        self.key = key
        self.reason = reason


def validate(defn: SettingDef, raw: Any) -> Any:
    """Normalize an incoming value or raise SettingError. Returns a JSON-safe value."""
    k = defn.kind
    if k == Kind.boolean:
        if not isinstance(raw, bool):
            raise SettingError(defn.key, "expected true/false")
        return raw
    if k == Kind.number:
        if isinstance(raw, bool) or not isinstance(raw, int | float) or int(raw) != raw:
            raise SettingError(defn.key, "expected a whole number")
        number = int(raw)
        if (defn.min is not None and number < defn.min) or (defn.max is not None and number > defn.max):
            raise SettingError(defn.key, f"must be between {defn.min:g} and {defn.max:g}")
        return number
    if k in (Kind.money, Kind.decimal):
        step = Decimal("0.01") if k == Kind.money else Decimal("0.1")
        try:
            amount = Decimal(str(raw)).quantize(step)
        except (InvalidOperation, ValueError) as e:
            raise SettingError(defn.key, "expected an amount") from e
        if (
            not amount.is_finite()
            or (defn.min is not None and amount < Decimal(str(defn.min)))
            or (defn.max is not None and amount > Decimal(str(defn.max)))
        ):
            raise SettingError(defn.key, "amount out of range")
        return format(amount.normalize(), "f")
    if not isinstance(raw, str):
        raise SettingError(defn.key, "expected text")
    value = raw.strip()
    if k == Kind.secret:
        if len(value) > 500 or any(c in value for c in "\r\n\t\x00"):
            raise SettingError(defn.key, "invalid key format")
        return value
    if len(value) > defn.max_length or any(ord(c) < 32 for c in value):
        raise SettingError(defn.key, "too long or contains control characters")
    if value == "":
        return ""  # clearing an optional field is always allowed
    if k == Kind.choice and value not in defn.choices:
        raise SettingError(defn.key, f"must be one of {', '.join(defn.choices)}")
    if k == Kind.phone:
        compact = re.sub(r"[ ()-]", "", value)
        if not _PHONE.match(compact):
            raise SettingError(defn.key, "invalid phone number")
        return compact
    if k == Kind.email and not _EMAIL.match(value):
        raise SettingError(defn.key, "invalid email")
    if k == Kind.url and not value.startswith("https://"):
        raise SettingError(defn.key, "links must start with https://")
    if defn.key == "admin_ip_allowlist":
        return normalize_allowlist(defn.key, value)
    return value


def normalize_allowlist(key: str, value: str) -> str:
    """Comma-separated IPs/CIDRs → canonical text; rejects anything that is not an address or network."""
    nets: list[str] = []
    for part in (p.strip() for p in value.split(",")):
        if not part:
            continue
        try:
            nets.append(str(ipaddress.ip_network(part, strict=False)))
        except ValueError as e:
            raise SettingError(key, f"not an IP address or network: {part}") from e
    return ", ".join(nets)


def mask(secret: str) -> str:
    return "" if not secret else "•••• " + (secret[-4:] if len(secret) >= 12 else "")
