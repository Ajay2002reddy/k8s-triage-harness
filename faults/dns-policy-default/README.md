# dns-policy-default
**Breaks:** the `worker` sets `dnsPolicy: Default`, so it uses the node's resolver, which can't resolve `api.orders.svc.cluster.local`.
**Realistic because:** `Default` sounds like the default but isn't (`ClusterFirst` is); it's often copied from host-network DaemonSets.
**A human checks first:** the worker's "bad address" errors while the Service is healthy, then the pod's `dnsPolicy` and `/etc/resolv.conf`.
