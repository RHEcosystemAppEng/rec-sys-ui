FROM registry.access.redhat.com/ubi9/python-312

USER root
WORKDIR /app/

# install and activate env
COPY entry_point.sh feature_store.yaml main.py pyproject.toml utils.py .

RUN pip3 install uv
RUN uv pip install -r pyproject.toml
RUN dnf update -y && \
    dnf install -y wget && \
    wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/local/bin/yq &&\
    chmod +x /usr/local/bin/yq

# give premisssions and 
RUN chmod -R 777 . && ls -la

ENTRYPOINT ["/bin/sh", "-c", "/app/entry_point.sh"]
