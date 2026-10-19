"""Database: declarative models, engines and sessions."""

# every new book gets its code before it is written (the session's before_flush listener)
from qamra_core import book_codes  # noqa: F401
from qamra_core.db import (  # noqa: F401  (registers every table on Base.metadata)
    audio,  # the activity books' audio QR recordings
    classic,  # Classic templates and identity portraits
    islamic,  # «قلبي يعرف الله»: the scholar's review of every unit
    models,
    portal,  # the kindergarten portal's tables
    store,
    studio,  # the template studio's theme versions
    text_review,  # staff edits of a story's words before «تأكيد»
)
