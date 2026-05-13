# Musical Markdown (.mmd) — Language Specification
### Version 1.0 Draft

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [File Structure](#2-file-structure)
3. [Header Block](#3-header-block)
4. [Track Declarations](#4-track-declarations)
5. [Scientific Pitch Notation](#5-scientific-pitch-notation)
6. [Duration System](#6-duration-system)
7. [Rests](#7-rests)
8. [Beat Anchors and Bar Lines](#8-beat-anchors-and-bar-lines)
9. [Chords](#9-chords)
10. [Ties and Slurs](#10-ties-and-slurs)
11. [Tuplets](#11-tuplets)
12. [Grace Notes](#12-grace-notes)
13. [Parenthetical Modifiers](#13-parenthetical-modifiers)
14. [Global Command Blocks](#14-global-command-blocks)
15. [Repeat Structures](#15-repeat-structures)
16. [Lyric Tracks](#16-lyric-tracks)
17. [Multi-Track Synchronization](#17-multi-track-synchronization)
18. [Comments and Annotations](#18-comments-and-annotations)
19. [Formal Grammar (EBNF)](#19-formal-grammar-ebnf)
20. [Complete Examples](#20-complete-examples)
21. [Implementation Notes for AI](#21-implementation-notes-for-ai)
22. [Quick Reference Card](#22-quick-reference-card)

---

## 1. Design Philosophy

Musical Markdown (.mmd) is a **logic-first, linear, ASCII-based** notation standard designed for two equal audiences: **human editors** who need readable plaintext music, and **AI systems** that need an unambiguous, mathematically operable stream of musical data.

### Core Principles

| Principle | Implication |
|-----------|-------------|
| **Temporal linearity** | Music flows left-to-right exactly as it is performed. No vertical stacking of simultaneous information (except within chord brackets). |
| **Explicit over implicit** | Every pitch includes its octave. Every note includes its duration. Nothing is inferred from context or position. |
| **Fixed-grid parsing** | Bar lines `\|` and beat anchors `;` create a regular, predictable structure. A parser can slice the file into a 2D grid of [measure × beat] without musical knowledge. |
| **Layered complexity** | A minimal valid note is `C4/4`. Modifiers, dynamics, and ornaments are additive layers that append to — never replace — the core pitch-duration token. |
| **Human-readable defaults** | Common cases are terse. A simple melody requires no header, no track declarations, and no global commands. |

### What .mmd Replaces

Traditional sheet music encodes pitch spatially (vertical position on a staff) and duration visually (notehead fill, stem, flag count). Both dimensions require human pattern recognition. .mmd collapses these into **two explicit strings** per note: a pitch string (`C#4`) and a duration fraction (`/4`), separated by nothing — `C#4/4`.

---

## 2. File Structure

A .mmd file is divided into three sections, all optional except the track body:

```
[HEADER BLOCK]          ← optional metadata
[TRACK DECLARATIONS]    ← optional named track definitions
[TRACK BODIES]          ← the music itself; at least one required
```

Sections are separated by blank lines. The parser identifies each line by its prefix character or bracket type.

### Line Types

| Prefix / Pattern | Type |
|-----------------|------|
| `---` | Section separator (cosmetic only) |
| `#` | Comment / annotation |
| `@KEY:VALUE` | Header field |
| `[COMMAND]` | Global command block |
| `Tn:` | Music track line (n = integer) |
| `Ln:` | Lyric track line |
| `Pn:` | Percussion track line |
| *(no prefix)* | Continuation of previous track line (for long scores) |

---

## 3. Header Block

The header block opens the file and provides global metadata. All fields are optional. Header fields use `@` prefix and `KEY:VALUE` syntax.

```
@TITLE: Moonlight Sonata — Excerpt
@COMPOSER: Ludwig van Beethoven
@ARRANGER: Jane Smith
@BPM: 54
@TIME: 4/4
@KEY: C#m
@TRACKS: T1=Right Hand, T2=Left Hand
@VERSION: 1.0
@LICENSE: CC-BY 4.0
@NOTE: Transcribed from the 1802 first edition.
```

### Standard Header Fields

| Field | Value Format | Description |
|-------|-------------|-------------|
| `@TITLE` | Free text | Title of the piece |
| `@COMPOSER` | Free text | Original composer |
| `@ARRANGER` | Free text | Arranger (if applicable) |
| `@BPM` | Integer | Initial tempo in beats per minute |
| `@TIME` | `n/n` | Initial time signature |
| `@KEY` | See §5.3 | Initial key signature |
| `@TRACKS` | `Tn=label, ...` | Human-readable track labels |
| `@VERSION` | `n.n` | .mmd spec version this file targets |
| `@LICENSE` | Free text | Copyright or license information |
| `@NOTE` | Free text | Freeform annotation |

---

## 4. Track Declarations

Tracks are the primary structural unit. Each music line begins with a **track prefix** — a letter followed by a channel number and a colon.

### Built-in Track Types

| Prefix | Type | Description |
|--------|------|-------------|
| `T` | Tone track | Pitched melodic or harmonic content |
| `L` | Lyric track | Text synchronized to a tone track |
| `P` | Percussion track | Unpitched rhythmic content |
| `C` | Chord symbol track | Roman numeral or lead-sheet chord symbols |

Track numbers start at `1`. `T1` is the default track if no prefix is given.

```
T1: C4/4; E4/4; G4/4; C5/4 |
T2: C3/1                    |
L1: Hel- ; lo  ; world; .   |
```

### Track Continuation

Long tracks can be broken across multiple lines with a continuation indent (two spaces):

```
T1: C4/4; E4/4; G4/4; C5/4 | D4/4; F4/4; A4/4; D5/4 |
  | E4/4; G4/4; B4/4; E5/4 | C4/1                    |
```

The `|` at the start of a continuation line signals that this line continues the track immediately above it.

---

## 5. Scientific Pitch Notation

Every pitched note is written in **Scientific Pitch Notation (SPN)**: a pitch class followed by an octave number.

### 5.1 Pitch Classes

```
C  C#  D  D#  E  F  F#  G  G#  A  A#  B
   Db     Eb        Gb     Ab     Bb
```

Both sharp (`#`) and flat (`b`) accidentals are accepted. Double accidentals use `##` and `bb`.

A natural sign, used to cancel a key signature accidental, is written with `n`: `Cn4` means C-natural in octave 4.

### 5.2 Octave Numbers

Octave numbers follow MIDI/scientific convention:

| Octave | Range | Common Name |
|--------|-------|-------------|
| `0` | C0–B0 | Sub-contra |
| `1` | C1–B1 | Contra |
| `2` | C2–B2 | Great |
| `3` | C3–B3 | Small |
| `4` | C4–B4 | One-line (Middle C = C4) |
| `5` | C5–B5 | Two-line |
| `6` | C6–B6 | Three-line |
| `7` | C7–B7 | Four-line |
| `8` | C8 | Five-line (top of piano) |

Middle C is always `C4`. The A above middle C (concert A, 440 Hz) is `A4`.

### 5.3 Key Signatures

Key signatures are declared in the header (`@KEY`) or inline via `[KEY:...]` command blocks. They affect **display** and **transposition** operations but do **not** alter explicit accidentals in the note stream. An AI must always honor the written pitch, not infer a key-adjusted pitch.

**Major keys:** `C`, `G`, `D`, `A`, `E`, `B`, `F#`, `C#`, `F`, `Bb`, `Eb`, `Ab`, `Db`, `Gb`, `Cb`  
**Minor keys:** append lowercase `m` — `Am`, `Em`, `Bm`, `F#m`, `C#m`, `Gm`, `Dm`, `Cm`, etc.

---

## 6. Duration System

Duration is written as a **forward slash followed by a denominator** appended directly to the pitch string, with no space.

```
C4/1   → whole note       (4 beats in 4/4)
C4/2   → half note        (2 beats)
C4/4   → quarter note     (1 beat)
C4/8   → eighth note      (½ beat)
C4/16  → sixteenth note   (¼ beat)
C4/32  → thirty-second note
C4/64  → sixty-fourth note
```

### 6.1 Dotted Notes

A single dot appended after the denominator adds half the note's value. A double dot adds three-quarters.

```
C4/4.   → dotted quarter   (1.5 beats)
C4/4..  → double-dotted quarter (1.75 beats)
C4/2.   → dotted half      (3 beats)
```

### 6.2 Duration Arithmetic

Parsers compute a note's beat-duration as:

```
base     = 4 / denominator          (in quarter-note units)
dotted   = base × 1.5
d.dotted = base × 1.75
```

Examples:

| Token | Beat Duration (in ♩) |
|-------|----------------------|
| `C4/1` | 4.0 |
| `C4/2` | 2.0 |
| `C4/2.` | 3.0 |
| `C4/4` | 1.0 |
| `C4/4.` | 1.5 |
| `C4/8` | 0.5 |
| `C4/8.` | 0.75 |
| `C4/16` | 0.25 |

### 6.3 Duration Inheritance

As a shorthand for repeated durations, a note may **omit** its duration if it is identical to the previous note's duration in the same track. The parser carries the last explicit duration forward.

```
# These two lines are equivalent:
T1: C4/4; D4/4; E4/4; F4/4 |
T1: C4/4; D4; E4; F4       |
```

Duration inheritance resets at every bar line and is **not** carried across tracks.

---

## 7. Rests

Rests use the token `R` followed by a duration. They accept all the same duration rules as pitched notes, including dots and inheritance.

```
R/1    → whole rest
R/2    → half rest
R/4    → quarter rest
R/4.   → dotted quarter rest
R/8    → eighth rest
```

Full-measure rests for any time signature use `R/M`:

```
T1: R/M |    # one full measure rest, regardless of time signature
```

---

## 8. Beat Anchors and Bar Lines

### 8.1 Bar Lines

A single pipe `|` marks the end of a measure:

```
T1: C4/4; D4/4; E4/4; F4/4 | G4/4; A4/4; B4/4; C5/4 |
```

A **double bar line** uses `||`:

```
T1: C4/1 | D4/1 || E4/1 |    # section boundary
```

A **final bar line** uses `|.`:

```
T1: C4/1 | D4/1 |.
```

### 8.2 Beat Anchors

Semicolons `;` are **mandatory beat separators** within a measure. They must appear at every beat boundary regardless of note durations, creating a fixed-count grid that is independent of the pitches or durations written in it.

In `4/4` time, every measure contains exactly **three** semicolons (four beat slots, three boundaries):

```
T1: C4/4; D4/4; E4/4; F4/4 |
```

In `3/4` time, every measure contains exactly **two** semicolons:

```
T1: C4/4; D4/4; E4/4 |
```

**Subdivision rule:** When a beat is subdivided (e.g., two eighth notes fill one quarter-note beat), they share a single beat slot and are separated by a comma:

```
# Beat 1 = two eighth notes, Beat 2 = quarter, Beat 3 = quarter, Beat 4 = quarter
T1: C4/8,D4/8; E4/4; F4/4; G4/4 |
```

This ensures every semicolon is a **beat boundary** and every comma is a **subdivision boundary**, giving parsers a two-level rhythmic grid.

### 8.3 Held-Beat Placeholders

When a single note spans more than one beat (a half note, whole note, dotted value, etc.), the beats it occupies beyond its attack point are written as **empty beat slots** — a bare semicolon with no token. This is mandatory. It ensures every measure in every track contains the same number of semicolons and that the grid can be read column-by-column without consulting duration values.

```
# In 4/4: a whole note fills all four beats.
# Beat 1 = attack; Beats 2, 3, 4 = held (empty slots).
T1: C3/1; ; ;  |

# A half note fills beats 1–2; a half note fills beats 3–4.
T2: C4/2; ; A3/2; |
#          ^--- beat 2 held from C4/2

# Four quarter notes — no held slots needed.
T3: C5/4; D5/4; E5/4; F5/4 |
```

The rule is: **the number of semicolons in a measure must equal (beats per measure − 1) for every track, without exception.** A parser counting semicolons can verify measure length before reading any durations.

Empty slots may optionally contain a single space for visual clarity, but this is cosmetic. `; ;` and `;;` are parsed identically.

### 8.4 Whitespace Rules

**Whitespace (spaces and tabs) is insignificant in .mmd and is ignored by all parsers.** It may be used freely to align tracks visually into a human-readable column grid, but it carries no musical meaning and must not be required for correct parsing.

```
# These three lines are musically identical:
T1: C4/4;D4/4;E4/4;F4/4|
T1: C4/4; D4/4; E4/4; F4/4 |
T1: C4/4 ;  D4/4 ;  E4/4 ;  F4/4  |
```

The only tokens where whitespace is **prohibited** are within a single note token, chord bracket, or command block: `C 4/4`, `[C4, E4]`, and `[BPM: 120]` are all invalid. A space may not appear inside a token — only between tokens.

**Recommended style:** When writing multi-track scores, authors are encouraged (but not required) to align corresponding beat slots into visual columns by padding with spaces. This produces a temporal grid that is readable at a glance:

```
T1: C5/4; B4/4; A4/4; G4/4 | F4/1;   ;   ;   |
T2: C4/2;     ; A3/2;       | F3/2;   ; G3/2; |
T3: C3/1;     ;     ;       | F2/1;   ;   ;   |
```

An AI parser must produce identical results whether or not this alignment is present.

### 8.5 Grid Invariant

The beat-anchor invariant states: **the sum of durations between any two adjacent semicolons (or between a bar line and the first semicolon, or between the last semicolon and the following bar line) must equal exactly one beat as defined by the time signature denominator.** Empty slots (§8.3) are not summed; they contribute zero duration.

A parser should validate this and report the measure number and beat position of any violation.

---

## 9. Chords

Simultaneous pitches are grouped in **square brackets**, separated by commas, followed by a single shared duration:

```
[C4,E4,G4]/4       → C major chord, quarter note
[D4,F#4,A4]/2      → D major chord, half note
[C4,Eb4,G4,Bb4]/4  → Cm7 chord, quarter note
```

Modifiers apply to the entire chord:

```
[C4,E4,G4]/4(f)(.)   → loud, staccato C major chord
```

### 9.1 Chord Inversions

Inversions are noted with a slash and the bass note after the closing bracket:

```
[C4,E4,G4]/4/E    → C major, first inversion (E in bass)
[C4,E4,G4]/4/G    → C major, second inversion (G in bass)
```

The bass note is a pitch class only (no octave); the actual voicing is determined by the notated pitches.

### 9.2 Arpeggio

An arpeggiated chord uses the `(arp)` modifier. Direction defaults to upward; use `(arp^)` for explicit upward and `(arpv)` for downward:

```
[C3,E3,G3,C4]/2(arp)    → arpeggiate upward
[C4,G3,E3,C3]/2(arpv)   → arpeggiate downward
```

---

## 10. Ties and Slurs

### 10.1 Ties

A tie connects two notes of the same pitch, extending duration across a beat anchor or bar line. Use `~` between the two note tokens:

```
T1: C4/4~C4/4; D4/4; E4/4; F4/4 |
# C4 sounds for 2 beats total (tied across beat 1–2)

T1: C4/2 | ~C4/4; D4/4 |
# C4 sounds for 3 beats total (tied across a bar line)
```

The second note in a tie must be the same pitch and octave. Its duration is added to the first without re-articulation.

### 10.2 Slurs

A slur indicates legato connection across a group of different pitches. Slurred groups are wrapped in `<` and `>`:

```
T1: <C4/4; D4/4; E4/4>; F4/4 |
```

Slurs do not affect duration; they are performance/phrasing instructions. Slurs may span bar lines:

```
T1: <C4/4; D4/4 | E4/4; F4/4> |
```

Nested slurs are not permitted. Ties within slurs are permitted.

---

## 11. Tuplets

A tuplet block groups notes that collectively fill a duration they would not normally fit. The syntax is:

```
[TUP:actual:normal] ... [/TUP]
```

Where `actual` is the number of notes played and `normal` is the number of notes the block fills.

```
# Triplet: 3 eighth notes in the time of 2 (one quarter beat)
[TUP:3:2] C4/8, D4/8, E4/8 [/TUP]

# Quintuplet: 5 sixteenth notes in the time of 4
[TUP:5:4] C4/16, D4/16, E4/16, F4/16, G4/16 [/TUP]
```

### Common Tuplet Shorthand

| Shorthand | Equivalent | Name |
|-----------|------------|------|
| `[TRP]...[/TRP]` | `[TUP:3:2]...[/TUP]` | Triplet |
| `[QNT]...[/QNT]` | `[TUP:5:4]...[/TUP]` | Quintuplet |
| `[SPT]...[/SPT]` | `[TUP:7:4]...[/TUP]` | Septuplet |

Full example in context:

```
T1: [TRP] C4/8, E4/8, G4/8 [/TRP]; A4/4; G4/4 |
#     ^--- fills one quarter-note beat ----------^
```

---

## 12. Grace Notes

Grace notes are **ornamental, unmetered** notes that precede a principal note. They consume no beat time from the grid. Grace notes are enclosed in `{}` and placed immediately before the principal note:

```
{B3/16}C4/4    → single grace note (acciaccatura — crushed note)
{A3/16,B3/16}C4/4   → two grace notes
```

An **appoggiatura** (a grace note that leans into the beat and borrows time from the principal) is marked with `{` and `!`:

```
{!B3/8}C4/4   → appoggiatura: B3 takes an eighth note's worth of time from C4
```

---

## 13. Parenthetical Modifiers

Parenthetical modifiers append performance instructions directly to a note, chord, or group token. Multiple modifiers stack left-to-right with no separator. They are always placed **after** the duration (and after any tie connector):

```
C4/4(f)(.)     → forte, staccato
[C4,E4,G4]/2(ff)(>)   → fortissimo, marcato chord
```

### 13.1 Dynamic Modifiers

| Token | Meaning | Approximate dB |
|-------|---------|----------------|
| `(ppp)` | pianississimo | very very very soft |
| `(pp)` | pianissimo | very very soft |
| `(p)` | piano | soft |
| `(mp)` | mezzo-piano | medium soft |
| `(mf)` | mezzo-forte | medium loud |
| `(f)` | forte | loud |
| `(ff)` | fortissimo | very loud |
| `(fff)` | fortississimo | very very loud |
| `(+)` | forte (shorthand) | loud (alias for `(f)`) |
| `(-)` | piano (shorthand) | soft (alias for `(p)`) |

### 13.2 Articulation Modifiers

| Token | Name | Description |
|-------|------|-------------|
| `(.)` | Staccato | Short, detached |
| `(..)` | Staccatissimo | Very short, very detached |
| `(-)` | Tenuto | Held full value, slight emphasis |
| `(^)` | Accent | Standard accent |
| `(>)` | Marcato | Strong accent |
| `(~)` | Vibrato | Apply vibrato |
| `(0)` | Open | Open string / open horn |
| `(+)` | Stopped | Stopped horn / left-hand pizzicato |
| `(o)` | Harmonic | Natural harmonic |
| `(/)` | Glissando up | Slide upward to next note |
| `(\\)` | Glissando down | Slide downward to next note |
| `(snap)` | Snap pizzicato | Bartók pizzicato |

> **Disambiguation note:** `(+)` and `(-)` serve dual roles. When appearing alongside a dynamic context (e.g., `C4/4(+)` alone), they mean forte/piano. When combined with an explicit dynamic token (e.g., `C4/4(f)(+)`), `(+)` reverts to its articulation meaning (stopped). Parsers should resolve ambiguity by checking whether a dynamic modifier has already been specified for that token.

### 13.3 Ornament Modifiers

| Token | Name | Description |
|-------|------|-------------|
| `(tr)` | Trill | Rapid alternation with the note above |
| `(tr-)` | Trill (whole step) | Trill with a whole step |
| `(tr+)` | Trill (half step) | Trill with a half step |
| `(m)` | Mordent | Single alternation with note below |
| `(mu)` | Upper mordent (Pralltriller) | Single alternation with note above |
| `(t)` | Turn | Four-note figure around the main note |
| `(ti)` | Inverted turn | Inverted four-note figure |

### 13.4 Pedal Modifiers (Piano)

| Token | Description |
|-------|-------------|
| `(ped)` | Depress sustain pedal |
| `(ped*)` | Release sustain pedal |
| `(sost)` | Depress sostenuto pedal |
| `(sost*)` | Release sostenuto pedal |
| `(una)` | Una corda (soft pedal on) |
| `(tre)` | Tre corde (soft pedal off) |

### 13.5 String/Bow Modifiers

| Token | Description |
|-------|-------------|
| `(up)` | Up-bow |
| `(dn)` | Down-bow |
| `(sul)` | Sul ponticello (near bridge) |
| `(ord)` | Ordinario (normal) |
| `(col)` | Col legno (with bow wood) |
| `(pizz)` | Pizzicato |
| `(arco)` | Return to arco |

---

## 14. Global Command Blocks

Global commands are enclosed in square brackets and affect the tracks that follow them. They are placed **on their own line** or **inline within a track line**.

### 14.1 Tempo

```
[BPM:120]              → set tempo to 120 BPM
[BPM:♩=120]            → explicit quarter-note = 120 (unambiguous in compound meters)
[BPM:♩.=80]            → dotted quarter = 80 (common in 6/8)
[TEMPO:accel]          → begin accelerando (gradual speed increase)
[TEMPO:rit]            → ritenuto (gradual slowdown)
[TEMPO:rall]           → rallentando (gradual slowdown)
[TEMPO:ato]            → a tempo (return to original tempo)
[TEMPO:accel:4]        → accelerando over 4 measures
[TEMPO:rit:2]          → ritenuto over 2 measures
[TEMPO:rubato]         → free tempo (interpretive)
```

### 14.2 Time Signature

```
[TIME:4/4]     → common time
[TIME:3/4]     → waltz time
[TIME:6/8]     → compound duple
[TIME:5/4]     → quintuple meter
[TIME:7/8]     → irregular septuple
[TIME:C]       → common time symbol (= 4/4)
[TIME:C|]      → cut time symbol (= 2/2)
```

A time signature change applies from the **next measure** forward.

### 14.3 Key Signature

```
[KEY:C]        → C major / A minor (no sharps/flats)
[KEY:G]        → G major / E minor (1 sharp)
[KEY:Bb]       → Bb major / G minor (2 flats)
[KEY:F#m]      → F# minor (3 sharps)
[KEY:none]     → atonal / no key signature
```

Key changes apply from the **next measure** forward.

### 14.4 Global Dynamics

```
[DYN:pp]       → set dynamic level to pp
[DYN:mp]       → set dynamic level to mp
[DYN:f]        → set dynamic level to f
[CRESC:4]      → crescendo over 4 measures (from current to next explicit dynamic)
[DIM:2]        → diminuendo over 2 measures
[CRESC:4:p:f]  → crescendo over 4 measures, explicitly from p to f
[DIM:2:ff:mp]  → diminuendo over 2 measures, from ff to mp
[SFZ]          → sforzando on next note
[FP]           → forte-piano on next note
```

### 14.5 Transposition

```
[XPOSE:+3]     → transpose all following notes up 3 semitones
[XPOSE:-5]     → transpose down 5 semitones
[XPOSE:0]      → cancel transposition (return to concert pitch)
[XPOSE:T1:+3]  → transpose only Track 1 up 3 semitones
```

Transposition commands are a primary AI operation target — they modify the pitch stream mathematically without altering rhythm, dynamics, or structure.

### 14.6 Clef (Display Hint)

Clef declarations are **display-only hints** for rendering software. They do not affect pitch values.

```
[CLEF:T1:treble]    → treble clef on Track 1
[CLEF:T2:bass]      → bass clef on Track 2
[CLEF:T1:alto]      → alto clef on Track 1
[CLEF:T1:tenor]     → tenor clef on Track 1
[CLEF:T1:treble8vb] → treble clef sounding an octave lower (guitar)
```

### 14.7 Miscellaneous

```
[CAPO:3]            → capo on fret 3 (guitar; sounding pitch is already adjusted in notes)
[8VA]               → begin ottava alta (notes sound an octave higher)
[8VB]               → begin ottava bassa (notes sound an octave lower)
[8VA*]              → end 8va
[8VB*]              → end 8vb
[15MA]              → begin quindicesima (two octaves higher)
[15MA*]             → end 15ma
[SECT:Verse 1]      → section label (display annotation)
[SECT:Chorus]       → section label
[FINE]              → marks the end point (used with D.C./D.S.)
[DC]                → Da Capo (return to beginning)
[DS]                → Dal Segno (return to sign)
[SIGN]              → place segno marker (𝄋)
[CODA]              → place coda marker (𝄌)
[TOCODA]            → jump to coda
```

---

## 15. Repeat Structures

### 15.1 Repeat Barlines

```
|:   → begin repeat
:|   → end repeat
|: ... :|   → repeat the enclosed section once (play twice total)
```

A multiplier `[REP:xN]` immediately after `:|` specifies N total plays:

```
|: C4/4; D4/4; E4/4; F4/4 :| [REP:x3]   → play 3 times total
```

### 15.2 Volta Brackets (First/Second Endings)

Volta brackets mark alternate endings. They are declared as inline command blocks:

```
T1: |: C4/4; D4/4; E4/4 [VOLTA:1] F4/4 :| [VOLTA:2] G4/4 |.
```

`[VOLTA:n]` begins ending n. The repeat jumps back to `|:`, skips `[VOLTA:1]` on the second pass, and plays `[VOLTA:2]` instead.

Multiple voltas are supported:

```
[VOLTA:1]  ... [VOLTA:2]  ... [VOLTA:3]
```

### 15.3 Named Repeat Blocks

For complex or non-adjacent repeats, named blocks may be used:

```
[BLK:A] C4/4; D4/4; E4/4; F4/4 [/BLK:A]
[BLK:B] G4/4; A4/4; B4/4; C5/4 [/BLK:B]

[FORM: A A B A]    → play block A, then A again, then B, then A
```

The `[FORM:]` command defines playback order using block names. This is particularly useful for AI-driven arrangement tasks.

---

## 16. Lyric Tracks

Lyric tracks (`Ln:`) are synchronized to tone tracks beat-for-beat. Each lyric syllable or word occupies the same beat slot (semicolon position) as its corresponding note. Syllable breaks within a word are marked with `-`.

```
T1: C4/4;  D4/4;  E4/4;  F4/4 |
L1: Twink-; le   ; twink-; le  |
```

### 16.1 Lyric Rules

- A syllable that extends across multiple beats leaves its subsequent beat slots **empty** (just a semicolon with no text, or a `_` placeholder).
- Melismas (multiple notes per syllable) are indicated by `_` in the beat slots after the syllable's first appearance.
- A rest in the melody corresponds to `%` (beat rest) or ` ` (space/empty) in the lyric track.
- Punctuation follows the word, not the syllable: `love,` not `lo-,ve`.

```
T1: C4/4;   D4/4; E4/4; R/4   |  F4/4; G4/2.          | 
L1: Hel-  ; lo  ; dear; %     |  how   are  you        |
```

Melisma example (one syllable across three notes):

```
T1: G4/4;   A4/8, B4/8;  C5/4 |
L1: A    ;  _             _    |
```

### 16.2 Multiple Verse Tracks

Additional verses use `L2:`, `L3:`, etc.:

```
T1: C4/4;  D4/4;  E4/4;  F4/4 |
L1: Twink-; le   ; twink-; le  |    # Verse 1
L2: Up    ; a-   ; bove  ; the |    # Verse 2
```

### 16.3 Lyric Track Binding

By default, `L1` binds to `T1`, `L2` to `T2`, etc. Explicit binding overrides this:

```
[BIND: L1→T2]    → attach L1 lyrics to Track 2
```

---

## 17. Multi-Track Synchronization

### 17.1 Temporal Alignment

Tracks are **time-synchronized**: measure 1 of `T1` plays simultaneously with measure 1 of `T2`. Bar lines act as synchronization checkpoints. All tracks must have the same number of measures.

Synchronization is determined entirely by the **beat grid** — the sequence of semicolons and bar lines — not by ASCII column position. Because whitespace is insignificant (§8.4) and held beats require explicit empty slots (§8.3), every track in a score has an identical number of semicolons per measure, making the grid unambiguous regardless of visual formatting.

The following example is in `4/4` (three semicolons per measure). T1 has four quarter-note attacks; T2 has two half-note attacks (beats 2 and 4 are held/empty); T3 has one whole-note attack per measure (beats 2, 3, and 4 are held/empty):

```
T1: C5/4; B4/4; A4/4; G4/4 | F4/1;   ;   ;   |
T2: C4/2;     ; A3/2;       | F3/2;   ; G3/2; |
T3: C3/1;     ;     ;       | F2/1;   ;   ;   |
```

An AI parsing this file must count semicolons to locate beat boundaries, not measure character offsets. The optional space-padding is a human-readability aid that aligns slots into visual columns; a correctly written .mmd file produces the same parse result whether it is formatted as above or as the compact equivalent:

```
T1: C5/4;B4/4;A4/4;G4/4|F4/1;;;|
T2: C4/2;;A3/2;|F3/2;;G3/2;|
T3: C3/1;;;|F2/1;;;|
```

Both representations are semantically identical.

### 17.2 Track Groups

Related tracks can be grouped for collective commands:

```
[GROUP:GRP1=T1,T2]    → define group GRP1
[DYN:f:GRP1]          → apply forte to all tracks in GRP1
[XPOSE:+2:GRP1]       → transpose group up 2 semitones
```

### 17.3 Track Muting and Soloing

For AI arrangement and analysis tasks:

```
[MUTE:T2]       → mute track T2
[SOLO:T1]       → solo track T1 (mute all others)
[UNMUTE:all]    → restore all tracks
```

### 17.4 Voice Leading on a Single Track

Two independent voices sharing a staff (common in SATB or piano writing) are separated by `//` within a single track line:

```
T1: C5/4; D5/4; E5/4; F5/4 // E4/4; F4/4; G4/4; A4/4 |
#   Voice 1 (Soprano)        // Voice 2 (Alto)
```

Both voices are parsed as simultaneous streams within the same track. Voice 1 precedes `//`, Voice 2 follows it. Duration rules and beat anchors apply independently to each voice.

---

## 18. Comments and Annotations

### 18.1 Line Comments

Lines beginning with `#` are comments and are ignored by parsers:

```
# This is a full-line comment
T1: C4/4; D4/4 |   # This is an end-of-line comment
```

### 18.2 Block Annotations

Multiline annotations use `#[ ... ]#`:

```
#[
  This section modulates from C major to G major.
  The pivot chord is G (V in C, I in G).
]#
```

### 18.3 AI Instruction Tags

Special `#AI:` comment tags pass instructions directly to an AI processor without affecting the musical output:

```
#AI: When generating variations of this phrase, preserve the rhythmic shape.
#AI: Harmonize the melody in T1 for T2 using only diatonic chords in C major.
#AI: Generate a four-measure continuation that develops the opening motive.
```

---

## 19. Formal Grammar (EBNF)

The following Extended Backus-Naur Form grammar defines the .mmd syntax precisely.

```ebnf
file          = header? track-section+ ;

header        = header-field+ ;
header-field  = "@" KEY ":" VALUE NEWLINE ;

track-section = track-line+ ;
track-line    = track-prefix ":" measure+ NEWLINE ;
track-prefix  = ("T"|"L"|"P"|"C") DIGIT+ ;

measure       = beat (";" beat)* "|" repeat-suffix? ;
beat          = event ("," event)* | global-cmd ;
event         = grace-note? note | chord | rest | tuplet-block | slur-group ;

note          = pitch duration? modifier* tie? ;
pitch         = PITCH-CLASS accidental? OCTAVE | "R" ;
PITCH-CLASS   = "A"|"B"|"C"|"D"|"E"|"F"|"G" ;
accidental    = "#" | "b" | "##" | "bb" | "n" ;
OCTAVE        = DIGIT ;
duration      = "/" DIGIT+ "."* ;
tie           = "~" note ;
modifier      = "(" MOD-TOKEN ")" ;

chord         = "[" pitch ("," pitch)* "]" duration? inversion? modifier* ;
inversion     = "/" PITCH-CLASS ;

rest          = "R" duration | "R/M" ;
grace-note    = "{" "!"? note+ "}" ;

slur-group    = "<" event+ ">" ;

tuplet-block  = ( "[TUP:" DIGIT ":" DIGIT "]"
                | "[TRP]" | "[QNT]" | "[SPT]" )
                event+
                ( "[/TUP]" | "[/TRP]" | "[/QNT]" | "[/SPT]" ) ;

repeat-suffix = ":" ("[REP:x" DIGIT+ "]")? ;
bar-line      = "|" | "||" | "|." | "|:" | ":|" ;

global-cmd    = "[" CMD-NAME (":" CMD-VALUE)* "]" ;

comment       = "#" .* NEWLINE | "#[" .* "]#" ;
```

---

## 20. Complete Examples

### 20.1 Minimal Example — Single Melody

```mmd
T1: C4/4; E4/4; G4/4; E4/4 | D4/4; F4/4; A4/4; F4/4 | C4/1 |.
```

### 20.2 Simple Two-Hand Piano

```mmd
@TITLE: Simple Study in C
@BPM: 100
@TIME: 4/4
@KEY: C
@TRACKS: T1=Right Hand, T2=Left Hand

[CLEF:T1:treble]
[CLEF:T2:bass]

T1: E4/4; G4/4; C5/4; G4/4 | D4/4; F4/4; B4/4; F4/4 | C4/1 |.
T2: [C3,G3]/2; [C3,G3]/2    | [G2,D3]/2; [G2,D3]/2   | C3/1 |.
```

### 20.3 Melody with Lyrics

```mmd
@TITLE: Twinkle Twinkle
@BPM: 120
@TIME: 4/4
@KEY: C

T1: C4/4; C4; G4; G4  | A4/4; A4; G4/2      | F4/4; F4; E4; E4  | D4/4; D4; C4/2      |.
L1: Twin-; kle; twin-; kle | lit-; tle; star  | how ; I ; won-; der | what; you; are      |.
```

### 20.4 Jazz Chord Voicings

```mmd
@TITLE: Jazz Comping Sketch
@BPM: 132
@TIME: 4/4
@KEY: F

[DYN:mf]
T1: R/8,[F3,A3,C4,Eb4]/8; R/8,[G3,Bb3,D4]/8; [F3,A3,C4,Eb4]/4; R/4         |
T1: R/8,[Bb3,D4,F4]/8;    [Bb3,D4,F4]/4;      R/8,[A3,C4,Eb4,G4]/8; R/4     |.
```

### 20.5 Dynamics, Articulation, Pedal

```mmd
@TITLE: Expressive Fragment
@BPM: 72
@TIME: 3/4
@KEY: G

[DYN:p]
T1: G4/4(ped)(~); A4/4; B4/4(ped*) | [DYN:mf] C5/4(^); B4/4(.); A4/4      |
  | [CRESC:2:mf:f] G4/2.; G4/2.     | G4/1(f)(ped)(ped*)                   |.
```

### 20.6 Triplets and Ornaments

```mmd
@TITLE: Ornament Study
@BPM: 88
@TIME: 4/4

T1: [TRP] C5/8, D5/8, E5/8 [/TRP]; F5/4(tr); G5/4; {B4/16}C5/4 |
  | A4/4(m); G4/4; F4/4(.); E4/4(>)                              |.
```

### 20.7 Repeats with Volta Brackets

```mmd
@TITLE: Folk Song with Repeat
@BPM: 96
@TIME: 4/4

|: G4/4; A4/4; B4/4; C5/4 | D5/4; C5/4; B4/4; A4/4 [VOLTA:1] | G4/1 :|
[VOLTA:2] G4/2; D5/2 |. 
```

### 20.8 Complex Multi-Track with AI Instruction

```mmd
@TITLE: Orchestral Sketch
@BPM: 108
@TIME: 4/4
@KEY: D
@TRACKS: T1=Violin, T2=Viola, T3=Cello

#AI: Generate a continuation of 8 measures that develops the opening 4-note motive in T1.
#AI: Keep T2 and T3 rhythmically simpler than T1.

[DYN:mf]
[SECT:Opening]

T1: F#5/4; E5/4; D5/4; C#5/4 | B4/4; A4/4; G4/4; F#4/4 |.
T2: D5/2;  A4/2               | G4/2; D4/2               |.
T3: D3/1                      | G2/1                     |.
```

---

## 21. Implementation Notes for AI

### 21.1 Parsing Algorithm

When parsing a .mmd file, an AI or parser implementation should follow this order:

1. **Tokenize**: Split input on `|` (measures), `;` (beats), `,` (subdivisions within a beat).
2. **Resolve headers**: Extract `@`-prefixed global metadata.
3. **Resolve global commands**: Apply `[CMD:VAL]` blocks to all subsequent tokens.
4. **Per-note parsing**: For each token, split on `/` to extract pitch and duration. Strip `()` groups as modifier lists. Check for `~` ties, `<>` slur wrappers, `{}` grace notes, `[...]` chord or tuplet blocks.
5. **Validate grid**: Verify that durations within each beat slot sum to exactly one beat (as defined by the denominator of the current time signature).
6. **Build event list**: Construct a flat, time-stamped event list with absolute tick positions (e.g., MIDI-style).

### 21.2 Mathematical Operations

.mmd is designed to support these operations without risking rhythmic corruption:

| Operation | Method |
|-----------|--------|
| **Transposition** | Add/subtract semitones to all PITCH-CLASS + OCTAVE values. Adjust OCTAVE when pitch crosses octave boundary. |
| **Time-shift** | Move a note's beat-slot position by N semicolons. Insert `R/` tokens to fill vacated slots. |
| **Inversion** | Mirror pitches around an axis pitch: `new_semitone = 2 × axis - original_semitone`. |
| **Retrograde** | Reverse the order of note tokens within a phrase block, preserving individual durations. |
| **Augmentation** | Multiply all duration denominators by 2 (e.g., `/4` → `/2`). Update `[TIME:]` accordingly. |
| **Diminution** | Divide all duration denominators by 2. |
| **Harmonization** | For each note in T1, generate T2/T3 notes at specified intervallic distances. |

### 21.3 Token Uniqueness Guarantee

Every note in a correctly written .mmd file is a **fully self-describing token**. A parser encountering `F#5/8(mf)(.)` in isolation can determine:
- Pitch: F-sharp, octave 5
- Duration: eighth note
- Dynamic: mezzo-forte
- Articulation: staccato

No surrounding context is required to interpret this token. This property enables AI systems to process notes individually, in parallel, or out of sequence, and still reconstruct the piece correctly.

### 21.4 Duration Inheritance Warning

Duration inheritance (§6.3) is the one exception to the self-describing token guarantee. When parsing a sequence like `C4/4; D4; E4`, the durations of `D4` and `E4` are implicit. AI implementations should **resolve inheritance at parse time** and store all notes with explicit durations in internal representation, treating inheritance as syntactic sugar only.

### 21.5 Recommended Internal Representation

```json
{
  "tick": 0,
  "track": 1,
  "type": "note",
  "pitch": { "class": "C", "accidental": null, "octave": 4, "semitone_abs": 60 },
  "duration_beats": 1.0,
  "duration_ticks": 480,
  "modifiers": ["mf", "staccato"],
  "tied_to": null,
  "slur": false,
  "measure": 1,
  "beat": 1
}
```

Storing `semitone_abs` (MIDI note number) alongside the SPN representation enables efficient transposition and interval calculations.

---

## 22. Quick Reference Card

```
PITCHES         C D E F G A B   (+ # b n for accidentals)
OCTAVES         C4 = Middle C   A4 = 440 Hz
DURATIONS       /1 /2 /4 /8 /16 /32   dots: /4. /4..
RESTS           R/4  R/2  R/M (full measure)
BAR LINES       |  ||  |.  |:  :|
BEAT ANCHOR     ;  (required at EVERY beat boundary, always)
HELD BEAT       ;  (empty slot — note is sustained, no new attack)
SUBDIVISION     ,  (between notes within a beat)
WHITESPACE      ignored everywhere except inside a token
CHORD           [C4,E4,G4]/4
TIE             C4/4~C4/4
SLUR            <C4/4; D4/4; E4/4>
GRACE NOTE      {B3/16}C4/4
APPOGGIATURA    {!B3/8}C4/4
TUPLET          [TRP] C4/8,D4/8,E4/8 [/TRP]
MODIFIERS       (ppp)(pp)(p)(mp)(mf)(f)(ff)(fff)  dynamics
                (.)(-)( ^)(>)(~)                  articulation
                (tr)(m)(mu)(t)(ti)                ornaments
                (ped)(ped*)(una)(tre)              pedal
                (up)(dn)(pizz)(arco)              bowing
GLOBAL CMDS     [BPM:120]  [TIME:4/4]  [KEY:G]
                [DYN:f]  [CRESC:4]  [DIM:2]
                [XPOSE:+3]  [SECT:Label]
                [CLEF:T1:treble]  [8VA]  [8VA*]
REPEATS         |: ... :| [REP:x3]
VOLTA           [VOLTA:1] ... [VOLTA:2]
NAMED BLOCKS    [BLK:A] ... [/BLK:A]  →  [FORM: A A B A]
TRACKS          T1: (melody)  T2: (harmony)
LYRICS          L1: syl-; la; ble; here |
PERCUSSION      P1: (drum patterns)
COMMENTS        # line comment   #[ block ]#
AI TAGS         #AI: instruction for AI processor
DUAL VOICE      T1: V1notes // V2notes |
```

---

*Musical Markdown (.mmd) Specification — Version 1.0 Draft*  
*This document is open for extension. Propose additions via the `#AI:` annotation system or by filing issues against the spec repository.*
