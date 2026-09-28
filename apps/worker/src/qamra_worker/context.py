"""Per-process resources for jobs. Created lazily inside the job process (RQ forks per job),
never in the parent, so pooled DB connections are not shared across forks."""

import os
from functools import cache

import sentry_sdk
from sqlalchemy.orm import Session, sessionmaker

from qamra_core.db.session import make_sync_engine, make_sync_sessionmaker
from qamra_core.observability import configure_logging
from qamra_core.storage import ObjectStorage
from qamra_worker.settings import get_settings


@cache
def _sessionmaker(pid: int) -> sessionmaker[Session]:
    return make_sync_sessionmaker(make_sync_engine(get_settings().database_url))


def db_session() -> Session:
    return _sessionmaker(os.getpid())()


@cache
def storage() -> ObjectStorage:
    return ObjectStorage.from_settings(get_settings())


def init_process() -> None:
    s = get_settings()
    configure_logging(s.log_level, s.log_json)
    if s.sentry_dsn:
        sentry_sdk.init(dsn=s.sentry_dsn.get_secret_value(), environment=s.env, send_default_pii=False)
