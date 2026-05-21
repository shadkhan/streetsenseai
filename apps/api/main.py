from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import admin, audit, compliance, copilot, corridors, dtro, embed, health, nuar, scheduling, webhooks, works

app = FastAPI(
    title="StreetSense AI API",
    version="0.1.0",
    description="Cross-Authority Roadworks Intelligence Platform",
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(works.router)
app.include_router(corridors.router)
app.include_router(nuar.router)
app.include_router(compliance.router)
app.include_router(copilot.router)
app.include_router(scheduling.router)
app.include_router(audit.router)
app.include_router(webhooks.router)
app.include_router(health.router)
app.include_router(dtro.router)
app.include_router(embed.router)
app.include_router(admin.router)


@app.get("/health")
async def health() -> dict[str, object]:
    return {"status": "ok", "phase": 1}
