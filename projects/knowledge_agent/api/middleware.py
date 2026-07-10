import uuid
import time
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

async def add_trace_id(request: Request, call_next):
    trace_id = str(uuid.uuid4())[:8]
    request.state.trace_id = trace_id
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() -start) * 1000, 2)
    response.headers["X-TRACE-ID"] = trace_id
    logger.info(f"trace={trace_id} method={request.method} path={request.url.path} duration_ms={duration} status={response.status_code}")
    return response