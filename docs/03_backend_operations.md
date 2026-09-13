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

## Validation

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
