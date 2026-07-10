from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.persistence import init_library


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Idempotent: creates library/ and the media table on first run, no-op after.
    init_library()
    yield


app = FastAPI(title="dechord", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}