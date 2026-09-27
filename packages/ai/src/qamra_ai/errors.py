"""Pipeline errors. `user_message_*` are safe to show to parents."""


class QamraError(Exception):
    user_message_ar = "حدث خطأ غير متوقع. جرّبوا مرة أخرى بعد قليل."
    user_message_en = "Something went wrong. Please try again in a moment."


class ProviderError(QamraError):
    """Transient provider failure (network, 5xx, rate limit). Safe to retry."""


class ProviderConfigError(QamraError):
    """Missing key or bad configuration. Not retryable."""


class ContentBlocked(QamraError):
    """Provider or our own safety review rejected the content."""

    user_message_ar = "لم نتمكّن من رسم هذه الصفحة بشكل مناسب، وسنعيد المحاولة تلقائيًا."
    user_message_en = "We couldn't draw this page appropriately and will retry automatically."


class InvalidOutput(QamraError):
    """Model returned output that failed validation."""
