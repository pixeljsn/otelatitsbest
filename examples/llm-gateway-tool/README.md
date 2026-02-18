# LLM Gateway → Tool Correlation Demo (Traces + Logs + Metrics)

A trendy but practical failure story:

`gateway-api -> llm-service -> tool-service`

The `tool-service` can simulate a realistic outage reason (`database connection refused` or timeout).
You then correlate telemetry across **metrics**, **traces**, and **logs** to find the root cause quickly.

## Why separate compose?

This demo is intentionally isolated from the root stack so it stays clean and easy to start/stop.

## Start

```bash
docker compose -f examples/llm-gateway-tool/docker-compose.yml up --build -d
```

## Endpoints

- Gateway API: http://localhost:18080
- Admin (via gateway) to toggle tool fail mode from host: `POST /admin/tool-fail-mode/{none|timeout|error}`
- Grafana: http://localhost:13000 (admin/admin)
- Jaeger UI: http://localhost:16687
- Prometheus: http://localhost:19090
- Loki API: http://localhost:13100

## Generate normal traffic

```bash
for i in {1..8}; do
  curl -s -X POST "http://localhost:18080/ask?question=what+is+the+risk+$i" | jq
done
```

## Simulate outage (tool DB reason)

1) Turn on failure mode in the tool:

```bash
curl -s -X POST http://localhost:18080/admin/tool-fail-mode/error | jq
```

2) Generate failing requests:

```bash
for i in {1..10}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST "http://localhost:18080/ask?question=incident+$i"
done
```

Expect HTTP `503` from gateway when downstream fails.

## Correlation workflow (root-cause in minutes)

1. **Metrics first (Prometheus/Grafana):**
   - Look for rise in error requests and latency around same timestamp.
   - Useful metric families from spanmetrics: `traces_spanmetrics_calls_total`, `traces_spanmetrics_duration_*`.

2. **Traces second (Jaeger):**
   - Search service `gateway-api` with error status.
   - Open one trace; you should see the chain `gateway-api -> llm-service -> tool-service`.
   - Failing span appears in tool call.

3. **Logs third (Loki in Grafana Explore):**
   - Query `{service_name="tool-service"}` in the failing timeframe.
   - Find log event `tool_database_connection_refused`.
   - Log body includes `trace_id` and `span_id`; match to trace for exact correlation.

## Common log events to demonstrate

- `gateway_llm_call_failed`
- `llm_tool_call_failed`
- `tool_database_connection_refused`
- `tool_timeout_simulated`

## Switch back to healthy mode

```bash
curl -s -X POST http://localhost:18080/admin/tool-fail-mode/none | jq
```

## Stop and clean

```bash
docker compose -f examples/llm-gateway-tool/docker-compose.yml down -v
```
