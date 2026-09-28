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
    "service_unavailable": (
        "الخدمة غير متاحة مؤقتًا. حاولوا بعد قليل.",
        "The service is temporarily unavailable. Try again shortly.",
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
