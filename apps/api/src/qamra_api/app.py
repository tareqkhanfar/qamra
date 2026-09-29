"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import Depends, FastAPI
from redis import Redis as SyncRedis
from redis.asyncio import Redis

from qamra_api.auth.router import router as auth_router
from qamra_api.deps import require_client_header
from qamra_api.errors import install_error_handlers
from qamra_api.logging import RequestLogMiddleware
from qamra_api.routers.admin_books import router as admin_books_router
from qamra_api.routers.admin_catalog import router as admin_catalog_router
from qamra_api.routers.admin_classic import router as admin_classic_router
from qamra_api.routers.admin_gift_cards import router as admin_gift_cards_router
from qamra_api.routers.admin_orders import router as admin_orders_router
from qamra_api.routers.admin_packing import router as admin_packing_router
from qamra_api.routers.admin_portal import router as admin_portal_router
from qamra_api.routers.admin_print_batches import router as admin_print_batches_router
from qamra_api.routers.admin_print_costs import router as admin_print_costs_router
from qamra_api.routers.admin_reports import router as admin_reports_router
from qamra_api.routers.admin_self_hosted import router as admin_self_hosted_router
from qamra_api.routers.admin_staff import router as admin_staff_router
from qamra_api.routers.admin_studio import router as admin_studio_router
from qamra_api.routers.admin_themes import router as admin_themes_router
from qamra_api.routers.companions import router as companions_router
from qamra_api.routers.create import router as create_router
from qamra_api.routers.e2e import router as e2e_router
from qamra_api.routers.examples import admin_router as examples_admin_router
from qamra_api.routers.examples import router as examples_router
from qamra_api.routers.family import router as family_router
from qamra_api.routers.family_members import router as family_members_router
from qamra_api.routers.free_cover import router as free_cover_router
from qamra_api.routers.health import router as health_router
from qamra_api.routers.invite import router as invite_router
from qamra_api.routers.leads import admin_router as admin_leads_router
from qamra_api.routers.leads import router as leads_router
from qamra_api.routers.portal import router as portal_router
from qamra_api.routers.portal_book import router as portal_book_router
from qamra_api.routers.portal_children import router as portal_children_router
from qamra_api.routers.portal_order import router as portal_order_router
from qamra_api.routers.printer import router as printer_router
from qamra_api.routers.reader import router as reader_router
from qamra_api.routers.settings import admin_router as settings_admin_router
from qamra_api.routers.settings import public_router as settings_public_router
from qamra_api.routers.shop import admin_router as shop_admin_router
from qamra_api.routers.shop import router as shop_router
from qamra_api.routers.themes import router as themes_router
from qamra_api.routers.voice import router as voice_router
from qamra_api.routers.voice_public import router as voice_public_router
from qamra_api.security_headers import SecurityHeadersMiddleware
from qamra_api.settings import ApiSettings, get_settings
from qamra_api.store.order_path import router as order_path_router
from qamra_api.store.payments import router as payments_router
from qamra_api.store.router import router as store_router
from qamra_core.db.session import make_async_engine, make_async_sessionmaker
from qamra_core.observability import configure_logging
from qamra_core.storage import ObjectStorage


def _init_sentry(settings: ApiSettings) -> None:
    if settings.sentry_dsn is None:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        environment=settings.env,
        send_default_pii=False,
        traces_sample_rate=0.0,
    )


def create_app(settings: ApiSettings | None = None, *, manage_resources: bool = True) -> FastAPI:
    """`manage_resources=False` lets tests inject their own db/redis/storage into `app.state`."""
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)
    _init_sentry(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if not manage_resources:
            yield
            return
        engine = make_async_engine(settings.database_url, settings.db_pool_size)
        app.state.sessionmaker = make_async_sessionmaker(engine)
        app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
        app.state.rq_redis = SyncRedis.from_url(settings.redis_url)  # RQ needs raw bytes, sync client
        app.state.storage = ObjectStorage.from_settings(settings)
        try:
            yield
        finally:
            await app.state.redis.aclose()
            app.state.rq_redis.close()
            await engine.dispose()

    app = FastAPI(
        title=f"{settings.brand_name_en} API",
        version="0.1.0",
        lifespan=lifespan,
        dependencies=[Depends(require_client_header)],
        docs_url="/api/docs" if settings.env != "prod" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.env != "prod" else None,
    )
    app.state.settings = settings
    install_error_handlers(app)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLogMiddleware)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(themes_router)
    app.include_router(leads_router)
    app.include_router(admin_leads_router)
    app.include_router(family_members_router)  # W4: the illustrated-family add-on (off by default)
    app.include_router(family_router)
    app.include_router(settings_public_router)
    app.include_router(settings_admin_router)
    app.include_router(admin_books_router)
    app.include_router(store_router)
    app.include_router(admin_orders_router)
    app.include_router(create_router)
    app.include_router(companions_router)  # W3: «ارسم صاحبك» in the parent flow
    app.include_router(admin_catalog_router)
    app.include_router(admin_print_costs_router)
    app.include_router(admin_reports_router)
    app.include_router(admin_self_hosted_router)
    app.include_router(admin_classic_router)
    app.include_router(admin_themes_router)  # W8: the template studio (Addendum 4 §3)
    app.include_router(admin_studio_router)
    app.include_router(admin_staff_router)
    app.include_router(free_cover_router)
    app.include_router(examples_router)
    app.include_router(examples_admin_router)
    app.include_router(shop_router)
    app.include_router(shop_admin_router)
    app.include_router(reader_router)  # W5: the web reader and share links
    app.include_router(payments_router)
    app.include_router(admin_print_batches_router)
    app.include_router(printer_router)
    app.include_router(portal_router)  # W4: the kindergarten portal (Phase 4)
    app.include_router(portal_children_router)
    app.include_router(portal_book_router)
    app.include_router(portal_order_router)
    app.include_router(invite_router)
    app.include_router(admin_portal_router)
    app.include_router(order_path_router)  # W2: Addendum 9 order path (add-ons, gift, codes, cross-sell)
    app.include_router(admin_gift_cards_router)
    app.include_router(admin_packing_router)
    app.include_router(voice_router)  # W6: «صوت أهلي» (Phase 5)
    app.include_router(voice_public_router)
    if settings.e2e_fixtures and settings.env != "prod":  # test-only fixtures (tests/e2e), never in prod
        app.include_router(e2e_router)
    return app
