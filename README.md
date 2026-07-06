# OpsTasks fault playground

OpsTasks is a small task manager and Kubernetes failure lab. The application is
deliberately ordinary; the interesting part is placing it into known broken
states so a human or future AI operations agent can inspect the evidence and
recover it.

The lab supports five scenarios:

| Fault | Visible symptom |
| --- | --- |
| `degraded` | Backend readiness returns 503 and the Pod becomes `0/1` |
| `errors` | Every task operation returns HTTP 500 |
| `slow` | Every task operation takes about three seconds |
| `database` | PostgreSQL is scaled to zero Pods |
| `crashloop` | A separate worker enters `CrashLoopBackOff` |

## Sixty-second tour

```text
Browser
  -> React files served by Nginx
  -> /api and /health proxied by Nginx
  -> FastAPI backend
  -> PostgreSQL
  -> persistent volume
```

- `frontend/` is the task UI and its Nginx reverse proxy.
- `backend/` is the FastAPI API, database model, validation, faults, and tests.
- `infra/k8s/` contains one healthy application manifest and one intentionally
  failing worker.
- `scripts/` contains the four operator actions: deploy, fault, status, recover.
- `compose.yaml` runs the normal application locally without Kubernetes.

A normal task request enters through Nginx, is validated by Pydantic, handled by
a FastAPI route, and persisted through SQLAlchemy to PostgreSQL. In Kubernetes,
health probes and workload state make failures visible to the operator.

## Repository map

```text
opstasks/
  backend/
    app/
      main.py          FastAPI startup and health endpoints
      routes.py        Task CRUD and application fault modes
      database.py      PostgreSQL engine and request sessions
      models.py        SQLAlchemy tasks table
      schemas.py       API validation and response shapes
    tests/             Focused backend tests
    Dockerfile
  frontend/
    src/               React application and component tests
    nginx.conf         Static files plus /api and /health proxy
    Dockerfile
  infra/k8s/
    app.yaml           Healthy frontend, backend, PostgreSQL, Services, and PVC
    failing-worker.yaml  Optional CrashLoop scenario
  infra/localstack/
    Dockerfile          Combined React and FastAPI image for local ECS
    task-definition.json  LocalStack ECS task with embedded SQLite storage
  scripts/
    deploy.sh          Build and deploy a healthy Minikube baseline
    fault.sh           Inject one of five faults
    status.sh          Show workloads, storage, Services, and recent events
    recover.sh         Recover every supported fault without deleting data
    localstack-*.sh    Deploy and test the optional ECR + ECS runtime
  compose.yaml         Local Docker stack
```

## Requirements

For local Docker development:

- Docker with Docker Compose

For backend or frontend tests:

- Python 3.12
- Node.js 22 and npm

For the Kubernetes lab:

- Docker
- Minikube
- kubectl

For the optional local AWS runtime:

- LocalStack CLI
- `awslocal`
- Docker
- curl

## Run the normal application with Docker

Create local demo configuration once:

```bash
cp .env.example .env
```

Start PostgreSQL, the API, and the UI:

```bash
docker compose up --build
```

Open:

- UI: <http://localhost:3001>
- API documentation: <http://localhost:8000/docs>
- Liveness: <http://localhost:8000/health/live>
- Readiness: <http://localhost:8000/health/ready>

Stop the stack while preserving database data:

```bash
docker compose down
```

Use `docker compose down -v` only when you intentionally want to delete the
local PostgreSQL volume and all tasks.

The `scripts/fault.sh` commands target Kubernetes, not Compose. For a quick
Compose-only application fault, call the controller directly and clear it when
finished:

```bash
curl -X POST http://localhost:8000/api/demo/faults/slow
curl http://localhost:8000/api/tasks
curl -X POST http://localhost:8000/api/demo/faults/clear
```

## Verify the healthy API

With Compose running, these commands exercise the full CRUD flow.

Check health:

```bash
curl -i http://localhost:8000/health/live
curl -i http://localhost:8000/health/ready
```

Create and list a task:

```bash
curl -i -X POST http://localhost:8000/api/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"Inspect cluster","description":"Review current Pod state"}'

curl -i http://localhost:8000/api/tasks
```

Update or delete the returned task ID:

```bash
curl -i -X PATCH http://localhost:8000/api/tasks/1 \
  -H 'Content-Type: application/json' \
  -d '{"status":"done"}'

curl -i -X DELETE http://localhost:8000/api/tasks/1
```

Valid task states are `todo`, `in_progress`, and `done`.

## Run the Kubernetes lab

Deploy a healthy baseline:

```bash
./scripts/deploy.sh
```

The script starts Minikube when necessary, builds both application images inside
Minikube, applies the manifest, removes a leftover failing worker, restarts the
application Pods to use freshly built images, and waits for readiness.

Open the UI:

```bash
minikube service frontend -n demo-app
```

Inspect the initial state:

```bash
./scripts/status.sh
```

The healthy baseline should contain one ready PostgreSQL Pod, one ready backend
Pod, one ready frontend Pod, no failing-worker Pod, and a bound
`postgres-pvc`.

### Access the backend directly

Keep this running in a second terminal:

```bash
kubectl port-forward -n demo-app deployment/backend 8000:8000
```

You can then use the same localhost health and API commands shown above. A
backend restart ends the port-forward; start it again after recovery.

## Fault experiment loop

Use one fault at a time:

```bash
./scripts/fault.sh MODE
./scripts/status.sh
# Inspect the evidence.
./scripts/recover.sh
./scripts/status.sh
```

Recovery scales PostgreSQL back to one, removes the failing worker, restarts the
backend to clear in-memory faults, and leaves `postgres-pvc` untouched.

### Degraded readiness

Inject and observe:

```bash
./scripts/fault.sh degraded
curl -i http://localhost:8000/health/live
curl -i http://localhost:8000/health/ready
./scripts/status.sh
```

Expected evidence:

- Liveness remains HTTP 200.
- Readiness becomes HTTP 503.
- The backend process remains `Running`, but its ready count becomes `0/1`.
- Kubernetes removes the backend from normal Service traffic.

### Controlled API errors

Inject and observe:

```bash
./scripts/recover.sh
./scripts/fault.sh errors
curl -i http://localhost:8000/api/tasks
kubectl logs -n demo-app deployment/backend
```

Expected evidence: task operations return HTTP 500 while both health endpoints
remain healthy.

### Slow requests

Inject and observe:

```bash
./scripts/recover.sh
./scripts/fault.sh slow
time curl http://localhost:8000/api/tasks
kubectl logs -n demo-app deployment/backend
```

Expected evidence: the request takes about three seconds and the backend logs an
injected delay.

### Database outage

Inject and observe:

```bash
./scripts/recover.sh
./scripts/fault.sh database
./scripts/status.sh
curl -i http://localhost:8000/health/ready
```

Expected evidence:

- The PostgreSQL StatefulSet has zero desired Pods.
- `postgres-pvc` remains bound.
- Backend readiness becomes HTTP 503.
- Task operations cannot use the database.

Scaling is asynchronous, so allow a few seconds for the PostgreSQL Pod to
disappear.

### CrashLoopBackOff

Inject and observe:

```bash
./scripts/recover.sh
./scripts/fault.sh crashloop
./scripts/status.sh
kubectl logs -n demo-app deployment/failing-worker
```

Expected evidence: a separate `failing-worker` repeatedly exits and reaches
`CrashLoopBackOff`. The main application remains healthy, making this a clean
workload-diagnosis exercise.

### Final recovery check

```bash
./scripts/recover.sh
./scripts/status.sh
curl -i http://localhost:8000/health/ready
```

Expected: readiness is HTTP 200, PostgreSQL and backend are ready, and no
failing-worker Deployment remains.

## Optional LocalStack ECR + ECS runtime

This is an alternative to Minikube, not a dependency of the Kubernetes lab.
LocalStack ECR stores one ECS-specific application image. That image serves the
built React UI and FastAPI from one process and uses an embedded SQLite file.
The ordinary Compose and Kubernetes paths continue to use PostgreSQL.

```text
Docker build -> LocalStack ECR -> LocalStack ECS task
                                    ├── FastAPI API
                                    ├── React static files
                                    └── SQLite file
```

Start LocalStack. Depending on your LocalStack installation and plan, configure
its authentication token before starting it:

```bash
localstack start -d
```

Build, push, register, and run the application:

```bash
./scripts/localstack-deploy.sh
```

The script creates the `opstasks` ECR repository, pushes the combined image,
creates the `opstasks` ECS cluster, registers a new task-definition revision,
and creates or updates the ECS service.

Open:

- UI: <http://localhost:8000>
- API: <http://localhost:8000/docs>

Inspect ECS and ECR state:

```bash
./scripts/localstack-status.sh
awslocal ecs list-tasks --cluster opstasks
awslocal ecr list-images --repository-name opstasks
```

### LocalStack faults

```bash
./scripts/localstack-fault.sh degraded
./scripts/localstack-fault.sh errors
./scripts/localstack-fault.sh slow
./scripts/localstack-fault.sh task-stop
./scripts/localstack-fault.sh service-down
```

| Mode | ECS behavior |
| --- | --- |
| `degraded` | Backend readiness returns HTTP 503 |
| `errors` | Task API returns HTTP 500 |
| `slow` | Task API waits about three seconds |
| `task-stop` | Calls ECS `StopTask`; the service should start a replacement |
| `service-down` | Sets the ECS service desired count to zero |

Recover any supported LocalStack fault:

```bash
./scripts/localstack-recover.sh
./scripts/localstack-status.sh
```

Recovery clears the application fault and recreates one healthy ECS task. The
SQLite database uses `/tmp/opstasks-localstack-data` on the Docker host for
local persistence.

The ECS path intentionally does not pretend to provide Kubernetes semantics:

- It has ECS tasks and services, not Pods, readiness routing, or StatefulSets.
- `CrashLoopBackOff` remains a Kubernetes-only scenario.
- PostgreSQL replica scaling and PVC inspection remain Kubernetes-only.
- SQLite is used only to keep the optional local ECS task self-contained.
- LocalStack service fidelity and availability depend on your installed plan.

Use Minikube when testing Kubernetes diagnosis. Use LocalStack ECS when testing
AWS CLI, ECR, ECS task, and ECS service diagnosis.

## Useful diagnostic commands

```bash
# Overview and recent events
./scripts/status.sh

# Application logs
kubectl logs -n demo-app deployment/backend
kubectl logs -n demo-app deployment/frontend
kubectl logs -n demo-app statefulset/postgres

# CrashLoop evidence
kubectl logs -n demo-app deployment/failing-worker

# Detailed Pod state, probes, restarts, and events
kubectl describe pod -n demo-app POD_NAME

# Check which ready Pods back each Service
kubectl get endpoints -n demo-app backend postgres

# Watch state change live
kubectl get pods -n demo-app -w
```

## Tests and static checks

Backend setup and checks:

```bash
cd backend
python3 -m venv venv
venv/bin/pip install -r requirements-dev.txt
venv/bin/python -m pytest
venv/bin/ruff check app tests
venv/bin/ruff format --check app tests
```

Frontend checks:

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
```

Basic configuration checks from the repository root:

```bash
docker compose config
bash -n scripts/*.sh
kubectl apply --dry-run=client -f infra/k8s/app.yaml
kubectl apply --dry-run=client -f infra/k8s/failing-worker.yaml
```

## Configuration

Compose reads `.env`:

| Variable | Example | Purpose |
| --- | --- | --- |
| `DATABASE_NAME` | `opstasks` | PostgreSQL database |
| `DATABASE_USER` | `opstasks` | Local database user |
| `DATABASE_PASSWORD` | `opstasks` | Local database password |

Kubernetes uses the same visible demo credentials directly in `app.yaml`.
Application faults are enabled only by the Compose and Kubernetes environment.
The backend default is disabled.

These credentials are intentionally convenient for a local lab. Never reuse
them in a shared or production environment.

## Persistence and cleanup

- `docker compose down` preserves Compose task data.
- `docker compose down -v` deletes Compose task data.
- Backend Pod replacement preserves Kubernetes task data.
- PostgreSQL Pod replacement preserves Kubernetes task data.
- `scripts/recover.sh` preserves Kubernetes task data.
- Deleting `postgres-pvc` or the `demo-app` namespace deletes Kubernetes task
  data.

Stop Minikube without deleting its workloads or data:

```bash
minikube stop
```

Delete the entire lab, including its Kubernetes task data, only when intended:

```bash
kubectl delete namespace demo-app
```

## Troubleshooting

### Compose says `.env` variables are missing

```bash
cp .env.example .env
docker compose up --build
```

### Backend rollout does not become ready

```bash
kubectl get pods -n demo-app
kubectl logs -n demo-app statefulset/postgres
kubectl logs -n demo-app deployment/backend
kubectl describe pod -n demo-app POD_NAME
```

The backend creates its fixed table during startup, so PostgreSQL must be
reachable before FastAPI can become ready.

### UI opens but API requests fail

```bash
kubectl get pods -n demo-app
kubectl get endpoints -n demo-app backend
kubectl logs -n demo-app deployment/frontend
kubectl logs -n demo-app deployment/backend
```

If a degraded or database fault is still active, run `./scripts/recover.sh`.

### Code changes do not appear in Minikube

Run `./scripts/deploy.sh` again. It rebuilds the images inside Minikube and
restarts the frontend and backend Deployments.

### Port-forward disconnects

Backend recovery replaces the Pod, which ends the connection. Start it again:

```bash
kubectl port-forward -n demo-app deployment/backend 8000:8000
```

## Deliberate limitations

This is a local learning lab, not a production deployment template:

- The fixed database schema is created automatically; there is no migration
  framework.
- Fault state exists in one backend process and resets on restart.
- The Kubernetes Secret contains visible demo credentials.
- Images use local mutable tags and `imagePullPolicy: Never`.
- Resource limits, TLS, network policies, high availability, and production
  secret management are intentionally omitted.
- There is no metrics stack; diagnosis uses HTTP behavior, Pods, events, and
  logs.

The omissions keep the incident mechanics visible and the repository small.
