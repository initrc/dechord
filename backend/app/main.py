import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app import persistence
from app.jobs import run_recognition_job
from app.persistence import MediaStatus
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


class MediaListItem(BaseModel):
    id: str
    original_filename: str
    uploaded_at: str
    status: str
    has_chords: bool


class AudioMeta(BaseModel):
    sample_rate: int
    duration: float
    source_path: str


class ChordSegment(BaseModel):
    start: float
    end: float
    label: str


class MediaDetail(BaseModel):
    id: str
    status: str
    audio: AudioMeta
    chords: list[ChordSegment]


class JobIdResponse(BaseModel):
    job_id: str


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


@app.get("/media", response_model=list[MediaListItem])
def list_media():
    conn = persistence.open_db(persistence.DB_PATH)
    try:
        rows = persistence.list_media(conn)
    finally:
        conn.close()
    return [
        MediaListItem(
            id=r.id,
            original_filename=r.original_filename,
            uploaded_at=r.uploaded_at,
            status=r.status,
            has_chords=r.has_chords,
        )
        for r in rows
    ]


@app.get("/media/{media_id}", response_model=MediaDetail)
def get_media_detail(media_id: str):
    conn = persistence.open_db(persistence.DB_PATH)
    try:
        row = persistence.get_media(conn, media_id)
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"unknown media: {media_id}")

    ext = Path(row.original_filename).suffix
    source_path = str(persistence.media_file_path(row.sha256, ext, library_dir=persistence.LIBRARY_DIR))
    assert row.duration is not None

    chords: list[dict[str, Any]] = []
    if row.has_chords:
        try:
            chords = json.loads(persistence.read_chords(row.sha256, library_dir=persistence.LIBRARY_DIR))
        except (FileNotFoundError, json.JSONDecodeError):
            chords = []

    return MediaDetail(
        id=row.id,
        status=row.status,
        audio=AudioMeta(
            sample_rate=44100,
            duration=row.duration,
            source_path=source_path,
        ),
        chords=[
            ChordSegment(
                start=float(c["start"]),
                end=float(c["end"]),
                label=str(c["label"]),
            )
            for c in chords
        ],
    )


@app.get("/media/{media_id}/audio/source")
def get_audio_source(media_id: str):
    conn = persistence.open_db(persistence.DB_PATH)
    try:
        row = persistence.get_media(conn, media_id)
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"unknown media: {media_id}")

    ext = Path(row.original_filename).suffix
    file_path = persistence.media_file_path(row.sha256, ext, library_dir=persistence.LIBRARY_DIR)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="audio file not found")

    return FileResponse(file_path)


@app.post("/media/{media_id}/chords", response_model=JobIdResponse)
def rerun_chords(media_id: str, background_tasks: BackgroundTasks):
    conn = persistence.open_db(persistence.DB_PATH)
    try:
        row = persistence.get_media(conn, media_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"unknown media: {media_id}")
        persistence.update_media_status(conn, media_id, MediaStatus.recognizing)
        job = persistence.insert_job(conn, media_id=media_id)
    finally:
        conn.close()
    background_tasks.add_task(run_recognition_job, job.id, media_id)
    return JobIdResponse(job_id=job.id)