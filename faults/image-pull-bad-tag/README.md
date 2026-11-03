# image-pull-bad-tag
**Breaks:** the `web` Deployment references an image tag with a typo (`1.30.2-alpne`), so no pod ever starts.
**Realistic because:** a hand-edited or templated tag is the most common cause of ImagePullBackOff after a deploy.
**A human checks first:** `get pods` (ImagePullBackOff), then the pod's events for the exact pull error.
