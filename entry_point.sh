#!/bin/sh
yq eval ".online_store.password = \"$DB_PASSWORD\"" -i /app/feature_store.yaml
cat /app/feature_store.yaml
python main.py