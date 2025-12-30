import os

import streamlit as st
from stapp_client import StappClient

st.title("Streamlit Hub")

stapp_client = StappClient()
apps = stapp_client.list_streamlit_apps()

for _idx, item in enumerate(apps):
    if item != "hub":
        st.divider()
        with st.container():
            name = item
            st.write(f"Name: {name}")
            st.write(
                f"URL: https://{name}{os.environ.get('STREAMLIT_HUB_SUFFIX', '-streamlit')}.{os.environ.get('STREAMLIT_HUB_BASE_DNS_RECORD', 'example.com')}"  # noqa: E501
            )
            if st.button(f"Restart app {name}"):
                stapp_client.delete_pod_for_streamlit_app(name)
                st.write("Restarting app...")
            if st.button(f"DANGER!!!: Delete {name}"):
                stapp_client.delete_streamlit_app(name)
                st.write(f"Deleted {name}")
                st.write("Make take a minute or two to clear from UI")


with st.sidebar:
    st.header("Create a new Streamlit App")
    st.write("Create a new Streamlit App by filling out the form below.")
    st.write("Note: This will take a few minutes to build and deploy.")

    app_name = st.text_input("App Name (EX: my-app)")
    repo = st.text_input("Git Repo URL (EX: https://github.com/<YOURORG>/<YOURPROJECT>.git)")
    ref = st.text_input("Git Branch (EX: feature/my-dev-branch)")
    code_dir = st.text_input("Code Directory (EX: src/streamlit-app)")
    additional_spec = st.text_area(
        "Additional Spec (YAML format)",
        value="{}",
        help="Additional spec to merge into the StreamlitApp spec. This should be in YAML format.",
    )

    # check that all fields are filled out
    if not app_name:
        st.error("App Name is required")
    if not repo:
        st.error("Git Repo URL is required")
    if not ref:
        st.error("Git Branch is required")
    if not code_dir:
        st.error("Code Directory is required")

    if app_name and repo and ref and code_dir:  # noqa: SIM102
        if st.button("Create Streamlit App"):
            # Create the custom resource
            stapp_client.create_streamlit_app(app_name, repo, ref, code_dir, additional_spec)
