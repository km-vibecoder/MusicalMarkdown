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

*More examples coming in Phase 3: two-hand piano, jazz chord comping,
transformation showcase (transposition / retrograde side-by-side).*
