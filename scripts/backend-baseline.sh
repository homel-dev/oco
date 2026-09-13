#!/usr/bin/env bash
set -euo pipefail

NS=observability-backend
mkdir -p artifacts
OUT="artifacts/backend-baseline-$(date -u +%Y%m%dT%H%M%SZ).txt"

{
  echo "# OCO backend resource baseline"
  date -u
  echo

  echo "## pods"
  kubectl -n "$NS" get pods -o wide
  echo

  echo "## top"
  kubectl -n "$NS" top pods || true
  echo

  echo "## pvc"
  kubectl -n "$NS" get pvc
  echo

  for d in victoriametrics victorialogs tempo; do
    echo "## filesystem: $d"
    kubectl -n "$NS" exec deploy/"$d" -- df -h || true
    echo
  done

  echo "## VictoriaMetrics counters"
  kubectl -n "$NS" exec deploy/victoriametrics -- \
    wget -qO- http://127.0.0.1:8428/metrics \
    | grep -E 'vm_rows|vm_http_request' \
    | head -80 || true
  echo

  echo "## VictoriaLogs counters"
  kubectl -n "$NS" exec deploy/victorialogs -- \
    wget -qO- http://127.0.0.1:9428/metrics \
    | grep -E 'vl_|vm_http_request' \
    | head -80 || true
} | tee "$OUT"

echo "$OUT"
