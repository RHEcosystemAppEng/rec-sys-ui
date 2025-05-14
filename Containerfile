FROM registry.access.redhat.com/ubi9/python-311

USER root
WORKDIR /app/

# install and activate env
COPY requirements.txt requirements.txt
RUN pip3 install uv
RUN uv pip install -r requirements.txt

COPY feature_store.yaml feature_store.yaml
COPY main.py main.py
COPY entry_point.sh entry_point.sh
COPY utils.py utils.py
# give premisssions and 
RUN chmod -R 777 . && ls -la
RUN dnf update -y && \
    dnf install -y wget && \
    wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/local/bin/yq &&\
    chmod +x /usr/local/bin/yq

ENTRYPOINT ["/bin/sh", "-c", "/app/entry_point.sh"]