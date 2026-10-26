#!/usr/bin/env bash

set -euo pipefail

NAMESPACE="demo-app"

kubectl scale statefulset/postgres -n "${NAMESPACE}" --replicas=1
kubectl rollout status statefulset/postgres -n "${NAMESPACE}" --timeout=180s
kubectl delete deployment failing-worker -n "${NAMESPACE}" --ignore-not-found
kubectl rollout restart deployment/backend -n "${NAMESPACE}"
kubectl rollout status deployment/backend -n "${NAMESPACE}" --timeout=180s

echo "Recovered. PostgreSQL data was preserved."
