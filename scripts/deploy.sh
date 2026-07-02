#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="demo-app"

command -v minikube >/dev/null || { echo "Minikube is required." >&2; exit 1; }
command -v kubectl >/dev/null || { echo "kubectl is required." >&2; exit 1; }

minikube status >/dev/null 2>&1 || minikube start
minikube image build -t opstasks-backend:1.0.0 "${ROOT_DIR}/backend"
minikube image build -t opstasks-frontend:1.0.0 "${ROOT_DIR}/frontend"

kubectl apply -f "${ROOT_DIR}/infra/k8s/app.yaml"
kubectl delete deployment failing-worker -n "${NAMESPACE}" --ignore-not-found
kubectl rollout restart deployment/backend deployment/frontend -n "${NAMESPACE}"
kubectl rollout status statefulset/postgres -n "${NAMESPACE}" --timeout=180s
kubectl rollout status deployment/backend -n "${NAMESPACE}" --timeout=180s
kubectl rollout status deployment/frontend -n "${NAMESPACE}" --timeout=180s

echo "Cluster ready. Open the UI with:"
echo "minikube service frontend -n ${NAMESPACE}"
