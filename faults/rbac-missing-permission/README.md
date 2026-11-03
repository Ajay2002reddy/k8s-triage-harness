# rbac-missing-permission
**Breaks:** Role `reporter` grants `configmap` (singular); the API needs `configmaps`, so the reporter's list calls get 403.
**Realistic because:** RBAC accepts any resource string without validation, so a singular/plural typo is a silent, common permission bug.
**A human checks first:** the app's 403 log line (it names the user, verb and resource), then the Role and RoleBinding for that ServiceAccount (`auth can-i`).
