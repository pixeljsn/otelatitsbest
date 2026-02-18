# Better OpenTelemetry Local Stack

A ready-to-run local observability stack with:

- OpenTelemetry Collector (OTLP ingest for traces, metrics, logs)
- Jaeger (traces)
- Prometheus (metrics)
- Loki (logs)
- Grafana (pre-provisioned datasources)

## Start

```bash
docker compose up -d
```

## Endpoints

- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Jaeger: http://localhost:16686
- Loki: http://localhost:3100
- OTLP gRPC ingest: localhost:4317
- OTLP HTTP ingest: localhost:4318

## Architecture and data flow

```text
telemetrygen-traces  ─┐
telemetrygen-metrics ─┼── OTLP (gRPC :4317) ──► OpenTelemetry Collector
telemetrygen-logs    ─┘                              │
                                                     ├── traces pipeline ─► Jaeger
                                                     ├── metrics pipeline ─► Prometheus exporter (:8889)
                                                     │                         ▲
                                                     │                         │ scrape
                                                     └── logs pipeline ───► Loki (/otlp)

Prometheus ──(Grafana datasource: Prometheus)──► Grafana dashboards/explore
Jaeger     ──(Grafana datasource: Jaeger)──────► Grafana explore (traces)
Loki       ──(Grafana datasource: Loki)────────► Grafana explore (logs)
```

## What is preconfigured

- Collector reliability processors (`memory_limiter`, `batch`)
- Trace-to-metrics RED generation (`spanmetrics`)
- Prometheus scrape targets for collector metrics
- Grafana datasources for Prometheus, Jaeger, and Loki
- Built-in telemetry generators for traces, metrics, and logs (run continuously)

## Troubleshooting: no logs/metrics/traces in Grafana

> You **do not** need to add Grafana datasources manually. They are provisioned from `grafana/provisioning/datasources/datasources.yml`.

### 1) Verify all services are up

```bash
docker compose ps
```

Expected: `otel-collector`, `grafana`, `prometheus`, `jaeger`, `loki`, and all `telemetrygen-*` services should be `Up`.

### 2) Verify collector is healthy and receiving traffic

```bash
curl -sf http://localhost:13133/
curl -sf http://localhost:8889/metrics | head
```

You should see healthy response and collector metric output.

### 3) Check collector logs for pipeline/exporter errors

```bash
docker compose logs --tail=200 otel-collector
```

Look for errors related to `otlp/jaeger`, `otlphttp/loki`, or `prometheus` exporter.

### 4) Validate signal-specific backends

**Traces (Jaeger):**

```bash
curl -sf http://localhost:16686 | head
```

Then open Jaeger UI and search `Service` list for generated services.

**Metrics (Prometheus):**

```bash
curl -sf 'http://localhost:9090/api/v1/query?query=up' | head
```

`otel-collector-pipeline-metrics` target should be up.

**Logs (Loki):**

```bash
curl -sf http://localhost:3100/ready
```

Should return `ready`.

### 5) Validate Grafana datasource provisioning

```bash
docker compose exec grafana ls -1 /etc/grafana/provisioning/datasources
```

You should see `datasources.yml` present.

### 6) Force fresh telemetry if needed

```bash
docker compose restart telemetrygen-traces telemetrygen-metrics telemetrygen-logs
```

Wait ~30-60 seconds, then refresh Grafana Explore for each datasource.

### 7) If still no data, isolate by path

- If Jaeger has traces but Grafana does not: Grafana datasource/query issue.
- If Prometheus has metrics but Grafana does not: Grafana datasource/query issue.
- If none of Jaeger/Prometheus/Loki have data: collector ingest/export path issue.

### 8) Send a manual test span (optional)

If generators are down or you need an explicit test, run:

```bash
docker compose run --rm telemetrygen-traces traces --otlp-endpoint=otel-collector:4317 --otlp-insecure --rate=5 --duration=15s
```
