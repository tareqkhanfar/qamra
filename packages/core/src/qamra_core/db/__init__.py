"""Database: declarative models, engines and sessions."""

from qamra_core.db import (  # noqa: F401  (registers every table on Base.metadata)
    audio,  # the activity books' audio QR recordings
    classic,  # Classic templates and identity portraits
    islamic,  # «قلبي يعرف الله»: the scholar's review of every unit
    models,
    portal,  # the kindergarten portal's tables
    store,
    studio,  # the template studio's theme versions
)
