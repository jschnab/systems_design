# Text storage implementation

## Overview

I largely followed instructions from the [Pi Kubernetes
Cluster](https://picluster.ricsanfre.com/docs/) website.

Text contents are stored in Longhorn exposed via MinIO. MinIO provides an AWS
S3-compatible interface.

## Installation

### Dependencies

Longhorn depends on `open-iscsi`, which was installed on all machines with:

```bash
apt install open-iscsi
```

Then, we ensure the iscsi_tcp module is loaded by running:

```bash
modprobe iscsi_tcp
```

Finally, we run the `iscsid` service:

```bash
systemctl enable iscsid
systemctl start iscsid
```

### Longhorn

Longhorn was installed in the namespace `longhorn-system` with a plain K8 YAML:

```bash
kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/v1.8.1/deploy/longhorn.yaml
```

### MinIO

MinIO was installed with Helm.

The repo was added and updated with:

```bash
helm repo add minio https://charts.min.io/
helm repo update minio
```

The contents of the chart can be inspected with (saved in the file
`minio-chart`):

```bash
helm show all minio/minio
```

Create a new workspace:

```bash
kubectl create namespace minio
```

Generate an admin root user and password:

```bash
tr -dc A-Za-z0-9 </dev/urandom | head -c20
```

Encode these with `base64` and store them as Kubernetes secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: minio-creds
  namespace: minio
  labels:
    app.kubernetes.io/name: minio
    app.kubernetes.io/component: storage
type: Opaque
data:
  rootUser: <paste-user-here>
  rootPassword: <paste-password-here>
```

We define chart values in `minio-values.yaml`:

```yaml
existingSecret: minio-creds
drivesPerNode: 1
replicas: 3
pools: 1

persistence:
  enabled: true
  storageClass: "longhorn"
  accessMode: ReadWriteOnce
  size: 20Gi

resources:
  requests:
    memory: 1Gi

buckets:
  - name: <bucket-name-here>
    policy: none

```

We install the chart with:

```bash
helm install minio minio/minio -f minio-values.yml --namespace minio
```

We can define users and access policies in the values file, or we can use the
MinIO CLI `mc`:

```bash
mc alias set ${MINIO_ALIAS} http://localhost:9001 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}
mc mb ${MINIO_ALIAS}/${MINIO_BUCKET_NAME}
mc mb ${MINIO_ALIAS}/${MINIO_BUCKET_NAME}-dev
mc admin user add ${MINIO_ALIAS} ${MINIO_PASTEBIN_USER} ${MINIO_PASTEBIN_PASSWORD}
mc admin policy create ${MINIO_ALIAS} pastebin-s3-access bucket-policy.json
mc admin policy attach ${MINIO_ALIAS} pastebin-s3-access --user ${MINIO_PASTEBIN_USER}
```

I did not create an ingress for the MinIO console, so I forward local port 9001 to the
same port of a MinIO pod, and then access this port locally.

The bucket policy is defined like for an S3 bucket in `bucket-policy.json`:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ReadBucket",
            "Effect": "Allow",
            "Action": [
                "s3:GetBucketTagging",
                "s3:ListBucketVersions",
                "s3:ListBucket",
                "s3:ListBucketMultipartUploads",
                "s3:GetBucketLocation"
            ],
            "Resource": [
                "arn:aws:s3:::<bucket-name>"
            ]
        },
        {
            "Sid": "ReadWriteObjects",
            "Effect": "Allow",
            "Action": [
                "s3:DeleteObject",
                "s3:ListMultipartUploadParts",
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObjectVersion",
                "s3:GetObjectVersionAttributes",
                "s3:AbortMultipartUpload",
                "s3:GetObjectTagging",
                "s3:GetObjectVersion"
            ],
            "Resource": [
                "arn:aws:s3:::<bucket-name>/*"
            ]
        }
    ]
}
```
