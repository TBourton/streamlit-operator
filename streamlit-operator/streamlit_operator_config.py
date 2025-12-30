from pydantic import BaseModel


class GitSyncAuthConfig(BaseModel):
    env: list
    volumeMounts: list
    volumes: list


class StreamlitOperatorConfig(BaseModel):
    baseDnsRecord: str
    suffix: str = "-streamlit"
    gitRepo: str = "https://github.com/tbourton/streamlit-operator.git"
    gitRef: str = "main"

    gitSyncAuthConfig: GitSyncAuthConfig
