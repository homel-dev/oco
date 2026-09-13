#!/usr/bin/env bash
set -euo pipefail

NS=observability-backend
TRACE_ID=11111111111111111111111111111111
SPAN_ID=2222222222222222
NOW_NS="$(date +%s)000000000"

kubectl -n "$NS" run oco-smoke-sender --rm -i --restart=Never \
  --image=curlimages/curl:8.16.0 -- sh -eu -c "
  curl -fsS -H 'Content-Type: application/json' \
    http://alloy:4318/v1/metrics \
    -d '{\"resourceMetrics\":[{\"resource\":{\"attributes\":[{\"key\":\"project\",\"value\":{\"stringValue\":\"oco\"}},{\"key\":\"service.name\",\"value\":{\"stringValue\":\"oco-smoke\"}},{\"key\":\"k8s.namespace.name\",\"value\":{\"stringValue\":\"observability-backend\"}},{\"key\":\"deployment.environment.name\",\"value\":{\"stringValue\":\"minikube\"}}]},\"scopeMetrics\":[{\"scope\":{},\"metrics\":[{\"name\":\"oco_smoke_total\",\"sum\":{\"aggregationTemporality\":2,\"isMonotonic\":true,\"dataPoints\":[{\"asInt\":\"1\",\"timeUnixNano\":\"$NOW_NS\"}]}}]}]}]}]}'

  curl -fsS -H 'Content-Type: application/json' \
    http://alloy:4318/v1/logs \
    -d '{\"resourceLogs\":[{\"resource\":{\"attributes\":[{\"key\":\"project\",\"value\":{\"stringValue\":\"oco\"}},{\"key\":\"service.name\",\"value\":{\"stringValue\":\"oco-smoke\"}},{\"key\":\"k8s.namespace.name\",\"value\":{\"stringValue\":\"observability-backend\"}},{\"key\":\"deployment.environment.name\",\"value\":{\"stringValue\":\"minikube\"}}]},\"scopeLogs\":[{\"scope\":{},\"logRecords\":[{\"timeUnixNano\":\"$NOW_NS\",\"severityText\":\"INFO\",\"body\":{\"stringValue\":\"oco-shared-backend-smoke\"},\"traceId\":\"$TRACE_ID\",\"spanId\":\"$SPAN_ID\"}]}]}]}]}'

  curl -fsS -H 'Content-Type: application/json' \
    http://alloy:4318/v1/traces \
    -d '{\"resourceSpans\":[{\"resource\":{\"attributes\":[{\"key\":\"project\",\"value\":{\"stringValue\":\"oco\"}},{\"key\":\"service.name\",\"value\":{\"stringValue\":\"oco-smoke\"}},{\"key\":\"k8s.namespace.name\",\"value\":{\"stringValue\":\"observability-backend\"}},{\"key\":\"deployment.environment.name\",\"value\":{\"stringValue\":\"minikube\"}}]},\"scopeSpans\":[{\"scope\":{},\"spans\":[{\"traceId\":\"$TRACE_ID\",\"spanId\":\"$SPAN_ID\",\"name\":\"oco-smoke\",\"kind\":1,\"startTimeUnixNano\":\"$NOW_NS\",\"endTimeUnixNano\":\"$NOW_NS\"}]}]}]}]}'
"

sleep 8

kubectl -n "$NS" run oco-smoke-query --rm -i --restart=Never \
  --image=curlimages/curl:8.16.0 -- sh -eu -c "
  curl -fsS \
    'http://victoriametrics:8428/api/v1/query?query=oco_smoke_total' \
    | grep -q oco_smoke_total

  curl -fsS --get \
    'http://victorialogs:9428/select/logsql/query' \
    --data-urlencode 'query=_msg:oco-shared-backend-smoke' \
    | grep -q oco-shared-backend-smoke

  curl -fsS \
    'http://tempo:3200/api/traces/$TRACE_ID' \
    | grep -q oco-smoke
"

echo "OCO backend smoke PASS"
