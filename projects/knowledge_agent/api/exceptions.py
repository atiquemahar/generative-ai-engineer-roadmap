from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger(__name__)

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_failed",
            "details": exc.errors(),
            "trace_id": getattr(request.state, "trace_id", None)
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled_error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "trace_id": getattr(request.state, "trace_id", None)}
    )

