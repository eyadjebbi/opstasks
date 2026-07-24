#!/usr/bin/env bash

set -euo pipefail

CLUSTER="opstasks"
SERVICE="opstasks"

awslocal ecs describe-services \
  --cluster "${CLUSTER}" \
  --services "${SERVICE}" \
  --query 'services[0].{Status:status,Desired:desiredCount,Running:runningCount,Pending:pendingCount,TaskDefinition:taskDefinition}' \
  --output table

task_arns="$(awslocal ecs list-tasks \
  --cluster "${CLUSTER}" \
  --service-name "${SERVICE}" \
  --query 'taskArns' \
  --output text)"

if [[ -n "${task_arns}" && "${task_arns}" != "None" ]]; then
  awslocal ecs describe-tasks \
    --cluster "${CLUSTER}" \
    --tasks ${task_arns} \
    --query 'tasks[].{Task:taskArn,Last:lastStatus,Desired:desiredStatus,Health:healthStatus,StoppedReason:stoppedReason}' \
    --output table
else
  echo "No running ECS tasks."
fi

awslocal ecr describe-repositories \
  --repository-names opstasks \
  --query 'repositories[].{Repository:repositoryName,URI:repositoryUri}' \
  --output table
