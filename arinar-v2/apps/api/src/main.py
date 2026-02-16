"""FastAPI application entry point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routes import (
    health, agents, debates, turns, setup, summary, events, openrouter,
    personas, materials, memory, preflight, artifacts, embeddings,
    workspace_settings, presence, websocket, knowledge, analytics, ai_assist,
    participants, autonomous
)


app = FastAPI(
    title="Arinar Debate API",
    description="M1/M2: Debate API with realtime controls",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(agents.router, tags=["agents"])
app.include_router(debates.router, tags=["debates"])
app.include_router(turns.router, tags=["turns"])
app.include_router(setup.router, tags=["setup"])
app.include_router(summary.router, tags=["summary"])
app.include_router(events.router, tags=["events"])
app.include_router(openrouter.router, tags=["openrouter"])
app.include_router(personas.router, tags=["personas"])
app.include_router(materials.router, tags=["materials"])
app.include_router(memory.router, tags=["memory"])
app.include_router(preflight.router, tags=["preflight"])
app.include_router(artifacts.router, tags=["artifacts"])
app.include_router(embeddings.router, tags=["embeddings"])
app.include_router(workspace_settings.router, tags=["workspace-settings"])
app.include_router(presence.router, tags=["presence"])
app.include_router(websocket.router, tags=["websocket"])
app.include_router(knowledge.router, tags=["knowledge"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(ai_assist.router, tags=["ai-assist"])
app.include_router(participants.router, tags=["participants"])
app.include_router(autonomous.router, tags=["autonomous"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug
    )
