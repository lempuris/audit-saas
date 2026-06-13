"""Thin wrapper over the S3 operations the documents feature needs:
presigned PUT/GET URLs, object HEAD, and delete. boto3 is imported lazily and
the client cached so unit tests (which monkeypatch these functions) never
construct a real client or require AWS credentials.

Credentials come from the default chain — the ECS task role in production, an
AWS profile/env vars locally.
"""

from functools import lru_cache
from typing import Any

from config.settings import get_settings


@lru_cache
def _client() -> Any:
    import boto3  # imported lazily; see module docstring

    settings = get_settings()
    return boto3.client("s3", region_name=settings.aws_region)


def _bucket() -> str:
    bucket = get_settings().documents_bucket
    if not bucket:
        raise RuntimeError("DOCUMENTS_BUCKET is not configured")
    return bucket


def presigned_put(key: str, content_type: str) -> str:
    """A presigned URL the browser PUTs the file to directly."""
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": _bucket(), "Key": key, "ContentType": content_type},
        ExpiresIn=get_settings().presigned_url_ttl_seconds,
    )


def presigned_get(key: str, filename: str) -> str:
    """A presigned download URL that prompts a save with the original name."""
    return _client().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": _bucket(),
            "Key": key,
            "ResponseContentDisposition": f'attachment; filename="{filename}"',
        },
        ExpiresIn=get_settings().presigned_url_ttl_seconds,
    )


def head(key: str) -> dict[str, Any]:
    """HEAD the object to confirm the upload landed; returns size + version id."""
    response = _client().head_object(Bucket=_bucket(), Key=key)
    return {
        "size_bytes": response.get("ContentLength"),
        "version_id": response.get("VersionId"),
    }


def delete(key: str) -> None:
    _client().delete_object(Bucket=_bucket(), Key=key)
