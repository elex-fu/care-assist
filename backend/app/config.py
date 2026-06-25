from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "mysql+aiomysql://care:carepass@localhost:3306/care_assist"
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "replace-with-random-secret-in-production"

    WECHAT_APPID: str = ""
    WECHAT_SECRET: str = ""

    OSS_ACCESS_KEY: str = ""
    OSS_SECRET_KEY: str = ""
    OSS_BUCKET: str = ""
    OSS_ENDPOINT: str = ""

    SENTRY_DSN: str = ""
    ENVIRONMENT: str = "development"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 60  # 60 days

    DEBUG: bool = False

    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "logs/care-assist.log"
    LOG_FORMAT: str = "standard"  # "standard" or "json"

    # AI Provider configuration
    DEFAULT_AI_PROVIDER: str = "kimi-code"
    FALLBACK_AI_PROVIDERS: list[str] = []

    # Kimi Code provider (Anthropic protocol via https://api.kimi.com/coding)
    KIMI_CODE_API_KEY: str = ""
    KIMI_CODE_BASE_URL: str = "https://api.kimi.com/coding"
    KIMI_CODE_MODEL: str = "kimi-k2.6"
    KIMI_CODE_TIMEOUT: float = 60.0


settings = Settings()
