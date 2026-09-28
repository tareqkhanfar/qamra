"""Private S3-compatible object storage (MinIO locally, Cloudflare R2 in production).

Everything is private; browsers only ever get short-lived signed URLs (≤ 15 minutes).
"""

from dataclasses import dataclass
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from qamra_core.settings import MAX_SIGNED_URL_SECONDS, CoreSettings


class ObjectNotFound(Exception):
    pass


@dataclass
class ObjectStorage:
    client: Any  # botocore S3 client (untyped)
    bucket: str
    sse: str | None
    default_ttl: int

    @classmethod
    def from_settings(cls, s: CoreSettings) -> "ObjectStorage":
        client = boto3.client(
            "s3",
            endpoint_url=s.s3_endpoint_url,
            region_name=s.s3_region,
            aws_access_key_id=s.s3_access_key_id.get_secret_value() if s.s3_access_key_id else None,
            aws_secret_access_key=(
                s.s3_secret_access_key.get_secret_value() if s.s3_secret_access_key else None
            ),
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        sse = None if s.s3_sse == "none" else s.s3_sse
        return cls(client=client, bucket=s.s3_bucket, sse=sse, default_ttl=s.s3_signed_url_seconds)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        extra: dict[str, str] = {"ContentType": content_type}
        if self.sse:
            extra["ServerSideEncryption"] = self.sse
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, **extra)

    def get(self, key: str) -> bytes:
        try:
            obj = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                raise ObjectNotFound(key) from e
            raise
        data: bytes = obj["Body"].read()
        return data

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound"):
                return False
            raise
        return True

    def delete(self, key: str) -> None:
        """Idempotent: deleting a missing key is not an error."""
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def delete_prefix(self, prefix: str) -> int:
        """Delete everything under a prefix (e.g. all of one child's objects). Returns the count."""
        deleted = 0
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            keys = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if keys:
                self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": keys, "Quiet": True})
                deleted += len(keys)
        return deleted

    def signed_get_url(self, key: str, ttl: int | None = None) -> str:
        ttl = ttl or self.default_ttl
        if not 0 < ttl <= MAX_SIGNED_URL_SECONDS:
            raise ValueError(f"signed URL ttl must be within {MAX_SIGNED_URL_SECONDS}s")
        url: str = self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=ttl
        )
        return url

    def ping(self) -> bool:
        self.client.head_bucket(Bucket=self.bucket)
        return True


def child_prefix(child_id: object) -> str:
    """All objects derived from one child live under this prefix → one-call deletion."""
    return f"children/{child_id}/"
