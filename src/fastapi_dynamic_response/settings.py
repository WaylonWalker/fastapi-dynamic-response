from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = "local"
    DEBUG: bool = False

    class Config:
        env_file = "config.env"

    @model_validator(mode="after")
    def validate_debug(self):
        if self.ENV == "local" and self.DEBUG is False:
            self.DEBUG = True
        return self


settings = Settings()
