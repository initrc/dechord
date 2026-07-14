from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import persistence
from app.jobs import run_recognition_job
from app.uploads import UploadError, ingest_upload


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Idempotent: creates library/ and the media/job tables on first run, no-op after.
    persistence.init_library()
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
    # Present when a fresh upload queued a recognition job; omitted on dedup
    # (an existing media row is not re-queued). Additive over design-v1.md's
    # `{ id }` contract so the frontend can poll `GET /jobs/{id}`.
    job_id: str | None = None


class JobResponse(BaseModel):
    status: str
    progress: int
    media_id: str
    error: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/media", response_model=MediaIdResponse)
async def upload_media(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    try:
        ingested = await ingest_upload(file)
    except UploadError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

    job_id: str | None = None
    if ingested.created:
        conn = persistence.open_db(persistence.DB_PATH)
        try:
            job = persistence.insert_job(conn, media_id=ingested.row.id)
        finally:
            conn.close()
        background_tasks.add_task(run_recognition_job, job.id, ingested.row.id)
        job_id = job.id

    body = MediaIdResponse(id=ingested.row.id, job_id=job_id).model_dump(exclude_none=True)
    status = 201 if ingested.created else 200
    return JSONResponse(status_code=status, content=body)


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    conn = persistence.open_db(persistence.DB_PATH)
    try:
        job = persistence.get_job(conn, job_id)
    finally:
        conn.close()
    if job is None:
        raise HTTPException(status_code=404, detail=f"unknown job: {job_id}")
    return JobResponse(
        status=job.status, progress=job.progress, media_id=job.media_id, error=job.error
    )