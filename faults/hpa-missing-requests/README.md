# hpa-missing-requests
**Breaks:** HPA `api` targets 70% CPU utilization, but the `api` container has no CPU request, so utilization is undefined and the HPA never scales.
**Realistic because:** HPAs get added to Deployments that never set requests; everything looks Running and the autoscaler quietly does nothing.
**A human checks first:** `describe hpa` (ScalingActive False, "missing request for cpu"), then the container's resources.
**Needs:** metrics-server (`make addons NAME=hpa-missing-requests`); without it the HPA fails earlier, for a different reason.
