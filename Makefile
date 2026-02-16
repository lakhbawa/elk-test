# ─────────────────────────────────────────────────────────────────────────────
# Makefile – convenience commands for the Kubernetes sharding demo
# Usage: make <target>
# ─────────────────────────────────────────────────────────────────────────────

IMAGE   = k8s-sharding-demo
TAG     = latest
NS      = sharding-demo
API_URL = http://localhost:30000

.PHONY: help build deploy status logs clean test port-forward

## Show this help
help:
	@echo ""
	@echo "  make build         Build the Docker image"
	@echo "  make deploy        Build image + apply all Kubernetes manifests"
	@echo "  make status        Show all pods, services, PVCs in the namespace"
	@echo "  make logs          Stream logs from the app pod"
	@echo "  make test          Run sample API calls (requires curl)"
	@echo "  make port-forward  Alternative access via kubectl port-forward"
	@echo "  make clean         Delete the entire namespace (removes everything)"
	@echo ""

## Build the Docker image (uses Docker Desktop's local daemon)
build:
	docker build -t $(IMAGE):$(TAG) ./app

## Apply all manifests in order (00 → 05)
apply:
	kubectl apply -f k8s/

## Build + deploy everything
deploy: build apply
	@echo ""
	@echo "Deployed!  Waiting for pods to become ready…"
	kubectl wait --namespace=$(NS) \
	  --for=condition=ready pod \
	  --selector=app=postgres \
	  --timeout=120s
	kubectl wait --namespace=$(NS) \
	  --for=condition=ready pod \
	  --selector=app=sharding-app \
	  --timeout=120s
	@echo ""
	@echo "All pods ready.  API available at $(API_URL)"

## Show current state of the namespace
status:
	kubectl get pods,services,pvc -n $(NS)

## Stream app logs
logs:
	kubectl logs -n $(NS) deployment/sharding-app -f

## kubectl port-forward as an alternative to NodePort
port-forward:
	@echo "Forwarding localhost:3000 → sharding-app pod…  (Ctrl+C to stop)"
	kubectl port-forward -n $(NS) service/sharding-app 3000:3000

## Run a quick smoke test against the API
test:
	@echo "=== Shard topology ==="
	curl -s $(API_URL)/shards | python3 -m json.tool || curl -s $(API_URL)/shards
	@echo ""
	@echo "=== Create user id=2 (even → shard-0) ==="
	curl -s -X POST $(API_URL)/users \
	  -H "Content-Type: application/json" \
	  -d '{"id":2,"name":"Alice","email":"alice@example.com"}' | python3 -m json.tool || true
	@echo ""
	@echo "=== Create user id=3 (odd  → shard-1) ==="
	curl -s -X POST $(API_URL)/users \
	  -H "Content-Type: application/json" \
	  -d '{"id":3,"name":"Bob","email":"bob@example.com"}' | python3 -m json.tool || true
	@echo ""
	@echo "=== Get user 2 (should come from shard-0) ==="
	curl -s $(API_URL)/users/2 | python3 -m json.tool || true
	@echo ""
	@echo "=== Get user 3 (should come from shard-1) ==="
	curl -s $(API_URL)/users/3 | python3 -m json.tool || true
	@echo ""
	@echo "=== List all users (fan-out across both shards) ==="
	curl -s $(API_URL)/users | python3 -m json.tool || true

## Delete the namespace and everything inside it
clean:
	kubectl delete namespace $(NS) --ignore-not-found
	@echo "Namespace $(NS) deleted."
