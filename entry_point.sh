#!/bin/sh
echo "entry point starting"
yq eval ".project = \"$FEAST_PROJECT_NAME\"" -i /app/feature_store.yaml
yq eval ".registry.path = \"$FEAST_REGISTRY_URL\"" -i /app/feature_store.yaml
yq eval ".online_store.host = \"$DB_HOST\"" -i /app/feature_store.yaml
yq eval ".online_store.port = \"$DB_PORT\"" -i /app/feature_store.yaml
yq eval ".online_store.user = \"$DB_USER\"" -i /app/feature_store.yaml
yq eval ".online_store.password = \"$DB_PASSWORD\"" -i /app/feature_store.yaml
yq eval ".online_store.database = \"$DB_NAME\"" -i /app/feature_store.yaml
cat /app/feature_store.yaml
echo "entry point ending"
python main.py
