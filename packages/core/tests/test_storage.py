import pytest
from qamra_core.settings import CoreSettings
from qamra_core.storage import ObjectNotFound, ObjectStorage, child_prefix


def test_put_get_delete(storage: ObjectStorage) -> None:
    storage.put("children/c1/photos/a.jpg", b"jpeg-bytes", "image/jpeg")
    assert storage.get("children/c1/photos/a.jpg") == b"jpeg-bytes"
    head = storage.client.head_object(Bucket=storage.bucket, Key="children/c1/photos/a.jpg")
    assert head["ServerSideEncryption"] == "AES256"
    storage.delete("children/c1/photos/a.jpg")
    storage.delete("children/c1/photos/a.jpg")  # idempotent
    assert not storage.exists("children/c1/photos/a.jpg")
    with pytest.raises(ObjectNotFound):
        storage.get("children/c1/photos/a.jpg")


def test_delete_prefix_only_touches_that_child(storage: ObjectStorage) -> None:
    for key in ("children/c1/photos/a.jpg", "children/c1/books/b/p1.png", "children/c2/photos/x.jpg"):
        storage.put(key, b"x", "image/png")
    assert storage.delete_prefix(child_prefix("c1")) == 2
    assert storage.exists("children/c2/photos/x.jpg")


def test_signed_urls_expire_within_15_minutes(storage: ObjectStorage) -> None:
    storage.put("k.png", b"x", "image/png")
    assert "X-Amz-Expires=600" in storage.signed_get_url("k.png")
    assert "X-Amz-Expires=900" in storage.signed_get_url("k.png", ttl=900)
    with pytest.raises(ValueError):
        storage.signed_get_url("k.png", ttl=3600)


def test_settings_reject_long_signed_urls() -> None:
    with pytest.raises(ValueError):
        CoreSettings(_env_file=None, s3_signed_url_seconds=3600)  # type: ignore[call-arg]
