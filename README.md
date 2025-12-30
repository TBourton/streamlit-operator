# Streamlit Operator

Forked from <https://github.com/fetch-rewards/streamlit-operator>

Streamlit apps are easy to develop, but can be a pain to deploy and keep up to date. The Streamlit Operator makes deploying a streamlit
app as easy as filling out a few fields in a web UI. Plus, it will keep your app up to date with your code via a continuous git sync, so you can focus on building.
If you're already using Kubernetes, this is the easiest way to deploy your apps.

## Installation

The Streamlit Operator comes prepackaged as a Helm chart.  If you've never used helm, please refer to
Helm's [documentation](https://helm.sh/docs) to get started.

Once Helm has been set up correctly, add the repo as follows:

    helm repo add streamlit-operator https://fetch-rewards.github.io/streamlit-operator/

If you had already added this repo earlier, run `helm repo update` to retrieve
the latest versions of the packages.  You can then run `helm search repo
<alias>` to see the charts.

To install the chart run:

    helm install streamlit-operator streamlit-operator/streamlit-chart --set baseDnsRecord=<YOUR-COMPANY>.com

To uninstall the chart:

    helm delete streamlit-operator

After installation, you should have an operator running in a newly created streamlit namespace, as well as a hub app running at `hub-streamlit.<YOUR-COMPANY>.com`.

## Usage

The operator is built around one StreamlitApp CRD that takes required configuration for each app.

## Architecture

![Architecture](docs/imgs/architecture.png)

## Development

### Dependencies

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Helm](https://helm.sh/docs/v3/intro/install)
- [Helm Docs](https://github.com/norwoodj/helm-docs)
- [yq](https://github.com/mikefarah/yq)

```console
uv sync
```
```console
prek install
prek install-hooks
```

## TODOs

- Make work with Istio
- Implement OAuth on hub <https://pypi.org/project/streamlit-oauth/>, <https://docs.streamlit.io/develop/concepts/connections/authentication>
