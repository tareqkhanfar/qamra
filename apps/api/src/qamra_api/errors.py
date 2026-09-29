"""API errors with friendly Arabic + English messages (CLAUDE.md §10)."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

MESSAGES: dict[str, tuple[str, str]] = {
    "invalid_credentials": ("البريد الإلكتروني أو كلمة المرور غير صحيحة.", "Email or password is incorrect."),
    "email_taken": (
        "هذا البريد مسجَّل من قبل. جرّبوا تسجيل الدخول.",
        "This email is already registered. Try signing in.",
    ),
    "weak_password": (
        "كلمة المرور قصيرة. استخدموا 8 أحرف على الأقل.",
        "Password is too short. Use at least 8 characters.",
    ),
    "not_authenticated": ("سجّلوا الدخول للمتابعة.", "Please sign in to continue."),
    "token_expired": ("انتهت الجلسة. سجّلوا الدخول مرة أخرى.", "Your session expired. Please sign in again."),
    "forbidden": ("ليست لديكم صلاحية لهذه الصفحة.", "You don't have access to this page."),
    "account_disabled": (
        "هذا الحساب موقوف. تواصلوا معنا للمساعدة.",
        "This account is disabled. Contact us for help.",
    ),
    "too_many_attempts": (
        "محاولات كثيرة. انتظروا قليلًا ثم حاولوا مرة أخرى.",
        "Too many attempts. Please wait a bit and try again.",
    ),
    "invalid_input": (
        "بعض البيانات غير صحيحة. راجعوها وحاولوا مرة أخرى.",
        "Some details are invalid. Please check and try again.",
    ),
    "bad_request": (
        "طلب غير صالح. حدّثوا الصفحة وحاولوا مرة أخرى.",
        "Invalid request. Refresh the page and try again.",
    ),
    "not_found": ("لم نجد ما تبحثون عنه.", "We couldn't find what you're looking for."),
    "google_disabled": (
        "تسجيل الدخول عبر Google غير متاح حاليًا.",
        "Google sign-in is not available right now.",
    ),
    "google_failed": (
        "لم يكتمل تسجيل الدخول عبر Google. حاولوا مرة أخرى.",
        "Google sign-in didn't complete. Please try again.",
    ),
    "registration_closed": (
        "التسجيل مغلق مؤقتاً. حاولوا لاحقاً.",
        "Sign-up is temporarily closed. Please try again later.",
    ),
    "invalid_setting": (
        "قيمة غير صالحة في أحد الحقول. راجعوها وحاولوا مرة أخرى.",
        "One of the values is invalid. Please check it and try again.",
    ),
    "wrong_password": ("كلمة المرور الحالية غير صحيحة.", "The current password is incorrect."),
    "common_password": (
        "كلمة المرور هذه شائعة جداً وسهلة التخمين. اختاروا غيرها.",
        "This password is too common and easy to guess. Please choose another.",
    ),
    "mfa_required": (
        "أدخلوا رمز التحقق من تطبيق المصادقة لإكمال الدخول.",
        "Enter the code from your authenticator app to finish signing in.",
    ),
    "mfa_setup_required": (
        "الإدارة تتطلّب التحقق بخطوتين. فعّلوه أولًا.",
        "The admin area requires two-step verification. Please set it up first.",
    ),
    "invalid_code": ("الرمز غير صحيح أو انتهت صلاحيته.", "The code is wrong or has expired."),
    "mfa_not_pending": (
        "ابدؤوا إعداد التحقق بخطوتين من جديد.",
        "Please start the two-step verification setup again.",
    ),
    "mfa_already_enabled": ("التحقق بخطوتين مفعّل مسبقًا.", "Two-step verification is already on."),
    "admin_requires_2fa": (
        "لا يمكن إيقاف التحقق بخطوتين لحساب إداري.",
        "Two-step verification can't be turned off for an admin account.",
    ),
    "ip_not_allowed": (
        "لا يُسمح بالوصول إلى الإدارة من هذا العنوان.",
        "Admin access isn't allowed from this address.",
    ),
    "consent_required": (
        "يلزم تأكيد موافقة وليّ الأمر المكتوبة قبل رفع الصور.",
        "Written guardian consent must be confirmed before uploading photos.",
    ),
    "invalid_photo": (
        "تعذّر استخدام هذه الصورة. جرّبوا صورة أوضح بوجهٍ واحد.",
        "We couldn't use this photo. Try a clearer photo with one face.",
    ),
    "file_too_large": ("الملف كبير جدًّا (الحد 10 ميغابايت).", "The file is too large (10 MB max)."),
    "budget_exceeded": (
        "تجاوز هذا الكتاب سقف التكلفة. ارفعوا السقف أو اعتمدوه كما هو.",
        "This book reached its cost cap. Raise the cap or approve it as it is.",
    ),
    "busy": (
        "هذا الكتاب قيد التوليد الآن. انتظروا حتى ينتهي.",
        "This book is generating right now. Please wait.",
    ),
    "not_ready": (
        "الكتاب غير جاهز للاعتماد بعد (ملفات الطباعة أو الفحص).",
        "The book isn't ready for approval yet (print files or preflight).",
    ),
    "service_unavailable": (
        "الخدمة غير متاحة مؤقتًا. حاولوا بعد قليل.",
        "The service is temporarily unavailable. Try again shortly.",
    ),
    # ---- the store (Addendum 4)
    "cart_empty": ("السلة فارغة. اختاروا كتابًا أولًا.", "Your cart is empty. Choose a book first."),
    "unknown_product": ("هذا المنتج غير متوفر الآن.", "This product isn't available right now."),
    "invalid_style": (
        "أسلوب الرسم هذا غير متاح لهذا الكتاب.",
        "This art style isn't available for this book.",
    ),
    "invalid_addons": (
        "لا يمكن إضافة هذه الإضافة لهذا الكتاب.",
        "This add-on can't go with this book.",
    ),
    "unknown_zone": ("اختاروا منطقة التوصيل من القائمة.", "Choose a delivery area from the list."),
    "unknown_city": ("اختاروا المدينة من القائمة.", "Choose your city from the list."),
    "items_unavailable": (
        "بعض ما في السلة لم يعد متوفرًا. راجعوا السلة من فضلكم.",
        "Some items in your cart are no longer available. Please review your cart.",
    ),
    "below_minimum": (
        "هذا المنتج يُطلب بكمية أكبر (طلبات الروضات من 20 نسخة).",
        "This product has a minimum quantity (kindergarten orders start at 20).",
    ),
    "express_full": (
        "اكتمل الإنتاج السريع لليوم. أزيلوه أو حاولوا غدًا.",
        "Express production is full for today. Remove it or try tomorrow.",
    ),
    "coupon_invalid": (
        "رمز الخصم غير صالح لهذا الطلب.",
        "This discount code isn't valid for this order.",
    ),
    "terms_required": ("وافقوا على شروط الطلب للمتابعة.", "Please accept the order terms to continue."),
    "try_again": ("لم يكتمل الطلب. حاولوا مرة أخرى.", "The order didn't go through. Please try again."),
    "invalid_transition": (
        "لا يمكن نقل الطلب إلى هذه الحالة من حالته الحالية.",
        "The order can't move to that status from where it is.",
    ),
    "reprint_needs_items": ("اختاروا ما يُعاد طبعه من الطلب.", "Choose which items to reprint."),
    "coupon_exists": ("يوجد كوبون بهذا الرمز.", "A coupon with this code already exists."),
    "bulk_price_pending": (
        "للطلبات من 10 نسخ فأكثر من هذا الكتاب، تواصلوا معنا لعرض سعر خاص.",
        "For 10 copies or more of this book, contact us for a special quote.",
    ),
    # ---- the create flow
    "consent_outdated": (
        "تغيّر نصّ الموافقة. حدّثوا الصفحة واقرؤوه من جديد.",
        "The consent text has changed. Reload the page and read it again.",
    ),
    "photo_required": ("أضيفوا صورة للطفل أولًا.", "Please add a photo of your child first."),
    "redraws_used": (
        "استخدمتم إعادات الرسم المجانية لهذا الطفل. تواصلوا معنا إن احتجتم المساعدة.",
        "You've used the free redraws for this child. Contact us if you need help.",
    ),
    "character_not_approved": (
        "اعتمدوا شخصية الطفل أولًا.",
        "Please approve your child's character first.",
    ),
    "too_many_previews": (
        "وصلتم إلى حد المعاينات لليوم. جرّبوا غدًا أو أكملوا طلبًا حاليًا.",
        "You've reached today's preview limit. Try tomorrow or finish a current order.",
    ),
    # «قمرة كلاسيك» (Addendum 4 §1A)
    "classic_unavailable": (
        "هذه الحكاية غير متوفّرة بعد في «قمرة كلاسيك» بهذا الشكل. جرّبوا «قمرة سحري» أو حكاية أخرى.",
        "This story isn't ready in Qamra Classic for this look yet. Try Qamra Magic or another story.",
    ),
    "template_exists": (
        "يوجد قالب معتمد لهذه الحكاية بهذا الأسلوب والشكل. أعيدوه للمراجعة أولًا لتغييره.",
        "An approved template already exists for this story, style and look. Send it back to review first.",
    ),
    "template_source_invalid": (
        "يمكن تحويل كتاب تجريبي معتمد فقط، لطفل متخيَّل، ومن دون رفيق مرسوم.",
        "Only an approved sample book of an invented child, without a drawn companion, can become a "
        "template.",
    ),
    "template_locked": (
        "هذه الصفحة مقفلة. افتحوا القفل أولًا لتعديلها.",
        "This page is locked. Unlock it first to change it.",
    ),
    "template_incomplete": (
        "لا يمكن اعتماد القالب قبل رسم كل صفحاته وتحديد مكان البطل في كل صفحة يظهر فيها.",
        "The template can be approved only when every page is drawn and every hero page has its hero box.",
    ),
    "free_cover_off": (
        "الغلاف المجاني غير متاح الآن. تصفّحوا الحكايات وابدؤوا كتابكم.",
        "The free cover isn't available right now. Browse the stories and start your book.",
    ),
    "free_cover_used": (
        "صمّمتم غلافًا مجانيًا لهذه الحكاية من قبل. جرّبوا حكاية أخرى أو أكملوا الكتاب.",
        "You already made a free cover for this story. Try another story or finish the book.",
    ),
    # public examples (docs/decisions.md)
    "example_not_sample": (
        "يمكن نشر كتب الأطفال المتخيَّلين التجريبية فقط كنماذج. كتب الأطفال الحقيقيين لا تُنشر أبدًا.",
        "Only sample books of invented children can be published as examples. Real children's books never "
        "are.",
    ),
    "example_not_approved": (
        "اعتمدوا الكتاب أولًا (بغلافه وصفحاته)، ثم انشروه نموذجًا.",
        "Approve the book first (with its cover and pages), then publish it as an example.",
    ),
    "quiz_gaps": (
        "بعض الإجابات لا تصل إلى أي اقتراح. أضيفوا قاعدة تغطيها ثم احفظوا.",
        "Some answers lead to no recommendation. Add a rule that covers them, then save.",
    ),
    "not_orderable": (
        "هذا الكتاب غير متاح للطلب بعد. نخبركم حين يتوفّر.",
        "This book can't be ordered yet. We'll let you know when it's available.",
    ),
    # W5: the reader, share links, payments, print batches
    "book_not_ready": (
        "الكتاب لم يجهز بعد. سنرسل لكم رسالة عندما يصبح جاهزًا للقراءة.",
        "The book isn't ready yet. We'll email you when it's ready to read.",
    ),
    "share_unavailable": (
        "هذا الرابط لم يعد يعمل: ربما انتهت صلاحيته أو أوقفه صاحب الكتاب.",
        "This link no longer works: it may have expired or been turned off by the book's owner.",
    ),
    "payment_unavailable": (
        "الدفع بالبطاقة غير متاح بعد. اختاروا الدفع عند الاستلام.",
        "Card payment isn't available yet. Please choose cash on delivery.",
    ),
    "batch_empty": ("لا توجد طلبات في هذه الدفعة.", "There are no orders in this batch."),
    "batch_not_ready": (
        "بعض طلبات الدفعة غير جاهزة (كتاب غير معتمد أو طلب ملغى). أخرجوها من الدفعة أو اعتمدوا كتبها.",
        "Some orders in this batch aren't ready (a book not approved, or a cancelled order). Remove them or "
        "approve their books.",
    ),
    "link_expired": (
        "انتهت صلاحية الرابط أو استُبدل برابط أحدث. اطلبوا رابطًا جديدًا من فريقنا.",
        "This link has expired or was replaced by a newer one. Ask our team for a new link.",
    ),
    # ---- the kindergarten portal (Phase 4)
    "org_pending": (
        "حساب روضتكم بانتظار موافقة فريقنا. سنتواصل معكم قريبًا.",
        "Your kindergarten account is waiting for our team's approval. We'll be in touch soon.",
    ),
    "org_rejected": (
        "لم نتمكّن من تفعيل حساب الروضة. تواصلوا معنا للمساعدة.",
        "We couldn't activate this kindergarten account. Please contact us.",
    ),
    "not_school": ("هذه الصفحة لحسابات الروضات فقط.", "This page is for kindergarten accounts only."),
    "import_format": (
        "ارفعوا ملف CSV: من Excel اختاروا «حفظ باسم» ثم CSV UTF-8.",
        "Upload a CSV file: in Excel choose Save As, then CSV UTF-8.",
    ),
    "import_empty": ("الملف فارغ أو لا يحتوي أطفالًا.", "The file is empty or has no children."),
    "import_too_many": ("الحد 60 طفلًا في الصف الواحد.", "A class can have at most 60 children."),
    "invite_expired": (
        "لم يعد هذا الرابط صالحًا. اطلبوا من الروضة رابطًا جديدًا.",
        "This link is no longer valid. Please ask the kindergarten for a new one.",
    ),
    "invite_claimed": (
        "هذا الرابط مستخدم من حساب آخر. تواصلوا مع الروضة.",
        "This link is already used by another account. Please contact the kindergarten.",
    ),
    "theme_required": ("اختاروا حكاية الصف أولًا.", "Please choose the class story first."),
    "class_not_ready": (
        "لا يوجد أطفال جاهزون بعد: يلزم موافقة الأهل وشخصية معتمدة.",
        "No children are ready yet: each needs parent consent and an approved character.",
    ),
    "plan_outdated": (
        "تغيّر أطفال الصف منذ آخر توزيع. وزّعوا الصفحات من جديد.",
        "The class changed since the last plan. Please plan the pages again.",
    ),
    "coverage_low": (
        "بعض الأطفال يظهرون أقل من العدد المطلوب. عدّلوا المخطط أو وزّعوا تلقائيًا.",
        "Some children appear fewer times than required. Adjust the plan or plan automatically.",
    ),
    "invalid_plan": (
        "المخطط غير صالح: تحقّقوا من الأطفال في كل صفحة.",
        "The plan isn't valid: please check the children on each page.",
    ),
    "class_book_busy": (
        "كتب الصف قيد الرسم الآن. انتظروا حتى تنتهي.",
        "The class books are being drawn right now. Please wait.",
    ),
    "class_book_locked": (
        "طُلبت كتب هذا الصف ولا يمكن تعديلها الآن. تواصلوا معنا.",
        "This class's books are already ordered and can't change now. Please contact us.",
    ),
    "class_redraws_used": (
        "استخدمتم إعادات الرسم المجانية لهذا الكتاب. تواصلوا معنا للمساعدة.",
        "You've used this class book's free redraws. Contact us for help.",
    ),
    "photo_permission_required": (
        "أكّدوا أن لديكم موافقة الأهالي على طباعة صورة الصف.",
        "Please confirm you have the parents' permission to print the class photo.",
    ),
    "invalid_image": (
        "تعذّر قراءة هذه الصورة. جرّبوا ملف PNG أو JPG.",
        "We couldn't read this image. Try a PNG or JPG file.",
    ),
    "nothing_to_order": ("لا توجد كتب معتمدة للطلب بعد.", "There are no approved books to order yet."),
    "already_ordered": ("طُلبت كتب هذا الصف من قبل.", "This class's books were already ordered."),
    "no_price_list": (
        "لم تُحدَّد أسعار الروضات لهذا الكتاب بعد. تواصلوا معنا.",
        "Kindergarten prices for this book aren't set yet. Please contact us.",
    ),
    "invalid_tiers": (
        "شرائح الأسعار غير صالحة: كميات من 1 فأكثر، بلا تكرار، وأسعار موجبة.",
        "Invalid price tiers: quantities from 1 up, no duplicates, and positive prices.",
    ),
    # ---- the order path (Addendum 9 §1.4–§1.6): codes, gift cards, the gift order
    "code_unknown": (
        "هذا الرمز غير صحيح. تأكّدوا منه وجرّبوا مرة أخرى.",
        "This code isn't valid. Check it and try again.",
    ),
    "gift_card_invalid": (
        "بطاقة الهدية لا تصلح لهذا الطلب. أزيلوها أو جرّبوا بطاقة أخرى.",
        "This gift card can't pay for this order. Remove it or try another one.",
    ),
    "gift_card_changed": (
        "تغيّر رصيد بطاقة الهدية. راجعوا المجموع الجديد في السلة ثم أكّدوا الطلب.",
        "The gift card's balance changed. Check the new total in your cart, then confirm.",
    ),
    "gift_card_exists": ("توجد بطاقة هدية بهذا الرمز.", "A gift card with this code already exists."),
    # ---- the template studio (Addendum 4 §3): theme versions, schedules, staff roles
    "version_open": (
        "لهذا الثيم نسخة مفتوحة بالفعل. أكملوها أو احذفوا المسودة أولًا.",
        "This theme already has an open version. Finish it or discard the draft first.",
    ),
    "version_pending": (
        "النسخة المفتوحة قيد المراجعة أو معتمدة. أعيدوها إلى مسودة لتعديلها.",
        "The open version is in review or approved. Send it back to draft to edit it.",
    ),
    "theme_invalid": (
        "هذا التعديل يخالف قواعد القصة. راجعوا الملاحظات وحاولوا مرة أخرى.",
        "This change breaks the story's rules. Check the notes and try again.",
    ),
    "schedule_invalid": ("اختاروا موعد نشر في المستقبل.", "Choose a publish date in the future."),
    "self_change": (
        "لا يمكنكم تغيير صلاحياتكم بأنفسكم. اطلبوا ذلك من مسؤول آخر.",
        "You can't change your own access. Ask another admin.",
    ),
    # W3: «ارسم صاحبك» and the custom story (Magic)
    "invalid_drawing": (
        "تعذّر استخدام هذه الصورة. صوّروا الرسمة كاملة على ورقتها، في ضوء جيد.",
        "We couldn't use this picture. Photograph the whole drawing on its paper, in good light.",
    ),
    "drawing_gone": (
        "حذفنا الصورة الأصلية للرسمة حفاظًا على الخصوصية. صوّروها من جديد لتعديلها.",
        "We deleted the original photo of the drawing for privacy. Take it again to change it.",
    ),
    "companion_busy": (
        "ما زلنا نرسم الصاحب، أو تم اختياره. انتظروا لحظات أو ابدؤوا برسمة جديدة.",
        "The companion is still being drawn, or was already chosen. Wait a moment or start a new drawing.",
    ),
    "companion_not_ready": (
        "لم يُرسم الصاحب بعد. انتظروا الخيارين ثم اختاروا واحدًا.",
        "The companion isn't drawn yet. Wait for the two options, then choose one.",
    ),
    "companion_not_approved": (
        "اختاروا شكل الصاحب أولًا، أو تخطّوا هذه الخطوة.",
        "Choose the companion's look first, or skip this step.",
    ),
    "companion_in_use": (
        "هذا الصاحب في كتاب لم يكتمل بعد. احذفوه بعد وصول الكتاب، أو احذفوا كل بيانات الطفل الآن.",
        "This companion is in a book that isn't finished yet. Delete it once the book arrives, "
        "or delete all your child's data now.",
    ),
    "custom_story_invalid": (
        "راجعوا تفاصيل الحكاية الخاصة: بعض الحقول ناقصة أو أطول من المسموح.",
        "Check the custom story details: some fields are missing or too long.",
    ),
    "custom_story_unsafe": (
        "بعض ما كتبتموه لا يناسب كتاب أطفال (كالعنف أو أرقام الهواتف والروابط). عدّلوه وحاولوا مرة أخرى.",
        "Some of what you wrote doesn't fit a children's book (like violence, phone numbers or links). "
        "Please edit it and try again.",
    ),
    "custom_story_magic_only": (
        "الحكاية الخاصة متوفرة في الكتاب السحري فقط.",
        "Custom stories are available for Magic books only.",
    ),
    "internal_error": (
        "حدث خطأ غير متوقع. حاولوا مرة أخرى بعد قليل.",
        "Something went wrong. Please try again in a moment.",
    ),
}


class ApiError(Exception):
    def __init__(self, code: str, status: int = 400, details: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.details = details or {}


def error_body(code: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    ar, en = MESSAGES.get(code, MESSAGES["internal_error"])
    body: dict[str, Any] = {"code": code, "message": {"ar": ar, "en": en}}
    if details:
        body["details"] = details
    return {"error": body}


_STATUS_CODES = {
    401: "not_authenticated",
    403: "forbidden",
    404: "not_found",
    405: "bad_request",
    429: "too_many_attempts",
    503: "service_unavailable",
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(error_body(exc.code, exc.details), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = sorted({".".join(str(p) for p in e["loc"][1:]) for e in exc.errors() if len(e["loc"]) > 1})
        return JSONResponse(error_body("invalid_input", {"fields": fields}), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_CODES.get(
            exc.status_code, "bad_request" if exc.status_code < 500 else "internal_error"
        )
        return JSONResponse(error_body(code), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:  # logged by the middleware
        return JSONResponse(error_body("internal_error"), status_code=500)
