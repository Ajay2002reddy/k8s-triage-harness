# configmap-missing
**Breaks:** the `api` container takes two env vars from ConfigMap `api-settings`, which doesn't exist; the namespace has `api-config`.
**Realistic because:** a renamed ConfigMap or the wrong apply order leaves pods in CreateContainerConfigError.
**A human checks first:** the pod status (CreateContainerConfigError) and its event, then `get configmaps`.
