# Better OpenTelemetry Local Stack

This repo gives you a **stronger observability baseline** than a minimal compose setup by adding:

- an OpenTelemetry Collector with reliability processors (`memory_limiter`, `batch`),
- OTLP ingest for traces/metrics/logs over gRPC + HTTP,
- RED metrics derived from traces via the `spanmetrics` connector,
- Prometheus for long-lived metrics storage/scraping,
- Jaeger for tracing UX,
- Loki for centralized log querying,
- Grafana pre-provisioned with Prometheus + Jaeger + Loki datasources,
- built-in telemetry generators for traces, metrics, and logs.

## Why this is better than a basic demo stack

Many quick tutorials wire components together but skip operational essentials. This stack bakes in:

1. **Collector safety defaults**: memory limiting + batching.
2. **Multi-signal ingest**: traces, metrics, and logs all accepted via OTLP.
3. **Trace-to-metrics pipeline**: span-to-RED metrics using `spanmetrics`.
4. **First-class logs**: collector logs pipeline exported directly into Loki.
5. **Ready dashboards**: Grafana auto-connects to Prometheus, Jaeger, and Loki.
6. **Smoke-test generators**: one-command demo telemetry to verify ingestion quickly.

## Quick start

```bash
docker compose up -d
```

Open UIs:

- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Jaeger: http://localhost:16686
- Loki API: http://localhost:3100

### Run smoke telemetry generation

> The compose file uses the correct published image path for telemetrygen:
> `ghcr.io/open-telemetry/opentelemetry-collector-contrib/telemetrygen:v0.119.0`

```bash
docker compose run --rm telemetrygen-traces
docker compose run --rm telemetrygen-metrics
docker compose run --rm telemetrygen-logs
```

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

- `docker-compose.yml` - services, ports, persistence, and telemetry generators
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
