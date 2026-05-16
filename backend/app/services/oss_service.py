"""OSS upload signature service (placeholder for local dev).

Production: integrate Aliyun OSS STS or generate signed POST policy.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings


class OSSService:
    @staticmethod
    def get_sts_token(member_id: str) -> Optional[dict]:
        """Generate temporary STS credentials for direct upload.

        Returns None if OSS is not configured (local dev fallback).
        """
        if not settings.OSS_ACCESS_KEY or not settings.OSS_BUCKET:
            return None

        # Placeholder: in production, call Aliyun STS AssumeRole
        return {
            "access_key_id": settings.OSS_ACCESS_KEY,
            "access_key_secret": settings.OSS_SECRET_KEY,
            "security_token": "sts-token-placeholder",
            "expiration": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "bucket": settings.OSS_BUCKET,
            "endpoint": settings.OSS_ENDPOINT,
            "region": "cn-hangzhou",
        }

    @staticmethod
    def generate_post_signature(member_id: str, report_id: str) -> Optional[dict]:
        """Generate signed POST policy for browser/MiniProgram direct upload.

        Returns None if OSS is not configured.
        """
        if not settings.OSS_ACCESS_KEY or not settings.OSS_BUCKET:
            return None

        # Placeholder: in production, calculate OSS signature with policy
        return {
            "url": f"https://{settings.OSS_BUCKET}.{settings.OSS_ENDPOINT}",
            "form_data": {
                "key": f"reports/{member_id}/{report_id}/${{filename}}",
                "OSSAccessKeyId": settings.OSS_ACCESS_KEY,
                "policy": "base64-policy-placeholder",
                "signature": "signature-placeholder",
            },
        }
