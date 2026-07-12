# Dechord

Dechord is a **local** audio tool. You drop a music file in, it recognizes the chord progression, and stores the result so you can re-run or revisit it. Playback is over the original master track; the chord timeline renders as a labeled-rectangle row directly above the master, locked to the same timeline.

Local-only by design — single user, single machine. No accounts, no auth, no remote sync.

## Hardware target

Primary target is Apple MacBook Air, M1, 16 GB unified memory, no fan. Recognizer runs on CPU; MPS acceleration is uncertain in madmom and not relied on.

Per-song latency budget: a few minutes is acceptable, so the chord stage runs asynchronously to the upload request. Users on faster hardware (e.g., a CUDA GPU) get faster turnaround, but the async contract stays the same — not all users have a powerful GPU.

## Pipeline

One stage, run per uploaded media item, asynchronous to the upload request:

1. **Chord recognition** with [madmom](https://github.com/CPJKU/madmom) `DeepChromaChordRecognitionProcessor`. Reads the uploaded master audio directly. No source separation.

Why no source separation: both candidate recognizers (madmom, autochord) are trained on **full mixes**. Feeding Demucs stems is an out-of-distribution input with no demonstrated accuracy benefit and adds minutes of per-song latency. See `recognizer-tradeoffs.md`.

Why madmom over autochord: comparable accuracy (~70–80% vs 67.3% across different benchmarks), and madmom's CNN stage runs on the GPU — fast on a CUDA box, acceptable on M1 CPU — while autochord's chroma stage is a CPU-only native VAMP plugin that the GPU cannot accelerate. Setup is also cleaner on macOS. See `recognizer-tradeoffs.md` for the full comparison.

Why no LLM: dedicated chord recognizers trained on labeled audio are SOTA on chord vocabulary, not language models. An LLM-generated explanation layer is a possible follow-up, out of scope for v1.

## Chord vocabulary

v1 emits what madmom provides: **maj, min, and `N`** (no-chord) — 25 classes (12 maj + 12 min + N). The fuller vocabulary originally considered (7, maj7, min7, dim, dim7, aug, sus2, sus4, 9) is not supported by any pip-installable pretrained recognizer; deferred to a later milestone along with a custom-trained model. See `recognizer-tradeoffs.md`.

## Output contract

Stored per media item, served on `GET /media/{id}`. `start`/`end` are seconds from the start of the audio — no bar or beat positions (see Out of scope).

```json
{
  "id": "media_abc",
  "status": "done",
  "audio": {
    "sample_rate": 44100,
    "duration": 192.4,
    "source_path": "library/ab/abc123.mp3"
  },
  "chords": [
    { "start": 0.0,  "end": 2.12, "label": "C:maj" },
    { "start": 2.12, "end": 4.30, "label": "G:maj" },
    { "start": 4.30, "end": 6.40, "label": "A:min" }
  ]
}
```

`label` uses JAMS-style syntax (`root:quality`, `N` for no chord). Quality is `maj` or `min` only in v1. This is the single contract both ends code against.

## Media library

Uploaded media persists on local disk so you can re-run recognition or replay the track without re-uploading. Storage layout:

```txt
library/
  abc123.mp3              # original upload (hash-named)
  abc123/
    chords.json           # cached recognition result
```

- Original uploads are content-hash addressed. The same byte-identical file uploaded twice dedups to one record.
- SQLite index (`library/index.db`) holds: `media(id, sha256, original_filename, uploaded_at, duration, status, has_chords)`. Schema migrations are trivial initially — define on first task, evolve as needed.
- Serves the manual-testing workflow directly: `POST /media/{id}/jobs` re-runs recognition on an existing item; the upload step is skipped.

## Backend

FastAPI + Pydantic + stdlib `sqlite3` (no ORM; the schema is tiny). One process, FastAPI `BackgroundTasks` for the heavy recognition work — adequate for single-user local use. A real queue (arq + Redis) is deferred until we have an actual contention problem, which on a local single-user tool we won't.

Async model stays: not all users have a powerful GPU, so the chord stage can still take minutes on weak hardware. The upload endpoint returns immediately with an ID; the frontend polls for completion.

Endpoint surface:

- `POST /media` (multipart upload) → `{ id }`. Stores the file, hashes it, creates a `media` row in `queued` state, queues recognition.
- `GET /media` → list of `{ id, original_filename, uploaded_at, status, has_chords }`. Powers the library list UI.
- `GET /media/{id}` → full record incl. `chords` (the Output contract above). 404 if unknown.
- `GET /media/{id}/audio/source` → streams the original upload. Used by the frontend playback UI.
- `POST /media/{id}/chords` → re-runs chord recognition on an existing item. Returns `{ job_id }`. For manual re-recognition.
- `GET /jobs/{id}` → `{ status, progress, media_id }`. Polled by the frontend. `status` ∈ `queued | recognizing | done | failed`.

Caching is intrinsic: recognition writes `chords.json` to the library path; re-running overwrites it.

Dependencies: `fastapi[standard]`, `pydantic`, `madmom` (pulls `torch`). `ffmpeg` normalizes uploads to mono 44.1 kHz before recognition (madmom loads the normalized audio itself via its own `SignalProcessor`).

## Frontend

Next.js + React + shadcn/ui (Lyra preset):

```sh
pnpm dlx shadcn@latest init --preset buFywKm --template next
```

v1 surface, two views:

1. **Library list** — table of media items: filename, duration, status, has-chords. Upload box at the top. Row click → item view. Re-run recognition button per item for manual testing.
2. **Item view** — two stacked tracks, one shared transport:
   - **Chord track (top)** — a row of labeled rectangles, one per chord in `chords[]`, widths proportional to `end - start`, labels rendered with `tonal.js` (root, quality). No bar ruler; the `<->` axis is `mm:ss` seconds. Playback cursor sweeps across in sync with the master transport.
   - **Master track (bottom)** — thin waveform of the source upload, same timeline as the chord track. Play / pause / seek on a single transport controls both.

Audio playback uses the Web Audio API on the master track only. No per-stem playback, no mute/solo, no per-stem FX, no editing, no export.

## Out of scope for v1

- **Source separation** (Demucs or otherwise). No accuracy benefit, significant added latency; see `recognizer-tradeoffs.md`.
- **Per-stem playback, mute, solo, or FX.** v1 plays back the master only.
- DAW-style **bar-ruler chord view**. Needs tempo + downbeat tracking (madmom `DBNBeatProcessor`/`DBNDownBeatProcessor` or librosa `beat_track`); deferred to a later milestone along with bar/beat coordinates in the chord contract. v1 renders chords on a seconds axis.
- **Full chord vocabulary** (7, maj7, min7, dim, dim7, aug, sus2, sus4, 9, slash bass). No pip-installable pretrained recognizer covers it; would require a custom-trained model on McGill Billboard — a research project, deferred.
- **Key detection and Roman-numeral labeling.** Chords display by absolute name (`C:maj`, `A:min`); key is only needed to translate those into scale degrees, which is a later layer.
- **Streaming progress (WebSocket)** — polling first, upgrade only if UX testing complains.

## Open decisions

1. Max upload size and accepted formats (propose: 50 MB, `mp3`/`wav`/`flac`/`m4a`).
2. SQLite schema details — deferred to the first persistence task.
3. ~~Choose the madmom processor variant — `DeepChromaChordRecognitionProcessor` vs `CRFChordRecognitionProcessor` — both emit maj/min/N; pick by quick benchmark during the first recognizer task.~~ **Resolved (T0004):** `DeepChromaChordRecognitionProcessor`. See `ravel/docs/recognizer-benchmark.md`.
