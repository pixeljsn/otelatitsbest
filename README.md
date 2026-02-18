# Better OpenTelemetry Local Stack

This repo gives you a **stronger observability baseline** than a minimal compose setup by adding:

- an OpenTelemetry Collector with reliability processors (`memory_limiter`, `batch`),
- OTLP ingest for traces/metrics/logs over gRPC + HTTP,
- RED metrics derived from traces via the `spanmetrics` connector,
- Prometheus for long-lived metrics storage/scraping,
- Jaeger for tracing UX,
- Grafana pre-provisioned with Prometheus + Jaeger datasources.

## Why this is better than a basic demo stack

Many quick tutorials wire components together but skip operational essentials. This stack bakes in:

1. **Collector safety defaults**: memory limiting + batching.
2. **Multi-signal ingest**: traces, metrics, and logs all accepted via OTLP.
3. **Trace-to-metrics pipeline**: span-to-RED metrics using `spanmetrics`.
4. **Ready dashboards**: Grafana auto-connects to Prometheus and Jaeger.

## Quick start

```bash
docker compose up -d
```

Open UIs:

- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Jaeger: http://localhost:16686

## Send telemetry from an app

Set your app's exporter endpoint:

```bash
# gRPC
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# or HTTP
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
```

Recommended common resource attributes:

```bash
OTEL_SERVICE_NAME=my-service
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=local,service.version=1.0.0
```

## Key files

- `docker-compose.yml` - services, ports, and persistence
- `otelcol/config.yaml` - receivers/processors/connectors/exporters
- `prometheus/prometheus.yml` - scrape targets
- `grafana/provisioning/datasources/datasources.yml` - auto datasource wiring

## Shutdown

```bash
docker compose down
```

To also remove persisted data:

```bash
docker compose down -v
```
