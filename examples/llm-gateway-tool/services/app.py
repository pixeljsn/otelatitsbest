import json
import logging
import os
import random
import time
from typing import Dict

import httpx
from fastapi import FastAPI, HTTPException
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SERVICE_NAME = os.getenv("SERVICE_NAME", "gateway-api")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
TOOL_FAIL_MODE = os.getenv("TOOL_FAIL_MODE", "none")
TIMEOUT_SECONDS = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "2.0"))
TRACE_EXPORT_INTERVAL_MS = int(os.getenv("TRACE_EXPORT_INTERVAL_MS", "1000"))

resource = Resource.create({"service.name": SERVICE_NAME, "deployment.environment": "demo"})

trace_provider = TracerProvider(resource=resource)
trace_provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces"),
        schedule_delay_millis=TRACE_EXPORT_INTERVAL_MS,
    )
)
trace.set_tracer_provider(trace_provider)

metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=f"{OTEL_ENDPOINT}/v1/metrics"),
    export_interval_millis=5000,
)
metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

log_provider = LoggerProvider(resource=resource)
log_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{OTEL_ENDPOINT}/v1/logs")))

logger = logging.getLogger(SERVICE_NAME)
logger.setLevel(logging.INFO)
logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=log_provider))

tracer = trace.get_tracer(SERVICE_NAME)
meter = metrics.get_meter(SERVICE_NAME)
request_counter = meter.create_counter("demo_requests_total", unit="1", description="Total requests in demo services")
error_counter = meter.create_counter("demo_errors_total", unit="1", description="Total errors in demo services")

app = FastAPI(title=f"{SERVICE_NAME} demo service")
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()


state: Dict[str, str] = {"tool_fail_mode": TOOL_FAIL_MODE}


def _trace_meta() -> Dict[str, str]:
    span_context = trace.get_current_span().get_span_context()
    return {
        "trace_id": f"{span_context.trace_id:032x}",
        "span_id": f"{span_context.span_id:016x}",
        "service": SERVICE_NAME,
    }


def log_event(level: str, event: str, **fields: object) -> None:
    payload = {"event": event, **_trace_meta(), **fields}
    if level == "error":
        logger.error(json.dumps(payload))
    else:
        logger.info(json.dumps(payload))



log_event(
    "info",
    "otel_configured",
    otlp_endpoint=OTEL_ENDPOINT,
    trace_export_interval_ms=TRACE_EXPORT_INTERVAL_MS,
)

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


@app.post("/ask")
async def ask(question: str) -> Dict[str, object]:
    if SERVICE_NAME != "gateway-api":
        raise HTTPException(status_code=404, detail="Route only available on gateway-api")

    request_counter.add(1, {"service": SERVICE_NAME, "route": "/ask"})
    with tracer.start_as_current_span("gateway.handle_request"):
        log_event("info", "gateway_received_question", question=question)
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            try:
                resp = await client.post("http://llm-service:8080/generate", params={"question": question})
                resp.raise_for_status()
            except Exception as exc:
                error_counter.add(1, {"service": SERVICE_NAME, "reason": "llm_dependency"})
                log_event("error", "gateway_llm_call_failed", error=str(exc))
                raise HTTPException(status_code=503, detail="LLM service unavailable") from exc

        answer = resp.json()
        log_event("info", "gateway_responding", token_usage=answer.get("tokens", 0))
        return {"answer": answer, "served_by": SERVICE_NAME}


@app.post("/admin/tool-fail-mode/{mode}")
async def set_tool_fail_mode_from_gateway(mode: str) -> Dict[str, str]:
    if SERVICE_NAME != "gateway-api":
        raise HTTPException(status_code=404, detail="Route only available on gateway-api")

    if mode not in {"none", "timeout", "error"}:
        raise HTTPException(status_code=400, detail="mode must be one of: none, timeout, error")

    with tracer.start_as_current_span("gateway.set_tool_fail_mode"):
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            try:
                resp = await client.post(f"http://tool-service:8080/admin/fail-mode/{mode}")
                resp.raise_for_status()
            except Exception as exc:
                error_counter.add(1, {"service": SERVICE_NAME, "reason": "tool_admin_dependency"})
                log_event("error", "gateway_tool_fail_mode_update_failed", mode=mode, error=str(exc))
                raise HTTPException(status_code=503, detail="Failed to update tool fail mode") from exc

        log_event("info", "gateway_tool_fail_mode_updated", mode=mode)
        return {"tool_fail_mode": mode}


@app.post("/generate")
async def generate(question: str) -> Dict[str, object]:
    if SERVICE_NAME != "llm-service":
        raise HTTPException(status_code=404, detail="Route only available on llm-service")

    request_counter.add(1, {"service": SERVICE_NAME, "route": "/generate"})
    with tracer.start_as_current_span("llm.plan_and_call_tool"):
        log_event("info", "llm_received_prompt", question=question)
        prompt_tokens = random.randint(80, 180)

        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            try:
                tool_resp = await client.get("http://tool-service:8080/tools/search", params={"q": question})
                tool_resp.raise_for_status()
            except Exception as exc:
                error_counter.add(1, {"service": SERVICE_NAME, "reason": "tool_dependency"})
                log_event("error", "llm_tool_call_failed", error=str(exc), dependency="tool-service")
                raise HTTPException(status_code=502, detail="Tool call failed") from exc

        tool_payload = tool_resp.json()
        answer = f"Based on {tool_payload['source']}: {tool_payload['result']}"
        total_tokens = prompt_tokens + len(answer.split())
        log_event("info", "llm_generated_answer", prompt_tokens=prompt_tokens, total_tokens=total_tokens)
        return {"answer": answer, "tokens": total_tokens}


@app.get("/tools/search")
def tool_search(q: str) -> Dict[str, str]:
    if SERVICE_NAME != "tool-service":
        raise HTTPException(status_code=404, detail="Route only available on tool-service")

    mode = state["tool_fail_mode"]
    request_counter.add(1, {"service": SERVICE_NAME, "route": "/tools/search", "mode": mode})
    with tracer.start_as_current_span("tool.execute_search"):
        log_event("info", "tool_search_invoked", mode=mode, query=q)
        if mode == "timeout":
            sleep_time = TIMEOUT_SECONDS + 1.5
            time.sleep(sleep_time)
            log_event("error", "tool_timeout_simulated", simulated_sleep_seconds=sleep_time)
            error_counter.add(1, {"service": SERVICE_NAME, "reason": "simulated_timeout"})
            raise HTTPException(status_code=504, detail="Simulated upstream timeout")

        if mode == "error":
            log_event("error", "tool_database_connection_refused", reason="postgres connection refused")
            error_counter.add(1, {"service": SERVICE_NAME, "reason": "db_connection_refused"})
            raise HTTPException(status_code=503, detail="Database connection refused")

        return {
            "source": "tool-service",
            "result": f"fresh context for '{q}'",
        }


@app.post("/admin/fail-mode/{mode}")
def set_fail_mode(mode: str) -> Dict[str, str]:
    if SERVICE_NAME != "tool-service":
        raise HTTPException(status_code=404, detail="Route only available on tool-service")

    if mode not in {"none", "timeout", "error"}:
        raise HTTPException(status_code=400, detail="mode must be one of: none, timeout, error")

    state["tool_fail_mode"] = mode
    log_event("info", "tool_fail_mode_updated", new_mode=mode)
    return {"tool_fail_mode": mode}
