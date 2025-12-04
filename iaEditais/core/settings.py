from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8'
    )

    DATABASE_URL: str
    DEEPEVAL_API_KEY: str
    DEEPEVAL_CONFIDENT_API_KEY: str
    SECRET_KEY: str = 'SECRET_KEY'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = 'HS256'

    OPENAI_API_KEY: str = '...'

    ALLOWED_ORIGINS: List[str] = [
        'http://localhost:8000',
        'http://localhost:3000',
    ]

    BROKER_URL: str = 'amqp://guest:guest@localhost:5672/'
    CACHE_URL: str = 'redis://localhost:6379/0'

    EVOLUTION_URL: str = 'http://localhost:8080/message/sendText/IaEditais'
    EVOLUTION_KEY: str = 'secret'

    ACCESS_TOKEN_COOKIE_NAME: str = 'access_token'
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = 'lax'
    COOKIE_PATH: str = '/'
