FROM python:3.12.0a6-alpine3.17

RUN apk --no-cache add git jq curl \
    && pip --no-cache-dir install databricks-cli

COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]