import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, BaseSettings, EmailStr, HttpUrl, PostgresDsn, validator

NAMESPACE_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"


class Settings(BaseSettings):
    API_PREFIX_STR: str = "/api/v1"
    API_SECRET_KEY: Optional[str]
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    SERVER_NAME: Optional[str]
    SERVER_HOST: Optional[AnyHttpUrl]

    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://10.0.0.137:5000",
        "http://localhost:5000",
        "https://hdoupe.ngrok.io",
    ]

    WORKERS_API_HOST: Optional[str]
    VIZ_HOST: Optional[str]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    PROJECT_NAMESPACE: str

    @validator("PROJECT_NAMESPACE", pre=True)
    def get_project_namespace(cls, v: Optional[str]) -> str:
        return v or "default"

    NAMESPACE: Optional[str]

    @validator("NAMESPACE", pre=True)
    def get_namespace(cls, v: Optional[str]) -> str:
        if v:
            return v
        elif Path(NAMESPACE_PATH).exists():
            with open(NAMESPACE_PATH) as f:
                return f.read().strip()
        else:
            return "default"

    PROJECT_NAME: str = "C/S Cluster Api"
    SENTRY_DSN: Optional[HttpUrl] = None

    @validator("SENTRY_DSN", pre=True)
    def sentry_dsn_can_be_blank(cls, v: str) -> Optional[str]:
        if v and len(v) == 0:
            return None
        return v

    DB_HOST: Optional[str]
    DB_USER: Optional[str]
    DB_PASS: Optional[str]
    DB_NAME: Optional[str]

    TEST_DB_NAME: str = "test"
    TEST_DB_PASS: str = os.environ.get("TEST_DB_PASS", "test")

    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return "{scheme}://{user}:{password}@{host}{path}".format(
            scheme="postgresql",
            user=values.get("DB_USER"),
            password=values.get("DB_PASS"),
            host=values.get("DB_HOST"),
            path=f"/{values.get('DB_NAME')}",
        )

    FIRST_SUPERUSER: Optional[EmailStr]
    FIRST_SUPERUSER_PASSWORD: Optional[str]

    JOB_NAMESPACE: str = "worker-api"

    GITHUB_TOKEN: Optional[str]
    GITHUB_BUILD_BRANCH: Optional[str]

    class Config:
        case_sensitive = True


settings = Settings()
