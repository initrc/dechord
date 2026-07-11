from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.persistence import init_library
from app.uploads import UploadError, ingest_upload


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


class MediaIdResponse(BaseModel):
    id: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/media", response_model=MediaIdResponse)
async def upload_media(file: UploadFile = File(...)):
    try:
        ingested = await ingest_upload(file)
    except UploadError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    body = MediaIdResponse(id=ingested.row.id).model_dump()
    status = 201 if ingested.created else 200
    return JSONResponse(status_code=status, content=body)