from fastapi import FastAPI
from projects.knowledge_agent.api.routers import chat, extract, health

app = FastAPI(title="GenAI Engineer API", version="0.1.0")
app.include_router(health.router)
app.include_router(chat.router, prefix="/chat")
app.include_router(extract.router, prefix="/extract")