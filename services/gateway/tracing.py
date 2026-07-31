"""OpenTelemetry 链路追踪配置"""

from shared.config import get_settings
from shared.utils import get_logger

logger = get_logger(__name__)


def setup_tracing(app):
    """配置 OpenTelemetry 链路追踪"""
    settings = get_settings()

    if settings.app_env == "development" and not settings.app_debug:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        resource = Resource.create({"service.name": settings.app_name, "service.version": "0.1.0"})
        provider = TracerProvider(resource=resource)

        # 开发环境输出到控制台，生产环境对接Jaeger
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app)
        logger.info("OpenTelemetry tracing initialized")

    except ImportError:
        logger.warning("OpenTelemetry packages not installed, tracing disabled")
    except Exception as e:
        logger.error("Failed to initialize tracing", error=str(e))
