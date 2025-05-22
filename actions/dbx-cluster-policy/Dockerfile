FROM python:alpine3.17

RUN apk --no-cache add git jq \
    && pip --no-cache-dir install databricks-cli

COPY entrypoint.py /entrypoint.py

ENTRYPOINT ["/entrypoint.py"]