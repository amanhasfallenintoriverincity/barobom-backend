"""Langfuse tracing integration (deferred — no-op until credentials set)."""
import os

LANGFUSE_ENABLED = bool(
    os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")
)

_trace_client = None


def get_trace_client():
    global _trace_client
    if not LANGFUSE_ENABLED:
        return None
    if _trace_client is None:
        from langfuse import Langfuse
        _trace_client = Langfuse(
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    return _trace_client


def trace_event(event_type: str, anonymous_id: str, metadata: dict | None = None):
    """Log an event via Langfuse if configured. Always succeeds silently."""
    try:
        client = get_trace_client()
        if client is None:
            return
        trace = client.trace(
            name=f"user_event:{event_type}",
            user_id=anonymous_id,
            metadata=metadata or {},
        )
    except Exception:
        pass
