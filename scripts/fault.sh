#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="demo-app"
MODE="${1:-}"

case "${MODE}" in
  degraded|errors|slow)
    kubectl exec -n "${NAMESPACE}" deployment/backend -- \
      python -c 'import sys, urllib.request; urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8000/api/demo/faults/" + sys.argv[1], method="POST"))' \
      "${MODE}"
    ;;
  database)
    kubectl scale statefulset/postgres -n "${NAMESPACE}" --replicas=0
    ;;
  crashloop)
    kubectl apply -f "${ROOT_DIR}/infra/k8s/failing-worker.yaml"
    ;;
  *)
    echo "Usage: $0 {degraded|errors|slow|database|crashloop}" >&2
    exit 2
    ;;
esac

echo "Fault active: ${MODE}"
