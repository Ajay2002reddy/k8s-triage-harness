# pvc-unknown-storageclass
**Breaks:** PVC `uploads` asks for StorageClass `fast-ssd`, which doesn't exist, so it never binds and the `web` pod stays Pending.
**Realistic because:** StorageClass names differ between clouds and clusters (`managed-premium`, `gp3`, `standard`); manifests moved between them break this way. On kind a non-existent class is the only way to get this, because kind has a default class.
**A human checks first:** the pod's FailedScheduling event, then `get pvc` and `get storageclass`.
