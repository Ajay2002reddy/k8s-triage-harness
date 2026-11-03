# networkpolicy-blocks-client
**Breaks:** NetworkPolicy `api-ingress` admits only `app: web`; the real client is `app: frontend`, so its requests time out.
**Realistic because:** policies written against an old or assumed client label silently drop traffic; the Service and endpoints all look healthy.
**A human checks first:** the client error (timeout, not refused) with healthy endpoints, then `get networkpolicy` and compare its `from` selector with the client's labels.
**Needs:** a CNI that enforces NetworkPolicy. kind's default kindnet does (it watches NetworkPolicies).
