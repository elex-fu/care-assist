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

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 60  # 60 days

    DEBUG: bool = False


settings = Settings()
