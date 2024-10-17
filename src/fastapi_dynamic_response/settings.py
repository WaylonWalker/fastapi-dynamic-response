from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = "local"

    class Config:
        env_file = "config.env"
