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

*More examples coming in Phase 3: jazz chord comping,
transformation showcase (transposition / retrograde side-by-side).*
