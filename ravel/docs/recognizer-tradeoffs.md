# Recognizer Trade-offs: madmom vs autochord

Two candidate pretrained recognizers for v1's chord stage. Both emit maj/min/N only (12 maj + 12 min + no-chord = 25 classes). Neither covers the full vocabulary originally requested (7, maj7, min7, dim, dim7, aug, sus2, sus4, 9). That gap is a separate decision; this doc compares the two on the dimensions that affect v1.

## Side-by-side

| Aspect | madmom | autochord |
|---|---|---|
| Architecture | CNN chroma extractor + CRF decoder | NNLS-Chroma VAMP plugin (native CPU) + TensorFlow BiLSTM-CRF |
| Framework | Custom NN loader (PyTorch tensors) | TensorFlow + native VAMP plugin |
| Vocabulary | maj, min, N | maj, min, N |
| Accuracy | ~70–80% weighted overlap on Billboard-style benchmarks (literature range, not a single self-reported figure) | 67.3% self-reported on their test set (different benchmark) |
| Heavy stage | CNN over spectrogram frames — GPU-friendly | VAMP chroma extraction — CPU-only native binary, no GPU path |
| macOS support | Cross-platform; works on M1 (MPS uncertain, falls back to CPU) | Ubuntu out-of-box; macOS needs manual VAMP install; Windows unsupported |
| Setup | One pip install, models bundled | pip pulls TensorFlow; VAMP plugin must be installed separately and discoverable via `VAMP_PATH` |
| Maintenance | 1.7k stars, multi-author (CPJKU academic group); quieter in recent years but stable | 162 stars, single author, last activity 2021; effectively dormant |
| Output shape | `(start, end, label)` numpy array | `[(start, end, label), ...]` tuples |
| Label syntax | JAMS-style (`C:maj`, `A:min`, `N`) | Same |

## Performance per 3-minute song

`~` marks estimates from the architecture, not measured runtimes. Verify empirically before locking.

| | madmom on M1 Air 16 GB | madmom on RTX 4090 | autochord on M1 Air 16 GB | autochord on RTX 4090 |
|---|---|---|---|---|
| Feature stage (chroma) | ~10–30s CPU (MPS uncertain) | ~1–2s GPU | ~30s–2min CPU (VAMP, no GPU path) | ~30s–2min CPU (no benefit from GPU) |
| Decode stage (CRF / BiLSTM) | <1s CPU | <1s | ~1–5s CPU | ~1–2s (small speedup on the tiny BiLSTM) |
| **Total** | **~2–6 min** | **~1–3s** | **~1–2 min** | **~1–2 min** (≈ same as M1) |

The asymmetry that matters: madmom's heavy stage is a CNN that runs on the GPU, so a 4090 collapses wall time to a few seconds. autochord's heavy stage is a native CPU binary (VAMP) that ignores the GPU entirely; the BiLSTM-CRF on top is small, so the 4090 only shaves the trivial part. **On a 4090, madmom is dramatically faster; autochord is barely faster than on M1.**

## Why not librosa (classical chroma + template matching)

A classical approach was considered: librosa CQT chroma → fixed chord templates → Viterbi over a hand-set HMM. Rejected for v1 because accuracy is materially worse than either deep recognizer, and that gap matters more than the speed or simplicity it would buy.

**Fundamental difference from the deep-model route.** The deep-model recognizers (madmom, autochord) learn two things from labeled data: a chroma extractor that suppresses non-chord energy (melody notes, transients, room modes), and a CRF decoder with transition statistics learned from real chord sequences (V→I is common, random jumps rare). The classical route replaces both with fixed math: librosa's CQT chroma accumulates pitch-class energy from *anything* at that pitch — chord tone or passing melody note, inaudible — and template matching uses idealized profiles (maj = {0,4,7} equal-weight) against a hand-set transition matrix. The deep model learned what to ignore; the classical chroma cannot.

**Expected accuracy.** Rough figures (literature range, not single measured numbers):
- madmom DeepChroma + CRF: ~70–80% on Billboard-style benchmarks.
- autochord BiLSTM-CRF: 67.3% self-reported (different benchmark).
- Classical chroma + templates + Viterbi (maj/min only): ~55–65%.

That gap is enough to make the recognized progression visibly wrong on a noticeable fraction of chords — especially in songs with active melodic motion over static harmony, where classical chroma systematically picks up melody notes as chord tones.

**Full-vocabulary caveat.** Classical *can* emit 7/maj7/dim/sus/9 by adding those templates, which neither pretrained deep recognizer does out of the box. But on noisy chroma the rare-quality predictions become unreliable: `C:7` predicted as `C:maj` (the 7th is too quiet), `C:dim` as `C:min` (flat fifth vs fifth is one bin), `C:maj7` as `C:maj`. With no learned prior to weight common qualities over rare ones, the template matcher over-predicts triads. Better to ship maj/min/N that's usually right than full vocab that's visibly wrong on exactly the chords you'd care about.

**Performance.** Classical chroma is FFT-based: roughly realtime to 5× realtime on M1 CPU, so a 3-minute song takes ~3–30s. Viterbi over ~25 templates is milliseconds. Faster than madmom on M1 and comparable to madmom-on-4090. But speed wasn't the deciding factor — accuracy was, and a 4090 doesn't fix classical's fundamental "can't tell a chord tone from a melody note" problem.

**Conclusion.** Classical is faster and simpler but materially less accurate. Since accuracy is the priority and madmom is acceptable on M1 + dramatically faster on the 4090, classical is not worth trading down to. Revisit only if we build a custom recognizer for the full vocabulary, where the classical chroma stage could serve as a baseline feature extractor.

## Why madmom is the better pick here

For Dechord specifically, given you value performance and may run on varied hardware:

- madmom has a real GPU path that pays off on the 4090 (~10–100×) while still working acceptably on M1 CPU.
- autochord pins its bottleneck to a native CPU binary that the 4090 cannot help with. Buying a 4090 would yield almost no inference speedup for autochord.
- autochord's macOS status ("with tweaks") is a setup tax you'd pay on your M1 Air dev machine, on top of TensorFlow + the VAMP plugin.
- Accuracy is comparable (67% vs ~70–80% across different benchmarks) — not enough difference to justify autochord's setup and performance costs.
- librosa (classical) is the fastest and simplest but materially less accurate; rejected because accuracy is a priority.

## Things this decision does not resolve

- **Vocabulary:** both are maj/min/N. If full vocabulary is required for v1, neither is sufficient; that reopens the custom-chroma or self-trained-model discussion.
- **Async job model:** stays regardless of recognizer. Not all users have a powerful GPU, so the chord stage can still take minutes on weak hardware. The async design (`POST /media` → background task → poll `GET /media/{id}`) is the user-facing contract; recognizer choice only affects how fast a single stage completes.

## Verification step before locking

Before committing to madmom, run both on a fixed ~5-song test set on the M1 Air and (if available) on the 4090, and record actual wall times. The estimates above are architectural; measured numbers will surface any setup friction (MPS, VAMP) that isn't visible from the READMEs.