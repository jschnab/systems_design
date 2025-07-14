# syntax=docker/dockerfile:1
FROM --platform=linux/arm64 arm64v8/alpine:3.20

ARG USER_NAME=pastebin
ARG USER_HOME=/home/${USER_NAME}

RUN apk update \
    && apk update \
    && apk add build-base python3-dev linux-headers \
    && adduser -S ${USER_NAME}

USER ${USER_NAME}
WORKDIR ${USER_HOME}

COPY requirements.txt requirements.txt
COPY src src
COPY run_wsgi run_wsgi

RUN --mount=type=cache,target=${USER_HOME}/.cache python3 -m venv .venv \
    && . .venv/bin/activate \
    && pip install -U pip setuptools wheel \
    && pip install -r requirements.txt

ENTRYPOINT ["./run_wsgi"]
