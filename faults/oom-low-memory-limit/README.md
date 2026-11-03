# oom-low-memory-limit
**Breaks:** the `worker` loads ~256 MiB into memory under a 64Mi limit and is OOM-killed on every start.
**Realistic because:** limits copied from a small service onto a batch job are a classic OOMKilled cause.
**A human checks first:** `describe pod` (Last State: OOMKilled, exit 137), then compare the limit with what the job does.
