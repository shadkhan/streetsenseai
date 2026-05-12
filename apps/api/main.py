from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import compliance, copilot, corridors, health, nuar, webhooks, works

app = FastAPI(
    title="StreetSense AI API",
    version="0.1.0",
    description="Cross-Authority Roadworks Intelligence Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(works.router)
app.include_router(corridors.router)
app.include_router(nuar.router)
app.include_router(compliance.router)
app.include_router(copilot.router)
app.include_router(webhooks.router)
app.include_router(health.router)


@app.get("/health")
async def health() -> dict[str, object]:
    return {"status": "ok", "phase": 1}
