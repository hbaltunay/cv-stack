import asyncio
import functools
from collections.abc import Callable
from typing import Any

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.propagate import extract, inject
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.trace import (
    SpanKind,
    Status,
    StatusCode,
    format_trace_id,
)

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger("cvs")


def setup_telemetry() -> None:
    resource = Resource.create(attributes={"service.name": "kafka-consumer"})

    provider = TracerProvider(resource=resource)

    if settings.ENVIRONMENT == "production":
        otlp_exporter = OTLPSpanExporter(settings.OTEL_ENDPOINT, insecure=True)
        batch_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(batch_processor)

    else:
        console_exporter = ConsoleSpanExporter()
        simple_processor = SimpleSpanProcessor(console_exporter)
        provider.add_span_processor(simple_processor)

    trace.set_tracer_provider(provider)

    # RedisInstrumentor().instrument()
    # ConfluentKafkaInstrumentor().instrument()


def get_trace_id() -> str | None:
    current_span = trace.get_current_span()
    span_context = current_span.get_span_context()

    if span_context.is_valid:
        return format_trace_id(span_context.trace_id)

    return None


def get_trace_span(headers: list) -> tuple[Context, SpanKind]:
    carrier = {
        k: v.decode("utf-8") if isinstance(v, bytes) else v for k, v in headers
    }
    return extract(carrier), SpanKind.CONSUMER


def trace_inject(request_id: str) -> list:
    headers_dict = {}
    headers_dict["request_id"] = request_id
    inject(headers_dict)
    return headers_dict


def observe(
    name: str | None = None, in_context: bool = False, **attributes: Any
) -> Callable[..., Any]:

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if not settings.OTEL_ENABLED:
            return func

        span_name = name if name else func.__name__

        attributes_payload = {
            f"{key}": str(value) for key, value in attributes.items()
        }

        tracer = trace.get_tracer(__name__)

        def _extract_kafka_meta(
            args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> tuple[dict[str, Any], Any, Any, str]:
            msg = (
                kwargs.get("msg")
                if "msg" in kwargs
                else (args[1] if args else None)
            )

            payload = {}
            extracted_context = None
            extracted_kind = None

            if msg and hasattr(msg, "headers") and msg.headers():
                try:
                    headers = {
                        key: val.decode("utf-8") for key, val in msg.headers()
                    }
                    request_id = headers.get("request_id")
                    if request_id:
                        payload["request_id"] = str(request_id)

                    extracted_context, extracted_kind = get_trace_span(
                        msg.headers()
                    )

                except Exception:
                    pass

            return payload, extracted_context, extracted_kind

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if in_context:
                dynamic_attrs, context, kind = _extract_kafka_meta(args, kwargs)
            else:
                dynamic_attrs, context, kind = None, None, SpanKind.INTERNAL

            with tracer.start_as_current_span(
                span_name, context=context, kind=kind
            ) as span:
                try:
                    if attributes_payload:
                        span.set_attributes(attributes_payload)
                    if dynamic_attrs:
                        span.set_attributes(dynamic_attrs)
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise e

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if in_context:
                dynamic_attrs, context, kind = _extract_kafka_meta(args, kwargs)
            else:
                dynamic_attrs, context, kind = None, None, SpanKind.INTERNAL

            with tracer.start_as_current_span(
                span_name, context=context, kind=kind
            ) as span:
                try:
                    if attributes_payload:
                        span.set_attributes(attributes_payload)
                    if dynamic_attrs:
                        span.set_attributes(dynamic_attrs)
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise e

        if asyncio.iscoroutinefunction(func):
            return async_wrapper

        return sync_wrapper

    return decorator


def set_attributes(attributes: dict) -> str | None:
    attributes_payload = {
        f"{key}": str(value) for key, value in attributes.items()
    }
    current_span = trace.get_current_span()

    if current_span.is_recording():
        current_span.set_attributes(attributes_payload)
        span_context = current_span.get_span_context()
        if span_context.is_valid:
            return format_trace_id(span_context.trace_id)
    return None
