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
- Built-in telemetry generators for traces, metrics, and logs (run continuously)

## Troubleshooting: no logs/metrics/traces in Grafana

- You **do not** need to add Grafana datasources manually. They are provisioned from `grafana/provisioning/datasources/datasources.yml`.
- Wait ~30-60 seconds after startup for services to become healthy and first samples to arrive.
- Confirm telemetry generators are running:

```bash
docker compose ps telemetrygen-traces telemetrygen-metrics telemetrygen-logs
```

- If needed, restart generators to force fresh traffic:

```bash
docker compose restart telemetrygen-traces telemetrygen-metrics telemetrygen-logs
```

- Check collector health and pipeline metrics:

```bash
curl -sf http://localhost:13133/ && curl -sf http://localhost:8889/metrics | head
```
