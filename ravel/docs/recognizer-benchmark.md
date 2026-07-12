# Recognizer Benchmark: DeepChroma vs CRF (madmom)

Resolves Open decision #3 in `design-v1.md`. Picks the madmom processor variant for
v1's chord stage.

## Decision

Use `DeepChromaChordRecognitionProcessor` (deep chroma + CRF) as the v1 chord
recognizer.

## What was compared

Both madmom recognizers emit the same maj/min/N label space (25 classes) via
`majmin_targets_to_chord_labels`, so the only difference is the front-end that
feeds each one's CRF decoder:

- **DeepChromaChordRecognitionProcessor** — `DeepChromaProcessor` deep chroma
  extractor + CRF (Korzeniowski & Widmer, ISMIR 2016, "Feature Learning for
  Chord Recognition: The Deep Chroma Extractor").
- **CRFChordRecognitionProcessor** — `CNNChordFeatureProcessor` CNN chord
  features + CRF (Korzeniowski & Widmer, MLSP 2016, "A Fully Convolutional Deep
  Auditory Model for Musical Chord Recognition").

Both were run over a single song (`backend/benchmarks/samples/suzume.mp3`, ~101 s)
the user knows the progression of from their DAW, via
`backend/benchmarks/recognizer_compare.py`. No hand-labeled ground-truth JSON was
produced; the two recognizers' outputs were compared against the known
progression by eye. Both stayed within maj/min/N (confirmed by the script's
label-space assertion).

## Rationale

### Why DeepChroma (chosen)

On the test song the two recognizers land close on the *chords themselves* for a
simple piano passage, but `DeepChromaChordRecognitionProcessor` produces a
cleaner, more coherent segmentation: 36 segments vs CRF's 50, without the
spurious short fragments CRF inserts (several sub-2-second labels in the intro
and mid-section that don't correspond to real chord changes). For a chord
*progression* view — where each labeled rectangle is meant to read as one chord
in a sequence — over-segmentation is actively harmful: it makes the progression
look noisier than it is and breaks the visual grouping the UI relies on.
DeepChroma's coarser, steadier segments read as a real progression.

### Why not CRF (rejected)

`CRFChordRecognitionProcessor` lands comparable chord *labels* on simple
material but splits the timeline too finely. On `suzume.mp3` it carved a single
long no-chord intro into several short `N`/`C:maj`/`G:maj`/`A:min` fragments and
inserted isolated one-off labels (`G:maj`, `A:min`, `B:min` around 31–42 s) that
don't reflect actual harmony. Both recognizers were already the worse for
complicated orchestral or dense pop material — maj/min/N undersells those styles
regardless of front-end — so when the simple-material case is roughly a tie on
labels, the segmentation granularity is the right tie-breaker, and it favors
DeepChroma. This also matches `T0004`'s fallback rule: within noise, pick
`DeepChromaChordRecognitionProcessor` (smaller, older, well-cited, the one the
~70–80% literature figure in `recognizer-tradeoffs.md` actually refers to).

## Caveats

- Single-song, by-eye comparison. This is a throwaway tie-break for v1, not a
  measured accuracy claim. Both recognizers are visibly wrong on dense
  orchestral/pop material; the maj/min/N vocabulary is the binding limit there,
  not the front-end choice.
- The full chord vocabulary (7, maj7, min7, dim, sus, 9) is out of scope for v1
  (`design-v1.md`, Out of scope); reopening that requires a custom-trained model,
  not a different choice among these two pretrained recognizers.
- T0005 implements the recognition service against `DeepChromaChordRecognitionProcessor`
  per this decision.