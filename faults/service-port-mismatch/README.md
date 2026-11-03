# service-port-mismatch
**Breaks:** Service `api` sends traffic to `targetPort: 8080`; nginx listens on 80. Endpoints exist, but every connection is refused.
**Realistic because:** a chart default (8080) that doesn't match the image's real port is a frequent "Service is up but refuses connections" incident.
**A human checks first:** the client's error (refused, not timeout), then the Service `targetPort` against the container's port.
