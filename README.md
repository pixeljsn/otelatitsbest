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

## What is preconfigured

- Collector reliability processors (`memory_limiter`, `batch`)
- Trace-to-metrics RED generation (`spanmetrics`)
- Prometheus scrape targets for collector metrics
- Grafana datasources for Prometheus, Jaeger, and Loki
