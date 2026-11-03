# probe-wrong-path
**Breaks:** the liveness probe hits `/healthz`, which this nginx answers with 404, so a healthy container is restarted over and over.
**Realistic because:** probe blocks get copied between services whose health endpoints differ.
**A human checks first:** restart count and `Unhealthy` events (`Liveness probe failed ... 404`), then the probe spec.
