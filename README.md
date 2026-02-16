# Kubernetes Sharding Demo – Node.js + PostgreSQL

A minimal project to learn Kubernetes concepts using a real-world pattern:
**database sharding** (splitting data across multiple database instances).

---

## What You Will Learn

| Concept | Where it appears |
|---|---|
| **Namespace** | Isolates all demo resources (`sharding-demo`) |
| **Deployment** | Keeps pods running; restarts them on failure |
| **Service (ClusterIP)** | Stable DNS name for internal pod-to-pod communication |
| **Service (NodePort)** | Exposes the app on `localhost:30000` |
| **Secret** | Stores the Postgres password securely |
| **PersistentVolumeClaim** | Requests disk storage so database data survives restarts |
| **Readiness/Liveness probes** | Tells Kubernetes when a pod is healthy |
| **imagePullPolicy: Never** | Uses a locally-built image (no registry needed) |

---

## Architecture

```
Your browser / curl
        │
        ▼  localhost:30000  (NodePort)
┌───────────────────┐
│  sharding-app     │  Node.js Express API
│  (Deployment)     │  – decides which shard to use
└────────┬──────────┘
         │  Kubernetes DNS (ClusterIP Services)
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│shard-0 │ │shard-1 │  PostgreSQL 15
│(even   │ │(odd    │  each backed by a
│ IDs)   │ │ IDs)   │  PersistentVolumeClaim
└────────┘ └────────┘
```

### Sharding logic (in `app/index.js`)

```
shard_index = user_id % 2

user_id 0, 2, 4, 6 … → shard-0  (postgres-shard-0)
user_id 1, 3, 5, 7 … → shard-1  (postgres-shard-1)
```

The app uses the **Kubernetes Service name** (`postgres-shard-0`, `postgres-shard-1`)
as the hostname. Kubernetes DNS resolves those names automatically.

---

## Prerequisites

1. **Docker Desktop** with **Kubernetes enabled**
   - Open Docker Desktop → Settings → Kubernetes → ☑ Enable Kubernetes → Apply
   - Wait for the green "Kubernetes is running" indicator
2. **kubectl** – comes bundled with Docker Desktop
3. **make** (optional but handy) – available on macOS/Linux; on Windows use Git Bash or WSL

Verify everything works:

```bash
kubectl version --short
kubectl get nodes          # should show "docker-desktop" node as Ready
```

---

## Quick Start

### Step 1 – Build the Docker image

```bash
docker build -t k8s-sharding-demo:latest ./app
```

Docker Desktop's Kubernetes uses the **same Docker daemon**, so this image is
immediately available to the cluster — no registry needed.

### Step 2 – Deploy to Kubernetes

```bash
kubectl apply -f k8s/
```

This applies the six YAML files in order (namespace → secret → shards → app).

### Step 3 – Wait for pods to be ready

```bash
kubectl get pods -n sharding-demo -w
```

You should see three pods eventually reach `Running` / `1/1 Ready`:

```
NAME                              READY   STATUS    RESTARTS
postgres-shard-0-xxx              1/1     Running   0
postgres-shard-1-xxx              1/1     Running   0
sharding-app-xxx                  1/1     Running   0
```

Press **Ctrl+C** to stop watching.

### Step 4 – Test the API

```bash
# What shards exist?
curl http://localhost:30000/shards

# Create a user with id=2 → even → goes to shard-0
curl -X POST http://localhost:30000/users \
  -H "Content-Type: application/json" \
  -d '{"id":2,"name":"Alice","email":"alice@example.com"}'

# Create a user with id=3 → odd → goes to shard-1
curl -X POST http://localhost:30000/users \
  -H "Content-Type: application/json" \
  -d '{"id":3,"name":"Bob","email":"bob@example.com"}'

# Fetch user 2 (app knows to query shard-0)
curl http://localhost:30000/users/2

# Fetch user 3 (app knows to query shard-1)
curl http://localhost:30000/users/3

# List ALL users — the app fans out to both shards and merges the result
curl http://localhost:30000/users
```

---

## Makefile shortcuts

```bash
make deploy        # build image + kubectl apply + wait for pods
make status        # kubectl get pods,services,pvc -n sharding-demo
make logs          # stream app logs
make test          # automated curl smoke-test
make port-forward  # alternative: kubectl port-forward to localhost:3000
make clean         # delete everything (kubectl delete namespace sharding-demo)
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (used by Kubernetes probes) |
| GET | `/shards` | Show shard topology |
| POST | `/users` | Create user `{ id, name, email }` |
| GET | `/users/:id` | Get user by ID |
| GET | `/users` | List all users (queries all shards) |
| DELETE | `/users/:id` | Delete user |

Every response includes a `routing` field showing **which shard was used and why**.

---

## File Structure

```
.
├── app/
│   ├── index.js          ← Express API + sharding logic
│   ├── package.json
│   └── Dockerfile
└── k8s/
    ├── 00-namespace.yaml          ← Namespace
    ├── 01-postgres-secret.yaml    ← Secret (password)
    ├── 02-postgres-shard-0.yaml   ← PVC + Deployment + Service (shard 0)
    ├── 03-postgres-shard-1.yaml   ← PVC + Deployment + Service (shard 1)
    ├── 04-app-deployment.yaml     ← Node.js app Deployment
    └── 05-app-service.yaml        ← NodePort Service (localhost:30000)
```

---

## Useful kubectl Commands

```bash
# See everything in the namespace
kubectl get all -n sharding-demo

# Describe a pod (events, env vars, probes)
kubectl describe pod -n sharding-demo <pod-name>

# See logs from a specific pod
kubectl logs -n sharding-demo <pod-name>

# Open a shell inside a pod
kubectl exec -it -n sharding-demo <pod-name> -- sh

# Connect to PostgreSQL in shard-0 directly
kubectl exec -it -n sharding-demo deployment/postgres-shard-0 -- \
  psql -U postgres -d sharddb

# Inside psql: see which users are on this shard
# SELECT * FROM users;
```

---

## Clean Up

```bash
# Remove everything created by this demo
kubectl delete namespace sharding-demo

# Or with make
make clean
```

---

## Going Further

- **StatefulSets** – the production-grade way to run databases in Kubernetes
  (ordered startup, stable network IDs, per-pod PVCs)
- **ConfigMap** – like a Secret but for non-sensitive configuration
- **Horizontal Pod Autoscaler** – automatically scale the app pods under load
- **Ingress** – route external HTTP traffic to services by hostname/path
- **Helm** – package manager for Kubernetes that templatises YAML files
