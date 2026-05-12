from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+aiomysql://care:carepass@localhost:3306/care_assist"
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "replace-with-random-secret-in-production"

    WECHAT_APPID: str = ""
    WECHAT_SECRET: str = ""

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 60  # 60 days

    DEBUG: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
