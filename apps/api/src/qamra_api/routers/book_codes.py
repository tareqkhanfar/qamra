"""The page a book's «عن قمرة» QR opens (`https://{domain}/b/{code}`, apps/web `[locale]/b/[code]`).

Public and without an account, so it says as little as possible: the child's first name and the product,
for a code that exists; the same 404 for a malformed, unknown or deleted code. No photo, no ids, no order.
"""

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import select

from qamra_api import ratelimit
from qamra_api.auth.router import client_ip
from qamra_api.deps import RedisDep, SessionDep
from qamra_api.errors import ApiError
from qamra_core.book_codes import normalize
from qamra_core.db.models import Book, Child
from qamra_pdf.imprint import product_name

router = APIRouter(prefix="/api/books", tags=["books"])
LOOKUPS_PER_IP_PER_HOUR = 120
# the API marks every answer no-store already
NO_STORE = {"Referrer-Policy": "no-referrer", "X-Robots-Tag": "noindex"}


class BookByCode(BaseModel):
    code: str
    child_name: str  # the first name only
    product_ar: str
    product_en: str


def line_of(book: Book) -> str:
    gen = book.generation or {}
    if gen.get("custom"):
        return "custom"
    return str(gen.get("line") or "magic")


@router.get("/by-code/{code}")
async def by_code(
    code: str, request: Request, response: Response, db: SessionDep, redis: RedisDep
) -> BookByCode:
    if await ratelimit.hit(redis, f"rl:book-code:{client_ip(request)}", 3600) > LOOKUPS_PER_IP_PER_HOUR:
        raise ApiError("too_many_attempts", 429)
    for key, value in NO_STORE.items():
        response.headers[key] = value
    wanted = normalize(code)
    if wanted is None:
        raise ApiError("not_found", 404)
    row = (
        await db.execute(
            select(Book, Child.first_name)
            .join(Child, Child.id == Book.child_id)
            .where(Book.code == wanted, Book.is_sample.is_(False))
        )
    ).first()
    if row is None:
        raise ApiError("not_found", 404)
    book, first_name = row
    line = line_of(book)
    return BookByCode(
        code=book.code,
        child_name=str(first_name),
        product_ar=product_name(line, "ar"),
        product_en=product_name(line, "en"),
    )
