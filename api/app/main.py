"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.app.db import init_db
from api.app.seed import seed
from api.app.skills_store import load_all_skills
from api.app.routers.events import router as events_router
from api.app.routers.identify import router as identify_router
from api.app.routers.observations import router as observations_router
from api.app.routers.skills import router as skills_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed()
    load_all_skills()
    yield


app = FastAPI(title="Barobom Backend", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events_router)
app.include_router(identify_router)
app.include_router(observations_router)
app.include_router(skills_router)


@app.get("/health")
def health():
    return {"status": "ok"}
