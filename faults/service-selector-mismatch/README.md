# service-selector-mismatch
**Breaks:** the `api` pods moved to the `app.kubernetes.io/name` label, but Service `api` still selects `app: api`, so it has no endpoints.
**Realistic because:** label migrations (to the recommended `app.kubernetes.io/*` labels) often miss one Service.
**A human checks first:** the Service's endpoints (empty although pods are Ready), then compare its selector with the pod labels.
