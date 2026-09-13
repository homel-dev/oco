# Consumer Migration to OCO Shared Backend

Migrate one project at a time.

Never delete a working local backend before shared-backend parity is
demonstrated.

For each project:

1. inventory current metrics, logs, traces, dashboards, and collectors;
2. label its namespace
   `observability.homel.dev/telemetry-consumer=true`;
3. send standard telemetry to shared Alloy, directly when possible;
4. retain project-local Alloy only when it performs useful local work;
5. update dashboards to shared VictoriaMetrics, VictoriaLogs, and Tempo UIDs;
6. verify telemetry parity;
7. verify historical/query behavior required by the project;
8. verify trace/log/metric correlation;
9. only then remove local Prometheus/Loki/Tempo;
10. remove obsolete Vector or standalone OTel Collector where Alloy replaces it;
11. update that project's documentation.

A reasonable migration order is:

1. OCO itself;
2. llm-runtime;
3. Relentless Rekrow;
4. Memory Steward;
5. host-runtime;
6. remaining consumers.

The order is not an invariant.

Application-owned data is not forced into the shared backend. For example, a
project may expose application PostgreSQL data to Grafana through a dedicated
read-only datasource and explicit NetworkPolicy.
