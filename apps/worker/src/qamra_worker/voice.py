"""«صوت أهلي» for the print files: the listening link a family-voice book prints on every story page."""

from sqlalchemy.orm import Session

from qamra_core import voice
from qamra_core.db.models import Book


def voice_url(db: Session, book: Book, domain: str) -> str | None:
    """`https://{domain}/v/{token}` when an order bought the family-voice add-on for this book, else None.

    The token is created once and never changes (it is printed); the parent can pause and resume it.
    """
    if not db.execute(voice.addon_query(book.id)).scalar():
        return None
    token = db.execute(voice.listen_token_query(book.id)).scalar_one_or_none()
    if token is None:
        token = voice.new_listen_token(book.id)
        db.add(token)
        db.flush()
    return voice.listen_base_url(domain, token.token)
