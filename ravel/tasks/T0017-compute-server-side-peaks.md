---
id: T0017
title: Compute server-side peaks at upload
status: done
dependencies:
  - T0016
---

# Scope

- Eliminate the ~2s client-side decode that still delays the master waveform on item-view mount (T0016 moved peaks precompute off the playback path but kept it on the frontend). Compute peaks once at upload alongside the existing ffmpeg WAV normalization, cache them under `library/{sha}/`, and serve via a new `GET /media/{id}/audio/peaks` endpoint.
- `usePeaks` becomes a thin fetch — no `AudioContext`, no `decodeAudioData`, no client-side scan. The waveform renders as soon as the small peaks blob arrives.

# Acceptance

- `POST /media` computes and stores a peaks file for every freshly ingested media item, using the already-required ffmpeg WAV as input. Deduped uploads (existing sha) do not recompute.
- `GET /media/{media_id}/audio/peaks` streams the cached peaks file as `application/octet-stream` (raw float32 bytes). Returns 404 when the media id or the peaks file is missing.
- `frontend/lib/peaks.ts` drops `AudioContext` / `decodeAudioData` / sample scan; `usePeaks` becomes a fetch + `Float32Array` wrap.
- A 5-min song's item view shows the waveform within tens of ms of mount (peak blob arrival), not seconds — no audible-progress-blocking decode on the main thread.
- Backend: `pytest` passes; new/updated tests cover peak generation and the endpoint. Frontend: `pnpm typecheck` and `pnpm lint` pass.

# Implementation Notes

## Peak extractor

- Compute in `backend/app/uploads.py` right after `_normalize_to_wav` (`uploads.py:117-120`), using the freshly written `library/{sha}/source.wav` as input so ffmpeg doesn't run twice.
- Use **numpy** (already installed via madmom→torch, no new dep). Read the WAV with stdlib `wave` for the header (sample rate, nframes), then `np.frombuffer(data, dtype=np.int16)` + `reshape(-1, bucketSize).max(axis=1).astype(np.float32) / 32768.0`. Mono input, so no channel dimension.
- Bucket size = `floor(sampleRate / PEAKS_PER_SECOND)`. Match `frontend/lib/peaks.ts`'s `PEAKS_PER_SECOND = 1000` exactly — keep that constant in sync (one in backend, one in frontend; a single source of truth is not worth a shared package for one number).
- Upload-time cost: sub-50ms for a 5-min song. Acceptable; the ffmpeg normalization already dominates upload time.

## Storage + transport

- File: `library/{sha}/peaks.bin` — raw float32 bytes, little-endian. ~1.2 MB for a 5-min song at 1000 Hz.
- Add `persistence.peaks_path(sha, library_dir)` mirroring `chords_path` / `source_wav_path` (`persistence.py:324-330`), plus `write_peaks` / `read_peaks` mirroring `write_chords` / `read_chords` (`persistence.py:332-344`). Same pattern, same conventions.
- Endpoint returns `FileResponse(peaks_path, media_type="application/octet-stream")`. Frontend: `fetch(\`/api/media/${mediaId}/audio/peaks\`).then(r => r.arrayBuffer()).then(b => new Float32Array(b))`. No JSON, no base64.

## Endpoint

- `GET /media/{media_id}/audio/peaks` in `backend/app/main.py`, mirroring the existing `/audio/source` route (`main.py:174-189`) — same media-id lookup, same 404 handling, just `peaks_path` instead of `media_file_path`.
- Separate route (not embedded in `MediaDetail`): consistent with `/audio/source`, lazy on demand, keeps `MediaDetail` small (library list view doesn't fetch peaks).

## Compute when

- At upload, inside `ingest_upload` (`uploads.py:117-128`), right after `source_wav` is written and `_wav_duration` is known. Matches the `chords.json` "computed at upload, cached, served as file" pattern (`persistence.py:329-344`).
- Deduped uploads return early (`uploads.py:111-113`) and must NOT recompute — peaks are content-addressed by sha, same as the media file itself.

## Tests

- Backend (`backend/tests/test_uploads.py`): assert `library/{sha}/peaks.bin` exists after upload, and that a byte-identical re-upload does not write it again.
- Backend (`backend/tests/test_library.py`): `GET /media/{id}/audio/peaks` returns 200 with `application/octet-stream` and a body whose byte length is `4 * n_peaks`; 404 for unknown media id and for a media id whose peaks file is missing.
- Frontend: no test framework exists for the frontend; rely on manual verification that the waveform appears promptly on mount and still aligns with the chord track.

## Sync `PEAKS_PER_SECOND`

- The 1000 Hz constant lives in two files now: `frontend/lib/peaks.ts:PEAKS_PER_SECOND` and the backend extractor. If either changes without the other, bucket→time mapping drifts. A comment at each site calling out the other location is the minimum; do not introduce a shared package or generated value for a single integer.

## References

- `frontend/lib/peaks.ts` — client-side `usePeaks` to replace.
- `frontend/components/master-track.tsx` — consumer of the peaks array; unchanged by this task (only the source of the array changes).
- `backend/app/uploads.py:50-65` — `_normalize_to_wav` (peak extraction slots in just after this).
- `backend/app/uploads.py:117-128` — the upload-time preprocess block to extend.
- `backend/app/persistence.py:324-344` — `source_wav_path` / `chords_path` / `write_chords` / `read_chords` patterns to mirror for `peaks_path` / `write_peaks` / `read_peaks`.
- `backend/app/main.py:174-189` — `/audio/source` endpoint to mirror for `/audio/peaks`.
- `backend/tests/test_uploads.py`, `backend/tests/test_library.py` — test patterns to extend.
- T0016 — moved peaks precompute off the playback path; this task moves it off the frontend entirely.