# OCO Backend Operations

## Deploy

```bash
task backend:up
```

Equivalent command:

```bash
kubectl apply -k k8s/backend
```

Wait for the components:

```bash
kubectl -n observability-backend rollout status deploy/alloy
kubectl -n observability-backend rollout status deploy/victoriametrics
kubectl -n observability-backend rollout status deploy/victorialogs
kubectl -n observability-backend rollout status deploy/tempo
```

## Tempo MinIO cutover

Create a dedicated `observability-tempo` bucket and dedicated credentials in
host-runtime MinIO.

Create the Secret from local values; do not commit credentials:

```bash
kubectl -n observability-backend create secret generic tempo-minio \
  --from-literal=access-key="$TEMPO_S3_ACCESS_KEY" \
  --from-literal=secret-key="$TEMPO_S3_SECRET_KEY"
```

Then apply:

```bash
kubectl apply -k k8s/backend/overlays/tempo-minio
```

`secret.example.yml` documents only the Secret schema.

## Static validation

Before deployment, render and validate repository manifests:

```bash
task ci:validate
```

Static validation checks repository policy, Kustomize rendering, Kubernetes
schemas, and OCO-specific topology invariants. It does not establish runtime
health.

## Runtime validation

A backend is not healthy merely because its Pods are `Running`.

Run:

```bash
task backend:smoke
task backend:baseline
```

The smoke test sends OTLP metrics, logs, and traces to Alloy and queries the
corresponding backend.

Then test restart persistence independently:

```bash
kubectl -n observability-backend rollout restart deploy/alloy
kubectl -n observability-backend rollout restart deploy/victoriametrics
kubectl -n observability-backend rollout restart deploy/victorialogs
kubectl -n observability-backend rollout restart deploy/tempo
kubectl -n observability-console rollout restart deploy/grafana
```

After each restart, rerun `task backend:smoke`.

The baseline records:

- Pod CPU and memory when Metrics Server is available;
- PVC state;
- filesystem usage;
- representative backend ingestion/query counters.

Use that result as the pre-migration baseline for comparing the cost removed
when project-local Prometheus/Loki/Tempo stacks are deleted.


## Destructive backend removal

`task backend:down` deletes the backend Kustomization, including the
`observability-backend` namespace and PVC-backed retained data.

It is intentionally guarded:

```bash
OCO_CONFIRM_DELETE_BACKEND=YES task backend:down
```

Do not use this command as the normal way to stop or restart the presentation
console. Console lifecycle is independent from backend retention.
