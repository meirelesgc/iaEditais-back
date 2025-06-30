from pydantic import HttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE: str = 'fiotec'
    PG_USER: str = 'postgres'
    PASSWORD: str = 'postgres'
    HOST: str = 'localhost'
    PORT: int = 5432

    OPENAI_API_KEY: str

    CLIENT: HttpUrl = 'http://localhost:3000'

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

    def get_connection_string(self) -> str:
        return f'postgresql://{self.PG_USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DATABASE}'

    def get_connection_string_psycopg3(self) -> str:
        return f'postgresql+psycopg://{self.PG_USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DATABASE}'
