#!/usr/bin/env bash

set -euo pipefail

CLUSTER="opstasks"
SERVICE="opstasks"

curl --fail --silent -X POST \
  http://localhost:8000/api/demo/faults/clear >/dev/null 2>&1 || true

awslocal ecs update-service \
  --cluster "${CLUSTER}" \
  --service "${SERVICE}" \
  --desired-count 0 >/dev/null
awslocal ecs wait services-stable --cluster "${CLUSTER}" --services "${SERVICE}"
awslocal ecs update-service \
  --cluster "${CLUSTER}" \
  --service "${SERVICE}" \
  --desired-count 1 >/dev/null
awslocal ecs wait services-stable --cluster "${CLUSTER}" --services "${SERVICE}"

echo "LocalStack ECS recovered."
