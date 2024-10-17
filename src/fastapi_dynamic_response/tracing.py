# tracing.py

from fastapi_dynamic_response.settings import Settings
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# from opentelemetry.exporter.richconsole import RichConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_tracing(app):
    settings = Settings()
    trace.set_tracer_provider(TracerProvider())
    tracer_provider = trace.get_tracer_provider()

    if settings.ENV == "local":
        # Use console exporter for local development
        # span_exporter = RichConsoleSpanExporter()
        # span_processor = SimpleSpanProcessor(span_exporter)
        # span_exporter = OTLPSpanExporter()
        span_exporter = OTLPSpanExporter(
            endpoint="http://localhost:4317", insecure=True
        )
        span_processor = BatchSpanProcessor(span_exporter)
    else:
        # Use OTLP exporter for production
        span_exporter = OTLPSpanExporter()
        span_processor = BatchSpanProcessor(span_exporter)

    tracer_provider.add_span_processor(span_processor)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
