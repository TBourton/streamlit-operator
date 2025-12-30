import os

import yaml
from kubernetes import client, config


class StappClient:
    def __init__(self):
        if os.getenv("ENVIRONMENT") == "local":
            self.config = config.load_kube_config(config_file="~/.kube/config", context="proxy")
        else:
            self.config = config.load_incluster_config()
        self.api = client.CustomObjectsApi()
        self.v1 = client.CoreV1Api()

    def list_streamlit_apps(self):
        # List instances of the custom resource
        custom_resource_list = self.api.list_namespaced_custom_object(
            group="fetch.com", version="v1", namespace="streamlit", plural="streamlit-apps"
        )

        outputs = []
        for item in custom_resource_list["items"]:
            name = item["metadata"]["name"]
            outputs.append(name)
        return outputs

    def create_streamlit_app(self, name, repo, ref, code_dir, additional_spec: str = "{}"):
        spec = {
            "repo": repo,
            "ref": ref,
            "codeDir": code_dir,
        }
        additional_spec_dict = yaml.safe_load(additional_spec) or {}
        spec = deep_update(spec, additional_spec_dict)

        self.api.create_namespaced_custom_object(
            group="fetch.com",
            version="v1",
            namespace="streamlit",
            plural="streamlit-apps",
            body={"apiVersion": "fetch.com/v1", "kind": "StreamlitApp", "metadata": {"name": name}, "spec": spec},
        )

    def delete_streamlit_app(self, name):
        self.api.delete_namespaced_custom_object(
            group="fetch.com",
            version="v1",
            namespace="streamlit",
            plural="streamlit-apps",
            name=name,
            body=client.V1DeleteOptions(propagation_policy="Foreground"),
        )

    def delete_pod_for_streamlit_app(self, name):
        # Find the pod for the custom resource
        pod_list = self.v1.list_namespaced_pod(namespace="streamlit", label_selector=f"app={name}")
        # Delete the pod
        for item in pod_list.items:
            pod_name = item.metadata.name
            self.v1.delete_namespaced_pod(
                name=pod_name,
                namespace="streamlit",
                body=client.V1DeleteOptions(propagation_policy="Foreground"),
            )


def deep_update(mapping, *updating_mappings):
    """https://github.com/pydantic/pydantic/blob/fd2991fe6a73819b48c906e3c3274e8e47d0f761/pydantic/utils.py#L200"""
    updated_mapping = mapping.copy()
    for updating_mapping in updating_mappings:
        for k, v in updating_mapping.items():
            if k in updated_mapping and isinstance(updated_mapping[k], dict) and isinstance(v, dict):
                updated_mapping[k] = deep_update(updated_mapping[k], v)
            else:
                updated_mapping[k] = v
    return updated_mapping
