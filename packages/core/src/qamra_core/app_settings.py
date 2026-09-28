"""Admin-managed system settings: the registry (types, limits, defaults) and validation.

Everything an operator may change without a deploy lives here: prices, contact details, AI keys and
models, notifications, site behaviour and privacy retention (within the privacy rules' bounds).
Infrastructure secrets (database, JWT, encryption keys) stay in the environment, never in the admin.

- `public` settings are served to the website (`GET /api/settings/public`).
- `secret` settings are encrypted at rest and never returned in full (only "set" + last 4 chars).
- `example=True` marks a default that is a placeholder to replace (the admin shows a badge).
"""

import enum
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


class Kind(enum.StrEnum):
    text = "text"
    number = "number"  # integer
    money = "money"  # decimal, 2 places
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
    Group("notifications", "البريد والواتساب", "Email & WhatsApp"),
    Group("privacy", "الخصوصية والحذف", "Privacy & retention"),
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
    SettingDef("fal_key", "ai_keys", Kind.secret, "", "مفتاح fal.ai (FLUX)", "fal.ai (FLUX) key"),
    # ---- AI models
    SettingDef(
        "image_provider",
        "ai_models",
        Kind.choice,
        "gemini",
        "مزوّد الرسم",
        "Image provider",
        choices=("gemini", "flux", "openai"),
    ),
    SettingDef(
        "text_model",
        "ai_models",
        Kind.text,
        "claude-opus-5",
        "نموذج كتابة القصة",
        "Story model",
        max_length=80,
    ),
    SettingDef(
        "text_model_fast",
        "ai_models",
        Kind.text,
        "claude-opus-5",
        "نموذج المراجعة والأمان",
        "Review & safety model",
        max_length=80,
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
        "gemini_image_size",
        "ai_models",
        Kind.choice,
        "2K",
        "دقة Gemini",
        "Gemini resolution",
        choices=("1K", "2K", "4K"),
    ),
    SettingDef(
        "flux_image_model",
        "ai_models",
        Kind.text,
        "fal-ai/flux-2-pro/edit",
        "نموذج FLUX",
        "FLUX model",
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
    SettingDef(
        "image_concurrency",
        "ai_models",
        Kind.number,
        4,
        "صفحات تُرسم بالتوازي",
        "Pages drawn in parallel",
        min=1,
        max=16,
    ),
    SettingDef(
        "page_max_regenerations",
        "ai_models",
        Kind.number,
        1,
        "إعادات الرسم التلقائية",
        "Automatic redraws",
        min=0,
        max=3,
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
    if k == Kind.money:
        try:
            amount = Decimal(str(raw)).quantize(Decimal("0.01"))
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
    return value


def mask(secret: str) -> str:
    return "" if not secret else "•••• " + (secret[-4:] if len(secret) >= 12 else "")
