#!/usr/bin/env bash

set -euo pipefail

CLUSTER="opstasks"
SERVICE="opstasks"
MODE="${1:-}"

case "${MODE}" in
  degraded|errors|slow)
    curl --fail --silent --show-error \
      -X POST "http://localhost:8000/api/demo/faults/${MODE}"
    echo
    ;;
  task-stop)
    task_arn="$(awslocal ecs list-tasks \
      --cluster "${CLUSTER}" \
      --service-name "${SERVICE}" \
      --query 'taskArns[0]' \
      --output text)"
    [[ "${task_arn}" != "None" ]] || { echo "No running ECS task found." >&2; exit 1; }
    awslocal ecs stop-task \
      --cluster "${CLUSTER}" \
      --task "${task_arn}" \
      --reason "Injected task failure" >/dev/null
    ;;
  service-down)
    awslocal ecs update-service \
      --cluster "${CLUSTER}" \
      --service "${SERVICE}" \
      --desired-count 0 >/dev/null
    ;;
  *)
    echo "Usage: $0 {degraded|errors|slow|task-stop|service-down}" >&2
    exit 2
    ;;
esac

echo "LocalStack fault active: ${MODE}"
