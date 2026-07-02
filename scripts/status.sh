#!/usr/bin/env bash

set -euo pipefail

kubectl get pods,deployments,statefulsets,services,pvc -n demo-app
echo
kubectl get events -n demo-app --sort-by=.lastTimestamp | tail -n 12
