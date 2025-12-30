import yaml
from pydantic import BaseModel, field_validator


class Ingress(BaseModel):
    # enabled: bool = True
    annotations: dict[str, str] = {}
    ingressClassName: str = "nginx"


class StreamlitAppSpec(BaseModel):
    repo: str
    ref: str
    codeDir: str
    entrypoint: str = "main.py"
    requirements: str = "requirements.txt"  # Path to requirements file relative to codeDir

    enableServiceLinks: bool = False
    serviceAccountName: str = "default"

    replicas: int = 1
    image: str = "python:3.11.14-slim"

    additionalLabels: dict[str, str] = {}
    additionalVolumes: list = []
    additionalVolumeMounts: list = []
    additionalEnv: list = []

    ingress: Ingress = Ingress()

    @field_validator("codeDir", "entrypoint", "requirements", mode="after")
    @classmethod
    def remove_leading_and_trailing_slashes(cls, value: str) -> str:
        return value.strip("/")


def make_streamlit_app_manifest(name: str, **spec_kws) -> dict:
    spec = StreamlitAppSpec(**spec_kws)

    manifest = {
        "apiVersion": "fetch.com/v1",
        "kind": "StreamlitApp",
        "metadata": {"name": name, "namespace": "streamlit"},
        "spec": spec.model_dump(mode="json"),
    }
    return manifest


if __name__ == "__main__":
    manifest = make_streamlit_app_manifest(
        name="name",
        repo="https://github.com/TBourton/streamlit-operator.git",
        ref="main",
        codeDir="demo-app",
    )

    manifest_str = yaml.dump(manifest, default_flow_style=False, sort_keys=False, indent=2)
    print(manifest_str)  # noqa: T201
