# Musical Markdown (.mmd) — Project File Manifest
### Version 1.0 Draft

---

## Files

### `musical-markdown-spec.md`
**The language specification.**
The canonical reference document for the .mmd standard. Covers the full syntax from first principles: Scientific Pitch Notation, the duration system, beat anchors and held-beat placeholders, chords, ties, slurs, tuplets, grace notes, parenthetical modifiers (dynamics, articulation, ornaments, pedal, bowing), global command blocks (tempo, time/key signature, dynamics, transposition, clef), repeat structures, lyric tracks, multi-track synchronization, and dual-voice notation. Includes a formal EBNF grammar, a complete examples section, implementation notes for AI parsers, and a quick-reference card. The spec establishes the two foundational rules that drive all validation: every measure in every track must contain exactly `(beats_per_measure − 1)` semicolons, and the sum of all note durations in a measure must equal the measure's total length in quarter-note units.

---

### `mmd_validator.py`
**The syntax validator / spell-checker.**
A zero-dependency Python 3.9+ command-line tool that parses and validates .mmd files against the spec. Reads from a file path or stdin; outputs a human-readable report (default) or structured JSON (`--json`). JSON output is designed as a direct LLM feedback payload — every error carries `track`, `measure`, `beat`, `message`, and `raw` fields so an LLM can locate and fix the exact offending token. Also provides a `--normalize` flag that strips all insignificant whitespace to produce a canonical form suitable for diffing two versions. Exit codes: `0` = valid, `1` = errors found, `2` = IO error.

**Validates:**
- Semicolon count per measure (beat-slot grid structure)
- Measure-total duration (all note durations must sum to the time signature length)
- Beat-slot subdivision overfill (comma-separated subdivisions must fit in one beat)
- Note token syntax (pitch class, accidental, octave, power-of-2 denominator, dots)
- Rest token syntax (`R/N`, `R/N.`, `R/M`)
- Chord token syntax (pitch list, shared duration, optional inversion)
- Duration inheritance (first note in a measure must carry an explicit duration)
- Global command block syntax (`[BPM]`, `[TIME]`, `[KEY]`, `[DYN]`, `[XPOSE]`, `[CLEF]`, etc.)
- Header field syntax (`@BPM`, `@TIME`, `@KEY`)
- Cross-track measure-count consistency (all T-prefix tracks must have equal measure counts)

**Usage:**
```bash
python tools/mmd_validator.py score.mmd              # human-readable report
python tools/mmd_validator.py score.mmd --json       # JSON for LLM feedback loops
python tools/mmd_validator.py score.mmd --normalize  # canonical whitespace-free form
echo "T1: C4/4;D4/4;E4/4;F4/4|" | python tools/mmd_validator.py -
```

---

### `test_mmd_validator.py`
**The validator test suite.**
64 unit tests organized into 8 test classes that verify the validator accepts all valid .mmd constructs and correctly rejects all known error patterns. Serves two purposes: regression protection when the validator is extended, and a readable catalog of valid vs. invalid .mmd examples that can be used as few-shot material in LLM prompts.

**Test classes:**
| Class | What it covers |
|-------|---------------|
| `TestValidFiles` | Baseline acceptance — all valid constructs must pass |
| `TestSemicolonErrors` | Wrong beat-slot counts, missing held-beat placeholders |
| `TestDurationSumErrors` | Overfilled/underfilled beat slots and measures |
| `TestNoteSyntaxErrors` | Bad pitch class, missing octave, bad/non-power-of-2 denominators |
| `TestRestErrors` | Malformed rest tokens |
| `TestChordErrors` | Invalid chord pitches and denominators |
| `TestHeaderErrors` | Bad `@BPM`, `@TIME`, `@KEY` values |
| `TestCommandErrors` | Invalid `[DYN]`, `[XPOSE]`, `[CLEF]` arguments |
| `TestCrossTrackErrors` | Mismatched measure counts across T-tracks |
| `TestNormalize` | Canonical form output |
| `TestDurationInheritance` | Edge cases for implicit duration carry-forward |

**Run:**
```bash
python tests/test_mmd_validator.py        # summary
python tests/test_mmd_validator.py -v     # verbose (one line per test)
```

---

### `mmd_llm_workflow.md`
**The LLM integration guide.**
Explains how to use the validator as the ground-truth oracle in a generate-validate-fix loop, eliminating the imprecision that comes from an LLM writing a novel format with no training examples. Covers three integration patterns: a single-turn API loop with Python pseudocode, an interactive chat workflow with copy-paste prompt templates, and a fully automated bash pipeline for Claude Code. Includes a "Common Error Patterns" section that maps each validator error message to its root cause and a concrete before/after fix — written so that an LLM receiving the validator's JSON output can interpret and correct the error without additional explanation.

---

## Dependency Map

```
musical-markdown-spec.md
    ↓ defines the rules that
mmd_validator.py implements
    ↓ tested by
test_mmd_validator.py
    ↓ used as described in
mmd_llm_workflow.md
```

The spec is the source of truth. The validator is an executable encoding of the spec's rules. The tests are the contract between the two. The workflow guide is the operational layer that connects all three to an LLM.

---

### `mmd_to_midi.py`
**The MIDI exporter.**
Converts a validated `.mmd` file to a standard `.mid` file using `midiutil`. Runs the validator as a pre-check by default (exit 3 on failure). Parses pitch, duration, duration-inheritance, dots, chords, ties, rests (including R/M), dynamics (→ MIDI velocity), XPOSE transposition, inline [BPM] and [TIME] command blocks, and multi-track scores. Lyric (L), percussion (P), and chord-symbol (C) tracks are silently skipped.

**Usage:**
```bash
python tools/mmd_to_midi.py score.mmd              # writes score.mid
python tools/mmd_to_midi.py score.mmd -o out.mid   # explicit output path
python tools/mmd_to_midi.py score.mmd --no-validate  # skip validator pre-check
echo "T1: C4/4;D4/4;E4/4;F4/4|" | python tools/mmd_to_midi.py -  # stdin
```

Exit codes: `0` = success, `1` = parse/MIDI error, `2` = IO error, `3` = validation failure.
Requires: `midiutil` (`pip install midiutil` or use the project `.venv`).

---

### `mmd_transposer.py`
**The mathematical transformation tool.**
Applies spec §21.2 operations to a validated `.mmd` file, outputting a new `.mmd`. All operations can be chained and optionally scoped to specific tracks with `--track T1,T2`.

| Operation | Flag | What it does |
|-----------|------|-------------|
| Transposition | `--transpose +N` | Shift all pitches N semitones; sharps used for output |
| Inversion | `--invert C4` | Mirror pitches around an axis pitch |
| Retrograde | `--retrograde` | Reverse measure order + within-measure note order |
| Augmentation | `--augment` | Double note durations (`/4 → /2`); updates `@TIME` denominator |
| Diminution | `--diminish` | Halve note durations (`/4 → /8`); updates `@TIME` denominator |

Handles notes, chords, tied notes, grace notes, rests, and inline command blocks. Runs the validator before and after by default (exit 3 on pre-validation failure).

**Usage:**
```bash
python tools/mmd_transposer.py score.mmd --transpose +5
python tools/mmd_transposer.py score.mmd --invert C4
python tools/mmd_transposer.py score.mmd --retrograde
python tools/mmd_transposer.py score.mmd --augment
python tools/mmd_transposer.py score.mmd --diminish
python tools/mmd_transposer.py score.mmd --transpose +3 --track T1,T2
python tools/mmd_transposer.py score.mmd --transpose +2 --augment   # chained
python tools/mmd_transposer.py score.mmd --transpose +5 -o out.mmd
```

Exit codes: `0` = success, `1` = transform error, `2` = IO error, `3` = validation failure.
Zero external dependencies (stdlib only).

---

### `mmd_to_lilypond.py`
**The LilyPond sheet music exporter.**
Converts a validated `.mmd` file to a LilyPond `.ly` source file for high-quality PDF sheet music rendering. Render the output with `lilypond score.ly`.

**Supports:** notes (SPN → LilyPond pitch with correct sharp/flat spelling), dotted durations, duration inheritance, rests (including R/M full-measure), chords (`<...>`), ties (`~`), grace notes (`\acciaccatura` / `\appoggiatura`), dynamics (`\mf`, `\f`, etc.), staccato/accent articulations, multi-staff output (one `\new Staff` per T-track), clef hints from `[CLEF:...]`, inline `[BPM]` / `[TIME]` / `[KEY]` / `[DYN]` / `[XPOSE]` commands, `@TITLE` / `@COMPOSER` / `@ARRANGER` / `@TRACKS` header fields.

**Not yet:** tuplets, slurs, repeats with volta brackets, dual-voice `//`.

**Usage:**
```bash
python tools/mmd_to_lilypond.py score.mmd              # writes score.ly
python tools/mmd_to_lilypond.py score.mmd -o out.ly    # explicit path
lilypond score.ly                                       # → score.pdf + score.midi
```

Exit codes: `0` = success, `1` = parse error, `2` = IO error, `3` = validation failure.
Zero external dependencies (stdlib only).

---

## Suggested Next Files

| Filename | Purpose |
|----------|---------|
| `mmd_examples/` | A library of validated reference scores in common styles |
| `mmd_prompts.md` | Curated system prompts and few-shot examples for LLM .mmd generation |
