"""
Structured logging into belgium_agent_log. Never silently swallow context.
"""
import traceback
from .supabase_client import supabase


def log_action(action: str, details: dict | None = None, success: bool = True):
    try:
        supabase().table("belgium_agent_log").insert({
            "action": action,
            "details": details or {},
            "success": success,
        }).execute()
    except Exception as e:
        print(f"log_action failed for {action}: {e}")


def log_exception(action: str, exc: Exception, extra: dict | None = None):
    details = {
        "error": str(exc),
        "type": type(exc).__name__,
        "trace": traceback.format_exc(),
    }
    if extra:
        details.update(extra)
    log_action(action, details, success=False)
