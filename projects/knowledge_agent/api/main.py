from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

# Absolute Workspace Imports
from projects.knowledge_agent.api.routers import chat, extract, health, knowledge
from projects.knowledge_agent.api.logging_config import setup_logging
from projects.knowledge_agent.api.middleware import add_trace_id
from projects.knowledge_agent.api.exceptions import (
    validation_exception_handler,
    general_exception_handler
)

# 1. Initialize logging configurations before app boots
setup_logging()

app = FastAPI(
    title="Enterprise Knowledge Agent API",
    version="1.0.0",
    description="Backend services for document ingestion, retrieval, and QA."
)

# 2. Register Middleware (Intercepts all requests)
app.middleware("http")(add_trace_id)


# 3. Register Global Exception Handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 4. Include Endpoints
app.include_router(health.router)
app.include_router(chat.router, prefix="/chat")
app.include_router(extract.router, prefix="/extract")
app.include_router(knowledge.router, prefix="/knowledge")

# 5. Temporary testing route to force an intentional system crash
@app.get("/force-error")
async def force_error():
    raise RuntimeError("Intentional system crash for testing purposes!")