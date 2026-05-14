# Musical Markdown (.mmd)
### An AI-native music notation standard and toolchain

---

## Project Summary

Musical Markdown (`.mmd`) is a plain-text music notation format designed from the ground up for two equal audiences: **human editors** who need readable, writable ASCII music, and **AI systems** that need an unambiguous, mathematically operable data stream.

Traditional sheet music encodes pitch spatially (vertical staff position) and duration visually (notehead shape). Both require human pattern recognition and are hostile to programmatic manipulation. `.mmd` replaces these with two explicit strings per note — a pitch (`F#5`) and a duration fraction (`/8`) — embedded in a fixed beat-grid that any parser can slice without musical knowledge.

The format is under active development. The specification, validator, and test suite are complete. The rendering and transformation toolchain is the next build phase.

---

## Repository Structure

```
mmd/
├── MANIFEST.md                  # File-by-file description of every project asset
├── README.md                    # This file
│
├── spec/
│   └── musical-markdown-spec.md # The canonical language specification (v1.0 draft)
│
├── tools/
│   ├── mmd_validator.py         # Syntax validator / LLM spell-checker
│   ├── mmd_to_midi.py           # MIDI exporter (requires midiutil)
│   ├── mmd_transposer.py        # Transpose, invert, retrograde, augment, diminish
│   ├── mmd_to_lilypond.py       # LilyPond exporter for PDF sheet music
│   └── mmd_llm_workflow.md      # Guide: using the validator in LLM feedback loops
│
└── tests/
    └── test_mmd_validator.py    # 64-test validator test suite (stdlib unittest)
```

---

## Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Specification v1.0 | ✅ Complete | Covers full syntax, EBNF grammar, AI impl notes |
| Syntax validator | ✅ Complete | Zero deps, Python 3.9+, JSON + text output |
| Validator test suite | ✅ Complete | 64 tests, 100% passing |
| LLM workflow guide | ✅ Complete | 3 integration patterns with code |
| MIDI export | ✅ Complete | `mmd_to_midi.py` — midiutil, multi-track, dynamics |
| Sheet music render | ✅ Complete | `mmd_to_lilypond.py` — LilyPond .ly, multi-staff, PDF-ready |
| Transposition CLI | ✅ Complete | `mmd_transposer.py` — transpose, invert, retrograde, augment, diminish |
| Example library | 🔲 Planned | `examples/` — validated reference scores |
| LLM prompt library | 🔲 Planned | `mmd_prompts.md` — few-shot generation prompts |

---

## The Format in 60 Seconds

```mmd
@TITLE: Simple Study
@BPM: 120
@TIME: 4/4
@KEY: G

# Each T-track is a pitched instrument. Tracks play simultaneously.
# Format: PITCH OCTAVE / DURATION  (e.g. G4/4 = G in octave 4, quarter note)
# Semicolons separate beats. Bar lines use |
# Held notes get empty beat slots:  C4/1;;;|  (whole note = 4 slots, 3 held)

T1: G4/4; A4/4; B4/4; C5/4 | D5/2;    ; C5/4; B4/4 |.
T2: G3/1; ;    ;    ;       | G3/2;    ; D3/2;      |.
L1: Do  ; Re  ; Mi  ; Fa    | Sol ;    ; Fa  ; Mi   |.
```

**Key syntax rules:**
- `C4` = middle C, `A4` = 440 Hz. Octave number is always explicit.
- `/4` = quarter note, `/2` = half, `/1` = whole, `/8` = eighth. Denominators must be powers of 2.
- Every beat gets a slot. A sustained note fills its held slots with bare `;`.
- Commas separate subdivisions *within* a beat: `C4/8,D4/8` = two eighths in one beat.
- Whitespace is insignificant. Visual column alignment is cosmetic only.

Full syntax reference: `spec/musical-markdown-spec.md`

---

## Validator Quick Start

```bash
# Validate a file
python tools/mmd_validator.py score.mmd

# JSON output for LLM feedback loops
python tools/mmd_validator.py score.mmd --json

# Canonical (whitespace-free) form for diffing
python tools/mmd_validator.py score.mmd --normalize

# From stdin
echo "T1: C4/4;D4/4;E4/4;F4/4|" | python tools/mmd_validator.py -

# Run the test suite
python tests/test_mmd_validator.py
python tests/test_mmd_validator.py -v   # verbose
```

Exit codes: `0` = valid, `1` = errors, `2` = IO error.

---

## LLM Integration Pattern

The validator is designed to serve as a deterministic oracle in an LLM generate-validate-fix loop. LLMs have no `.mmd` training data, so first-pass output is often syntactically incorrect. The loop converges in 1–3 rounds:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  User request                                           │
│       │                                                 │
│       ▼                                                 │
│  LLM generates .mmd                                     │
│       │                                                 │
│       ▼                                                 │
│  mmd_validator.py --json  ──── valid? ──── YES ──► done │
│       │                                                 │
│      NO                                                 │
│       │                                                 │
│       ▼                                                 │
│  JSON errors fed back to LLM as next prompt             │
│       │                                                 │
│       └──────────────────────────────────────────────── │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

Each error object carries `track`, `measure`, `beat`, `message`, and `raw` — precise enough for the LLM to find and fix without re-reading the whole file. Full integration guide: `tools/mmd_llm_workflow.md`

---

## Roadmap

### Phase 2 — Transformation Toolchain

**`tools/mmd_transposer.py`**
CLI tool for mathematical operations on validated `.mmd` files. The fixed-grid structure makes these lossless:
- Key transposition (`--transpose +3`)
- Melodic inversion around an axis pitch (`--invert C4`)
- Retrograde (time-reversal of a phrase or track)
- Augmentation / diminution (doubling or halving all durations)
- Time-shift (move a track N beats forward, fill gaps with rests)

**`tools/mmd_to_midi.py`**
Export a validated `.mmd` file to a standard `.mid` file using the `midiutil` library. Maps the pitch/duration/dynamic model directly to MIDI note-on/note-off events with velocity. Supports multi-track output, tempo changes, and time signature metadata. This makes `.mmd` files audible without a dedicated player.

**`tools/mmd_to_lilypond.py`**
Convert `.mmd` to LilyPond (`.ly`) source for high-quality PDF sheet music rendering. LilyPond is the standard open-source music engraver. This provides the human-readable visual output path without building a custom renderer.

### Phase 3 — Content and Prompts

**`examples/`**
A library of validated `.mmd` reference scores covering common styles and structures: simple melody, two-hand piano, SATB vocal, jazz chord comping, a lyric song. These serve as few-shot examples for LLM generation and as regression tests for the transformation tools.

**`prompts/mmd_prompts.md`**
Curated system prompts and few-shot templates for LLM `.mmd` generation. Includes the specification excerpt, worked examples of the most common error patterns and their fixes, and task-specific prompt variants (compose melody, harmonize, arrange for two hands, continue a phrase).

### Phase 4 — Interactive Tools

**`tools/mmd_player.html`**
Browser-based `.mmd` player using the Web Audio API and/or Tone.js. Parse → synthesize directly in the browser. No server required.

**`tools/mmd_editor/`**
A minimal web editor with live validation feedback (validator runs on keystroke via WebAssembly or a local API endpoint) and playback.

---

## Design Decisions Log

| Decision | Rationale |
|----------|-----------|
| Semicolons as beat separators, not whitespace | Whitespace is insignificant; a parser needs an unambiguous token to count beats. Semicolons are visible in every code editor and survive copy-paste. |
| Mandatory held-beat placeholders | Makes the beat grid self-describing. A parser can determine measure length by counting semicolons without reading any duration values. |
| Measure-total duration validation (not per-slot) | Per-slot checks incorrectly reject valid multi-beat notes (whole notes, half notes) in their attack slot. Measure-total catches real errors — missing notes, wrong denominators — without false positives. |
| Scientific Pitch Notation with explicit octave | Eliminates clef ambiguity entirely. `C4` is always middle C regardless of context. |
| Power-of-2 denominators only | Enables exact rational duration arithmetic with no floating-point edge cases. Tuplets are handled as named blocks (`[TRP]`) rather than fractional denominators. |
| Whitespace insignificant | Allows human authors to align tracks visually without the alignment becoming load-bearing. LLMs should not infer structure from spacing. |
| JSON validator output | Error objects with `track`/`measure`/`beat` coordinates are directly consumable by an LLM as a structured correction prompt, without natural-language parsing. |

---

## Contributing

This project is in active design. The specification is the source of truth — changes to validator behavior should be preceded by a spec update. When adding a new syntactic feature:

1. Add the syntax to `spec/musical-markdown-spec.md`
2. Add acceptance tests to `tests/test_mmd_validator.py`
3. Implement validation in `tools/mmd_validator.py`
4. Confirm `python tests/test_mmd_validator.py` passes
5. Update `MANIFEST.md` if new files are added

---

## License

TBD — to be determined by project owner before public release.
