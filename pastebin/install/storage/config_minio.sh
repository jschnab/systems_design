#!/usr/bin/env bash

set -ex

mc alias set ${MINIO_ALIAS} http://localhost:9001 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}
mc mb ${MINIO_ALIAS}/${MINIO_BUCKET_NAME}
mc mb ${MINIO_ALIAS}/${MINIO_BUCKET_NAME}-dev
mc admin user add ${MINIO_ALIAS} ${MINIO_PASTEBIN_USER} ${MINIO_PASTEBIN_PASSWORD}
mc admin policy create ${MINIO_ALIAS} pastebin-s3-access bucket-policy.json
mc admin policy attach ${MINIO_ALIAS} pastebin-s3-access --user ${MINIO_PASTEBIN_USER}
