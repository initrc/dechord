"""Throwaway benchmark: compare the two madmom chord recognizers.

Resolves Open decision #3 in ravel/docs/design-v1.md: pick between
`DeepChromaChordRecognitionProcessor` (deep chroma + CRF) and
`CRFChordRecognitionProcessor` (CNN chord features + CRF). Both emit the same
maj/min/N label space, so the choice is empirical accuracy on the target music.

Rather than scoring against hand-labeled ground truth (matching timestamps by
hand is error-prone), this script just runs both recognizers over each audio
file and prints their chord progressions side by side. Verify them manually
against the known progression.

Usage:

    uv run python benchmarks/recognizer_compare.py AUDIO1 [AUDIO2 ...]

Each audio file may be mp3, wav, flac, or m4a. Prints, per file, the segments
from each recognizer as `start - end  label` (seconds), and asserts both stay
within the maj/min/N vocabulary. The verdict is recorded by hand in
ravel/docs/recognizer-benchmark.md.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from madmom.audio.chroma import DeepChromaProcessor
from madmom.features.chords import (
    CNNChordFeatureProcessor,
    CRFChordRecognitionProcessor,
    DeepChromaChordRecognitionProcessor,
)
from madmom.processors import SequentialProcessor

# Canonical maj/min/N label set: roots A..G# across maj/min plus no-chord.
# Used to confirm both recognizers stay within the v1 vocabulary.
_ROOTS = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]
_ALLOWED_LABELS = frozenset(
    [f"{r}:maj" for r in _ROOTS] + [f"{r}:min" for r in _ROOTS] + ["N"]
)

Label = str  # JAMS-style "root:quality" or "N"


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    label: Label


def _segments_from_structured(arr) -> list[Segment]:
    """madmom returns a structured array with start/end/label fields."""
    return [Segment(float(s), float(e), str(lbl)) for s, e, lbl in arr]


def assert_label_space(name: str, segs: list[Segment]) -> None:
    """Confirm a recognizer's output stays in {maj, min, N} per recognizer-tradeoffs.md."""
    labels = {s.label for s in segs}
    unexpected = labels - _ALLOWED_LABELS
    if unexpected:
        raise AssertionError(f"{name} emitted labels outside maj/min/N: {sorted(unexpected)}")


def _build_recognizers() -> dict[str, SequentialProcessor]:
    """Construct each recognizer once (model load is slow); reuse across songs."""
    return {
        "DeepChroma": SequentialProcessor(
            [DeepChromaProcessor(), DeepChromaChordRecognitionProcessor()]
        ),
        "CRF": SequentialProcessor(
            [CNNChordFeatureProcessor(), CRFChordRecognitionProcessor()]
        ),
    }


def _print_progression(name: str, segs: list[Segment]) -> None:
    print(f"=== {name} ({len(segs)} segments) ===")
    for s in segs:
        print(f"  {s.start:>7.2f} - {s.end:>7.2f}   {s.label}")
    print()


def run(audio_path: str, recognizers: dict[str, SequentialProcessor]) -> None:
    """Run both recognizers on one song and print their progressions."""
    for name, proc in recognizers.items():
        segs = _segments_from_structured(proc(audio_path))
        assert_label_space(name, segs)
        _print_progression(name, segs)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(description="Compare madmom chord recognizer variants.")
    parser.add_argument("audio", nargs="+", help="AUDIO1 [AUDIO2 ...]")
    args = parser.parse_args(argv)
    recognizers = _build_recognizers()

    for audio_path in args.audio:
        print(f"### {audio_path}\n")
        run(audio_path, recognizers)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))