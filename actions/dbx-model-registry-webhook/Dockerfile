FROM python:3.12.0a6-alpine3.17

RUN apk --no-cache add git \
    && pip --no-cache-dir install requests

COPY entrypoint.py /entrypoint.py

ENTRYPOINT ["/entrypoint.py"]