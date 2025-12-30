from streamlit_app_spec_schema import StreamlitAppSpec
from streamlit_operator_config import GitSyncAuthConfig


def template_deployment(name, streamlit_app_spec: StreamlitAppSpec, git_sync_auth_config: GitSyncAuthConfig):
    spec = streamlit_app_spec
    common_env = [
        {"name": "DEBIAN_FRONTEND", "value": "noninteractive"},
    ]

    deployment_dict = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": name, "namespace": "streamlit", "labels": {"app": name, **spec.additionalLabels}},
        "spec": {
            "replicas": spec.replicas,
            "selector": {"matchLabels": {"app": name}},
            "template": {
                "metadata": {"labels": {"app": name, "app.kubernetes.io/name": name, **spec.additionalLabels}},
                "spec": {
                    "enableServiceLinks": spec.enableServiceLinks,
                    "strategy": {"type": "RollingUpdate", "rollingUpdate": {"maxUnavailable": 1, "maxSurge": 0}},
                    "securityContext": {"fsGroup": 65533},  # to make SSH key readable
                    "serviceAccountName": spec.serviceAccountName,
                    "containers": [
                        {
                            "name": "streamlit",
                            "image": spec.image,
                            "env": [
                                {"name": "IN_HUB", "value": "True"},
                                {"name": "CODE_DIR", "value": f"repo/{spec.codeDir}"},
                                {"name": "ENTRYPOINT", "value": spec.entrypoint},
                                {"name": "REQUIREMENTS", "value": spec.requirements},
                                *common_env,
                                *spec.additionalEnv,
                            ],
                            "command": ["/app/launch/launch.sh"],
                            "ports": [{"containerPort": 80}],
                            "volumeMounts": [
                                {"name": "code", "mountPath": "/app"},
                                {"name": "launch", "mountPath": "/app/launch"},
                                *spec.additionalVolumeMounts,
                            ],
                            "livenessProbe": {
                                "httpGet": {"path": "/_stcore/health", "port": 80},
                                "failureThreshold": 3,
                                "periodSeconds": 10,
                            },
                            "readinessProbe": {
                                "httpGet": {"path": "/_stcore/health", "port": 80},
                                "failureThreshold": 3,
                                "periodSeconds": 10,
                            },
                            "startupProbe": {
                                "httpGet": {"path": "/_stcore/health", "port": 80},
                                "failureThreshold": 30,
                                "periodSeconds": 10,
                                "initalDelaySeconds": 5,
                            },
                        },
                        {
                            "name": "git-sync",
                            "image": "registry.k8s.io/git-sync/git-sync:v4.5.0",
                            "volumeMounts": [
                                *git_sync_auth_config.volumeMounts,
                                {"name": "code", "mountPath": "/tmp/code"},
                            ],
                            "env": [
                                {"name": "GITSYNC_REPO", "value": spec.repo},
                                {"name": "GITSYNC_REF", "value": spec.ref},
                                {"name": "GITSYNC_ROOT", "value": "/tmp/code"},
                                {"name": "GITSYNC_LINK", "value": "repo"},
                                {"name": "GITSYNC_SSH_KNOWN_HOSTS", "value": "true"},
                                {"name": "GITSYNC_PERIOD", "value": "10s"},
                                {"name": "GITSYNC_MAX_FAILURES", "value": "6"},
                                *git_sync_auth_config.env,
                                *common_env,
                            ],
                            "securityContext": {"runAsUser": 65533},  # git-sync user
                        },
                    ],
                    "volumes": [
                        {"name": "code", "emptyDir": {}},
                        {"name": "launch", "configMap": {"name": "streamlit-launch-script", "defaultMode": 0o500}},
                        *git_sync_auth_config.volumes,
                        *spec.additionalVolumes,
                    ],
                },
            },
        },
    }

    return deployment_dict


def template_service(name):
    svc_name = make_service_name(name)
    container_port = 80
    target_port = container_port
    service_dict = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": svc_name, "namespace": "streamlit"},
        "spec": {
            "ports": [{"port": 80, "targetPort": target_port, "protocol": "TCP", "name": "http-port"}],
            "selector": {"app": name},
        },
    }
    return service_dict


def template_ingress(
    name,
    streamlit_app_spec: StreamlitAppSpec,
    dns_name: str,
):
    ing_name = make_ingress_name(name)
    service_name = make_service_name(name)

    spec = streamlit_app_spec

    ingress_dict = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {
            "name": f"{ing_name}",
            "annotations": spec.ingress.annotations,
        },
        "spec": {
            "ingressClassName": spec.ingress.ingressClassName,
            "rules": [
                {
                    "host": dns_name,
                    "http": {
                        "paths": [
                            {
                                "path": "/",
                                "pathType": "ImplementationSpecific",
                                "backend": {"service": {"name": f"{service_name}", "port": {"number": 80}}},
                            }
                        ]
                    },
                }
            ],
        },
    }
    return ingress_dict


def make_service_name(name: str) -> str:
    return f"{name}-service"


def make_ingress_name(name: str) -> str:
    return f"{name}-ing"
