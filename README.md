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

### Phase 2 — Transformation Toolchain ✅ Complete

**`tools/mmd_to_midi.py`** — Export to standard MIDI (midiutil). Multi-track, dynamics, transposition.  
**`tools/mmd_transposer.py`** — Transpose, invert, retrograde, augment, diminish. Zero dependencies.  
**`tools/mmd_to_lilypond.py`** — Convert to LilyPond `.ly` for PDF sheet music. Render with `lilypond score.ly`.

### Phase 3 — Reference Content

**`examples/`**
A library of 6–8 validated `.mmd` scores covering a range of styles: simple melody, two-hand piano, jazz chord comping, a lyric song, an SATB sketch, and at least one score that demonstrates a mathematical transformation (transposition or retrograde). Serves three purposes: few-shot material for LLM generation, regression tests for the transformation tools, and the content that every subsequent demo is built around. Nothing else in Phase 4 can be demoed without this.

**`prompts/mmd_prompts.md`**
Curated system prompts and few-shot templates for LLM `.mmd` generation. Covers the most common generation tasks (compose melody, harmonize, arrange for two hands, continue a phrase) and maps each common validator error to its root cause and fix — so an LLM receiving the JSON output can self-correct without additional guidance.

### Phase 4 — Demo Experience

*Goal: close the gap between "interesting format" and "I get it" to under 10 seconds.*

**`tools/mmd_player.html`**
Browser-based `.mmd` player using Tone.js. Paste a score, click play, hear it — no installation, no server. This is the primary demo artifact: the format and the sound are visible simultaneously, making the value proposition self-evident. Hostable on GitHub Pages as a shareable link.

**`demo/mmd_demo.ipynb`**
Colab-ready Jupyter notebook demonstrating the full AI loop: plain-English description → Claude generates `.mmd` → validator checks → MIDI plays in-browser. No local setup required. This is where the deeper story lives — that AI music generation can be held to a verifiable, correctable standard. Links to the Claude API and uses the examples from Phase 3 as few-shot context.

### Phase 5 — Interactive Editor

**`tools/mmd_editor/`**
A minimal web editor combining live validation feedback (validator runs on every keystroke) with the Phase 4 player for immediate playback. Targets users who want to write or edit `.mmd` directly rather than generate it via AI.

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

| Asset | License |
|-------|---------|
| `spec/musical-markdown-spec.md` | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — free to share, adapt, and implement for any purpose with attribution |
| `tools/`, `tests/` (all `.py` files) | [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) — includes explicit patent grant and patent retaliation clause |

© 2026 km-vibecoder. See `LICENSE` (tools) and `LICENSE-SPEC.md` (specification) for full terms.
