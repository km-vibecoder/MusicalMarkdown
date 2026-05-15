# .mmd Example Library

Validated reference scores demonstrating the Musical Markdown format.
Each file passes `mmd_validator.py` and works with all Phase 2 tools.

---

## Scores

### `twinkle-shared-melody.mmd` — A Melody, Three Songs
**Demonstrates:** single-voice melody · duration inheritance · half-note held-beat placeholders · three synchronized lyric tracks on one melody track

"Twinkle Twinkle Little Star", "Baa Baa Black Sheep", and the "ABC Song" share
the same traditional melody. A single `T1` track drives `L1`, `L2`, and `L3`
simultaneously, showing how the beat grid synchronizes completely different
text to the same rhythmic skeleton.

```bash
python tools/mmd_validator.py   examples/twinkle-shared-melody.mmd
python tools/mmd_to_midi.py     examples/twinkle-shared-melody.mmd
python tools/mmd_to_lilypond.py examples/twinkle-shared-melody.mmd
python tools/mmd_transposer.py  examples/twinkle-shared-melody.mmd --transpose +5
```

---

### `amazing-grace.mmd` — Two-Hand Piano, Waltz Time
**Demonstrates:** two synchronized T-tracks · left-hand waltz bass pattern · half-note chords · dotted half notes filling a 3/4 measure · pickup measures · explicit accidentals in a key signature

A nine-measure excerpt of "Amazing Grace" (John Newton, 1779 — public domain).
`T1` carries the melody; `T2` plays a traditional waltz bass pattern (root quarter
on beat 1, inner chord half note on beats 2–3). `L1` tracks verse 1 lyrics with
`%` on pickup rests and `_` on sustained melody beats.

The left-hand chord `[F#3,A3]/2` shows explicit sharps — `@KEY: G` is
display-only in `.mmd`, so accidentals must always be written in full.

```bash
python tools/mmd_validator.py   examples/amazing-grace.mmd
python tools/mmd_to_midi.py     examples/amazing-grace.mmd
python tools/mmd_to_lilypond.py examples/amazing-grace.mmd
python tools/mmd_transposer.py  examples/amazing-grace.mmd --transpose -2
```

---

### `transformation-showcase.mmd` — One Motif, Four Forms
**Demonstrates:** transposition · inversion · retrograde · four simultaneous T-tracks · explicit accidentals (Bb4 vs A#4 enharmonic equivalence)

A two-measure motif (`C4→G4` stepwise ascent, `A4→E4` stepwise descent) heard
in four voices simultaneously. Each voice shows a different serial transformation:

| Track | Transformation | CLI flag |
|-------|----------------|----------|
| T1 | Subject (original) | — |
| T2 | Answer: transposed +7 semitones (perfect 5th up) | `--transpose +7` |
| T3 | Inversion: mirrored around G4 — ascent becomes descent | `--invert G4` |
| T4 | Retrograde: measures reversed, then notes within each reversed | `--retrograde` |

Mute any single track in your DAW to hear each transformation in isolation.
Augmentation (`--augment`) doubles note values to four measures and is noted
in the file header as a CLI exercise.

```bash
python tools/mmd_validator.py   examples/transformation-showcase.mmd
python tools/mmd_to_midi.py     examples/transformation-showcase.mmd
python tools/mmd_to_lilypond.py examples/transformation-showcase.mmd

# Reproduce any derived track from T1:
python tools/mmd_transposer.py  examples/transformation-showcase.mmd --transpose +7 --track T1
python tools/mmd_transposer.py  examples/transformation-showcase.mmd --invert G4    --track T1
python tools/mmd_transposer.py  examples/transformation-showcase.mmd --retrograde   --track T1
```

---

### `jazz-turnaround.mmd` — Jazz Chord Comping
**Demonstrates:** four-note jazz voicings (Dm7, G7, Cmaj7, A7) · explicit accidentals in chords (C#3, Bb2) · sub-beat comp rhythm (`R/8,[chord]/8`) · walking bass with chromatic approach tones · C-track chord symbol annotations · `(arp)` modifier

An 8-measure ii–V–I–VI turnaround in C (medium swing, 132 BPM) scored for
three voices: melody, comping hand, and walking bass. The comping track
alternates two patterns — beat-2 backbeat and beat-1 downbeat — with an
off-beat anticipation on the "and-of-4" in every measure. The `R/8,[chord]/8`
syntax within a single beat slot demonstrates sub-beat event packing (spec §8.2).

The walking bass uses chromatic approach tones (`Bb2→B2` approaching C, `Bb2→A2`
approaching A) — a core jazz bass technique written explicitly in .mmd since key
signatures are display-only.

```bash
python tools/mmd_validator.py   examples/jazz-turnaround.mmd
python tools/mmd_to_midi.py     examples/jazz-turnaround.mmd
python tools/mmd_to_lilypond.py examples/jazz-turnaround.mmd
python tools/mmd_transposer.py  examples/jazz-turnaround.mmd --transpose +2  # → D major
```
