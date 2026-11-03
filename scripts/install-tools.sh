#!/usr/bin/env bash
# Install the pinned kind, kubectl, kubeconform and actionlint (linux-amd64) into BIN_DIR,
# verifying each download against the sha256 in cluster/versions.env.
# CI runs this; on a laptop it's optional if you already have matching versions.
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../cluster/versions.env
source "$REPO_ROOT/cluster/versions.env"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

if [[ "$(uname -s)-$(uname -m)" != "Linux-x86_64" ]]; then
  echo "install-tools: only linux-amd64 checksums are pinned; install the versions in cluster/versions.env yourself" >&2
  exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$BIN_DIR"

# fetch URL SHA256 FILE: download and verify, or fail.
fetch() {
  curl -fsSL --retry 3 -o "$tmp/$3" "$1"
  echo "$2  $tmp/$3" | sha256sum --check --quiet
}

fetch "https://github.com/kubernetes-sigs/kind/releases/download/$KIND_VERSION/kind-linux-amd64" \
  "$KIND_SHA256" kind
install -m 0755 "$tmp/kind" "$BIN_DIR/kind"

fetch "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/amd64/kubectl" "$KUBECTL_SHA256" kubectl
install -m 0755 "$tmp/kubectl" "$BIN_DIR/kubectl"

fetch "https://github.com/yannh/kubeconform/releases/download/$KUBECONFORM_VERSION/kubeconform-linux-amd64.tar.gz" \
  "$KUBECONFORM_SHA256" kubeconform.tar.gz
tar -xzf "$tmp/kubeconform.tar.gz" -C "$tmp" kubeconform
install -m 0755 "$tmp/kubeconform" "$BIN_DIR/kubeconform"

fetch "https://github.com/rhysd/actionlint/releases/download/v$ACTIONLINT_VERSION/actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz" \
  "$ACTIONLINT_SHA256" actionlint.tar.gz
tar -xzf "$tmp/actionlint.tar.gz" -C "$tmp" actionlint
install -m 0755 "$tmp/actionlint" "$BIN_DIR/actionlint"

echo "install-tools: installed kind $KIND_VERSION, kubectl $KUBECTL_VERSION, kubeconform $KUBECONFORM_VERSION, actionlint $ACTIONLINT_VERSION into $BIN_DIR"
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo "install-tools: add $BIN_DIR to PATH" >&2 ;;
esac
