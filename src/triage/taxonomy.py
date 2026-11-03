"""Root-cause categories: the fixed label set that makes grading objective.

The agent must answer with exactly one ``Category``; the primary eval metric is an
exact match against ``category`` in ``faults/<id>/truth.yaml``.

The values come verbatim from docs/PROJECT_BRIEF.md. Change this enum only through an
ADR (CLAUDE.md): adding or renaming a value silently changes what "accuracy" means.
"""

from __future__ import annotations

from enum import StrEnum


class Category(StrEnum):
    IMAGE_PULL = "image_pull"
    BAD_COMMAND = "bad_command"
    OOM = "oom"
    PROBE_MISCONFIG = "probe_misconfig"
    SELECTOR_MISMATCH = "selector_mismatch"
    PORT_MISMATCH = "port_mismatch"
    INGRESS_BACKEND_TIMEOUT = "ingress_backend_timeout"
    TLS_SECRET = "tls_secret"  # noqa: S105 - a category name, not a credential
    NETWORK_POLICY = "network_policy"
    PVC_UNBOUND = "pvc_unbound"
    QUOTA_EXCEEDED = "quota_exceeded"
    CONFIG_MISSING = "config_missing"
    DNS = "dns"
    SCHEDULING_TAINT = "scheduling_taint"
    RBAC_FORBIDDEN = "rbac_forbidden"
    HPA_MISCONFIG = "hpa_misconfig"


# One-line definitions. They draw the boundaries between neighbouring categories
# (e.g. selector vs port mismatch), so a fault's label is never a judgement call.
DEFINITIONS: dict[Category, str] = {
    Category.IMAGE_PULL: "The container image can't be pulled (wrong name or tag, missing "
    "pull credentials, unreachable registry): ErrImagePull / ImagePullBackOff.",
    Category.BAD_COMMAND: "The container's command, args or entrypoint is wrong, so the "
    "process can't start or exits at once (missing executable or script, unknown flag).",
    Category.OOM: "A container exceeds its memory limit and is OOMKilled.",
    Category.PROBE_MISCONFIG: "A liveness, readiness or startup probe is misconfigured (path, "
    "port, timing) for an otherwise healthy app, so it restarts or never becomes Ready.",
    Category.SELECTOR_MISMATCH: "A Service's label selector matches none of the pods it "
    "should route to, so the Service has no endpoints.",
    Category.PORT_MISMATCH: "A Service's targetPort doesn't match the port the container "
    "listens on, so connections through the Service are refused.",
    Category.INGRESS_BACKEND_TIMEOUT: "The ingress proxy times out waiting for a slow or hung "
    "backend (HTTP 504).",
    Category.TLS_SECRET: "TLS termination fails because the referenced TLS Secret is "
    "missing, malformed or doesn't match the host.",
    Category.NETWORK_POLICY: "A NetworkPolicy blocks traffic the application needs.",
    Category.PVC_UNBOUND: "A PersistentVolumeClaim stays Pending (e.g. unknown "
    "StorageClass), so pods that mount it can't be scheduled.",
    Category.QUOTA_EXCEEDED: "Admission rejects pods because a ResourceQuota is exhausted "
    "or a LimitRange is violated.",
    Category.CONFIG_MISSING: "A ConfigMap, Secret or key that a pod references doesn't "
    "exist, so the container can't be created.",
    Category.DNS: "Name resolution fails because of DNS configuration (pod dnsPolicy or "
    "dnsConfig, CoreDNS).",
    Category.SCHEDULING_TAINT: "Pods stay Pending because nodes carry taints the pods "
    "don't tolerate.",
    Category.RBAC_FORBIDDEN: "A workload's ServiceAccount lacks an RBAC permission it "
    "needs, so its API calls get 403 Forbidden.",
    Category.HPA_MISCONFIG: "A HorizontalPodAutoscaler can't compute or apply a scale "
    "because of its own or its target's configuration (e.g. missing resource requests, "
    "wrong scaleTargetRef).",
}
