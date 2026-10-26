#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER="opstasks"
SERVICE="opstasks"

for command_name in awslocal docker curl; do
  command -v "${command_name}" >/dev/null || {
    echo "Required command not found: ${command_name}" >&2
    exit 1
  }
done

curl --fail --silent http://localhost.localstack.cloud:4566/_localstack/health >/dev/null || {
  echo "LocalStack is not running. Start it with: localstack start -d" >&2
  exit 1
}

create_repository() {
  local name="$1"
  awslocal ecr describe-repositories --repository-names "${name}" >/dev/null 2>&1 ||
    awslocal ecr create-repository --repository-name "${name}" >/dev/null
}

repository_uri() {
  local name="$1"
  awslocal ecr describe-repositories \
    --repository-names "${name}" \
    --query 'repositories[0].repositoryUri' \
    --output text
}

create_repository opstasks
app_image="$(repository_uri opstasks):latest"

docker build \
  -f "${ROOT_DIR}/infra/localstack/Dockerfile" \
  -t "${app_image}" \
  "${ROOT_DIR}"
docker push "${app_image}"

awslocal ecs describe-clusters --clusters "${CLUSTER}" \
  --query 'clusters[0].status' --output text 2>/dev/null | grep -q ACTIVE ||
  awslocal ecs create-cluster --cluster-name "${CLUSTER}" >/dev/null

task_file="$(mktemp)"
trap 'rm -f "${task_file}"' EXIT
sed \
  -e "s|__APP_IMAGE__|${app_image}|g" \
  "${ROOT_DIR}/infra/localstack/task-definition.json" >"${task_file}"

task_arn="$(awslocal ecs register-task-definition \
  --cli-input-json "file://${task_file}" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)"

service_status="$(awslocal ecs describe-services \
  --cluster "${CLUSTER}" \
  --services "${SERVICE}" \
  --query 'services[0].status' \
  --output text 2>/dev/null || true)"

if [[ "${service_status}" == "ACTIVE" ]]; then
  awslocal ecs update-service \
    --cluster "${CLUSTER}" \
    --service "${SERVICE}" \
    --desired-count 0 >/dev/null
  awslocal ecs wait services-stable --cluster "${CLUSTER}" --services "${SERVICE}"
  awslocal ecs update-service \
    --cluster "${CLUSTER}" \
    --service "${SERVICE}" \
    --task-definition "${task_arn}" \
    --desired-count 1 >/dev/null
else
  awslocal ecs create-service \
    --cluster "${CLUSTER}" \
    --service-name "${SERVICE}" \
    --task-definition "${task_arn}" \
    --desired-count 1 >/dev/null
fi

awslocal ecs wait services-stable --cluster "${CLUSTER}" --services "${SERVICE}"
echo "LocalStack ECS is ready:"
echo "  UI:  http://localhost:8000"
echo "  API: http://localhost:8000/docs"
