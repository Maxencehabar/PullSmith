from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "local"
    trello_webhook_secret: str = ""
    github_webhook_secret: str = ""
    queue_url: str = ""
    repo_root: str = "/Users/maxencehabar/Documents/PullSmith/repos"
    repo_urls: list[str] = [
        "https://github.com/youdyApprentis/youdy-front",
        "https://github.com/youdyApprentis/youdy-back",
        "https://github.com/youdyApprentis/youdy-functions",
    ]
    runner_image: str = ""
    github_app_id: str = ""
    github_private_key: str = ""
    github_pat: str = ""
    vercel_token: str = ""
    vercel_team_id: str = ""
    vercel_project_map: dict[str, str] = {
        "youdy-front": "youdy-front-max",
        "youdy-back": "youdy-back-max",
    }
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

    @field_validator("repo_urls", mode="before")
    @classmethod
    def _split_repo_urls(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            parts = [item.strip() for item in value.split(",")]
            return [item for item in parts if item]
        return []

    @field_validator("vercel_project_map", mode="before")
    @classmethod
    def _parse_vercel_project_map(cls, value):
        if value is None:
            return {}
        if isinstance(value, dict):
            return {str(k).strip(): str(v).strip() for k, v in value.items() if str(k).strip() and str(v).strip()}
        if isinstance(value, str):
            mapping: dict[str, str] = {}
            pairs = [item.strip() for item in value.split(",") if item.strip()]
            for pair in pairs:
                if "=" not in pair:
                    continue
                repo, project = pair.split("=", 1)
                repo = repo.strip()
                project = project.strip()
                if repo and project:
                    mapping[repo] = project
            return mapping
        return {}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
