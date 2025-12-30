import logging

import kopf
import kubernetes
import pydantic
import yaml
from kubernetes.client.rest import ApiException
from streamlit_app_manifest_templating import template_deployment, template_ingress, template_service
from streamlit_app_spec_schema import StreamlitAppSpec
from streamlit_operator_config import StreamlitOperatorConfig

config: StreamlitOperatorConfig


@kopf.on.startup()  # type: ignore
def configure(settings: kopf.OperatorSettings, **_):  # noqa: ARG001
    global config

    with open("/config/config.yaml") as f:
        config = StreamlitOperatorConfig(**yaml.safe_load(f))

    logging.info("Loaded config: %s", config)
    _ = kubernetes.config.load_incluster_config()  # type: ignore
    client = kubernetes.client.CustomObjectsApi()  # type: ignore

    group = "fetch.com"
    version = "v1"
    namespace = "streamlit"
    plural = "streamlit-apps"
    name = "hub"

    body = {
        "apiVersion": f"{group}/{version}",
        "kind": "StreamlitApp",
        "metadata": {
            "name": name,
            "namespace": namespace,
        },
        "spec": {
            "repo": config.gitRepo,
            "ref": config.gitRef,
            "codeDir": "streamlit-hub",
            "serviceAccountName": "streamlit-serviceaccount",
            "additionalEnv": [
                {"name": "STREAMLIT_HUB_SUFFIX", "value": config.suffix},
                {"name": "STREAMLIT_HUB_BASE_DNS_RECORD", "value": config.baseDnsRecord},
            ],
        },
    }

    # We want to always update the hub on startup, to ensure any new operator version is reflected
    kws = {
        "group": group,
        "version": version,
        "namespace": namespace,
        "plural": plural,
        "body": body,
    }
    try:
        # First try to REPLACE
        replaced = client.patch_namespaced_custom_object(name=name, **kws)
        logging.info("Replaced existing StreamlitApp %s: %s", name, replaced)
        return replaced
    except ApiException as e:
        if e.status != 404:
            logging.exception("Error replacing StreamlitApp: %s")
            raise kopf.PermanentError(f"Error replacing StreamlitApp: {e}") from e

        logging.info("StreamlitApp %s not found, will create it", name)

    # If not found, create it
    try:
        created = client.create_namespaced_custom_object(**kws)
        logging.info("Created StreamlitApp %s: %s", name, created)
        return created
    except ApiException as e:
        logging.exception("Error creating or patching StreamlitApp: %s")
        raise kopf.PermanentError(f"Error creating or patching StreamlitApp: {e}") from e


@kopf.on.create("streamlit-apps")  # type: ignore
def create_fn(spec, name, namespace, logger, **kwargs):  # noqa: ARG001
    # Override the namespace, since the operator won't have permissions to create the apps anywhere else anyway
    namespace = "streamlit"
    dns_name = make_dns_name(name)
    try:
        spec = StreamlitAppSpec(**(spec or {}))
    except pydantic.ValidationError as e:
        raise kopf.PermanentError(f"Spec validation error: {e}") from e

    # Template the deployment
    deployment_data = template_deployment(name, spec, dns_name, config.gitSyncAuthConfig)
    kopf.adopt(deployment_data)

    # Template the service
    service_data = template_service(name, spec)
    kopf.adopt(service_data)

    # Template the ingress
    ingress_data = template_ingress(name, spec, dns_name)
    kopf.adopt(ingress_data)

    api = kubernetes.client.CoreV1Api()  # type: ignore
    apps_api = kubernetes.client.AppsV1Api()  # type: ignore
    networking_api = kubernetes.client.NetworkingV1Api()  # type: ignore

    deployment_obj = apps_api.create_namespaced_deployment(namespace=namespace, body=deployment_data)
    logger.info("Created deployment: %s", deployment_obj.metadata.name)

    service_obj = api.create_namespaced_service(namespace=namespace, body=service_data)
    logger.info("Created service: %s", service_obj.metadata.name)

    ingress_obj = networking_api.create_namespaced_ingress(namespace=namespace, body=ingress_data)
    logger.info("Created ingress: %s", ingress_obj.metadata.name)

    return {
        "ingress-name": ingress_obj.metadata.name,
        "service-name": service_obj.metadata.name,
        "deployment-name": deployment_obj.metadata.name,
        "streamlit-app-name": name,
        "dns-name": dns_name,
    }


@kopf.on.update("streamlit-apps")
def update_fn(spec, status, namespace, logger, **kwargs):  # noqa: ARG001
    # Override the namespace, since the operator won't have permissions to create the apps anywhere else anyway
    namespace = "streamlit"

    try:
        spec = StreamlitAppSpec(**(spec or {}))
    except pydantic.ValidationError as e:
        raise kopf.PermanentError(f"Spec validation error: {e}") from e

    name = status["create_fn"]["streamlit-app-name"]
    dns_name = make_dns_name(name)

    # Template the deployment
    deployment_name = status["create_fn"]["deployment-name"]
    assert deployment_name == name, "Deployment name mismatch!"
    deployment_data = template_deployment(name, spec, dns_name, config.gitSyncAuthConfig)
    kopf.adopt(deployment_data)

    # Template the service
    service_name = status["create_fn"]["service-name"]
    assert service_name == f"{name}-service", "Service name mismatch!"
    service_data = template_service(name, spec)
    kopf.adopt(service_data)

    # Template the ingress
    ingress_name = status["create_fn"]["ingress-name"]
    assert ingress_name == f"{name}-ing", "Ingress name mismatch!"
    ingress_data = template_ingress(name, spec, dns_name)
    kopf.adopt(ingress_data)

    api = kubernetes.client.CoreV1Api()  # type: ignore
    apps_api = kubernetes.client.AppsV1Api()  # type: ignore
    networking_api = kubernetes.client.NetworkingV1Api()  # type: ignore

    # Replace the deployment
    deployment_obj = apps_api.replace_namespaced_deployment(
        name=deployment_name,
        namespace=namespace,
        body=deployment_data,
    )
    logger.info("Replaced deployment: %s", deployment_obj.metadata.name)

    # Replace the service
    service_obj = api.replace_namespaced_service(name=service_name, namespace=namespace, body=service_data)
    logger.info("Replaced service: %s", service_obj.metadata.name)

    # Replace the ingress
    ingress_obj = networking_api.replace_namespaced_ingress(
        name=ingress_name,
        namespace=namespace,
        body=ingress_data,
    )
    logger.info("Replaced ingress: %s", ingress_obj.metadata.name)


def make_dns_name(name: str) -> str:
    return f"{name}{config.suffix}.{config.baseDnsRecord}"
