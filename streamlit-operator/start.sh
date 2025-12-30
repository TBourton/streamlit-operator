#!/bin/sh

pip install -r requirements.txt

python -m kopf run --liveness=http://0.0.0.0:8080/healthz --namespace=streamlit main.py
