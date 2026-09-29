"""Database: declarative models, engines and sessions."""

from qamra_core.db import (  # noqa: F401  (registers every table on Base.metadata)
    classic,  # Classic templates and identity portraits
    models,
    portal,  # the kindergarten portal's tables
    store,
    studio,  # the template studio's theme versions
)
