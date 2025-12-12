from functools import lru_cache
from pydantic import HttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "local"
    trello_webhook_secret: str = ""
    github_webhook_secret: str = ""
    queue_url: str = ""
    repo_root: str = "/tmp/repos"
    runner_image: str = ""
    github_app_id: str = ""
    github_private_key: str = ""
    github_pat: str = ""
    trello_api_key: str = ""
    trello_token: str = ""
    trello_key: str = ""
    trello_akey: str = ""
    trello_board_id: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
