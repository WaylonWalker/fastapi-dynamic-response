from pydantic import BaseModel, model_validator
from pydantic_settings import BaseSettings


class ApiServer(BaseModel):
    app: str = "fastapi_dynamic_response.main:app"
    port: int = 8000
    reload: bool = True
    log_level: str = "info"
    host: str = "0.0.0.0"
    workers: int = 1
    forwarded_allow_ips: str = "*"
    proxy_headers: bool = True


class Settings(BaseSettings):
    ENV: str = "local"
    DEBUG: bool = False
    api_server: ApiServer = ApiServer()

    class Config:
        env_file = "config.env"

    @model_validator(mode="after")
    def validate_debug(self):
        if self.ENV == "local" and self.DEBUG is False:
            self.DEBUG = True
        return self


settings = Settings()
