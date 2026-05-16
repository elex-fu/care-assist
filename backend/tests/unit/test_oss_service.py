from unittest.mock import patch

from app.services.oss_service import OSSService


class TestOSSService:
    def test_get_sts_token_when_not_configured(self):
        with patch("app.services.oss_service.settings.OSS_ACCESS_KEY", ""), \
             patch("app.services.oss_service.settings.OSS_BUCKET", ""):
            result = OSSService.get_sts_token("member_123")
            assert result is None

    def test_get_sts_token_when_configured(self):
        with patch("app.services.oss_service.settings.OSS_ACCESS_KEY", "ak_123"), \
             patch("app.services.oss_service.settings.OSS_SECRET_KEY", "sk_456"), \
             patch("app.services.oss_service.settings.OSS_BUCKET", "my-bucket"), \
             patch("app.services.oss_service.settings.OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com"):
            result = OSSService.get_sts_token("member_123")
            assert result is not None
            assert result["access_key_id"] == "ak_123"
            assert result["bucket"] == "my-bucket"
            assert result["region"] == "cn-hangzhou"
            assert "expiration" in result

    def test_generate_post_signature_when_not_configured(self):
        with patch("app.services.oss_service.settings.OSS_ACCESS_KEY", ""), \
             patch("app.services.oss_service.settings.OSS_BUCKET", ""):
            result = OSSService.generate_post_signature("member_123", "report_456")
            assert result is None

    def test_generate_post_signature_when_configured(self):
        with patch("app.services.oss_service.settings.OSS_ACCESS_KEY", "ak_123"), \
             patch("app.services.oss_service.settings.OSS_SECRET_KEY", "sk_456"), \
             patch("app.services.oss_service.settings.OSS_BUCKET", "my-bucket"), \
             patch("app.services.oss_service.settings.OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com"):
            result = OSSService.generate_post_signature("member_123", "report_456")
            assert result is not None
            assert result["url"] == "https://my-bucket.oss-cn-hangzhou.aliyuncs.com"
            assert "reports/member_123/report_456/${filename}" in result["form_data"]["key"]
            assert result["form_data"]["OSSAccessKeyId"] == "ak_123"
