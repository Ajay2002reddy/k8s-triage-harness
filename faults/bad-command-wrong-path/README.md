# bad-command-wrong-path
**Breaks:** the `worker` container's command points at `/app/worker.py`, but the script is mounted at `/opt/worker`.
**Realistic because:** command and mount path drift apart when someone changes one of them in a refactor; the process exits immediately and crash-loops.
**A human checks first:** the crash-looping pod's logs (`--previous`), then compare the command with the volume mounts.
