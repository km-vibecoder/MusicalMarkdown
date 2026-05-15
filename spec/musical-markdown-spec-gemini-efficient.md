# Musical Markdown (.mmd) — Efficient Spec (Gemini Version)
## 1. Core Invariants
- **Linear/Explicit**: Music flows left-to-right. Pitch+Octave+Duration are mandatory. No vertical stacking (except chords).
- **Fixed Beat Grid**: Measures are sliced by beat anchors `;`. 
  - **4/4**: Exactly 3 `;` (4 slots) per track-measure.
  - **3/4**: Exactly 2 `;` (3 slots) per track-measure.
- **Held Beats**: If a note spans >1 beat, the attack is in slot 1; subsequent slots are bare `;`. 
  - *Ex (4/4 whole note)*: `C4/1 ; ; ; |`

## 2. Token Anatomy
- **Note**: `[Pitch][Accidental][Octave]/[Denominator][Dots][Modifiers][Tie]`
  - *Pitch*: `A-G`. *Accidental*: `#`, `b`, `##`, `bb`, `n` (natural). *Octave*: `0-8` (`C4`=mid C).
  - *Duration*: `/1`, `/2`, `/4`, `/8`, `/16`, `/32`. `.` (+50%), `..` (+75%).
  - *Modifiers*: `(f)`, `(.)`, `(tr)`. *Tie*: `~`.
  - *Ex*: `C#4/4.(mf)(.)~`
- **Rest**: `R/[dur]` or `R/M` (full measure rest).
- **Chord**: `[P1,P2,...]/[dur][Inversion][Modifiers]`
  - *Ex*: `[C4,E4,G4]/4/E(p)`
- **Grace**: `{note,note}principal` (unmetered). `{!note}principal` (appoggiatura).

## 3. Structural Grammar
- **Separators**: `|` (measure), `;` (beat), `,` (sub-beat subdivision).
- **Hierarchy**: `Measure > Beat Slot > Event`.
- **Inheritance**: Notes omit `/dur` to inherit from previous note in same measure. Resets at `|`.
- **Tuplets**: `[TRP]...[/TRP]` (3:2), `[QNT]...[/QNT]` (5:4), `[SPT]...[/SPT]` (7:4), `[TUP:act:norm]`.
- **Multi-Voice**: `T1: Voice1 // Voice2 |` (Independent grids per voice).

## 4. Metadata & Global Commands
- **Header**: `@KEY: VAL` (BPM, TIME, KEY, TITLE, TRACKS).
- **Global**: `[BPM:120]`, `[TIME:4/4]`, `[KEY:G]`, `[DYN:f]`, `[XPOSE:+2]`.
- **Tracks**: `Tn:` (Tone), `Ln:` (Lyric), `Pn:` (Percussion).

## 5. Concise Example (4/4, C Major)
```mmd
@BPM: 120
@TIME: 4/4
T1: C4/4; E4; G4; C5/4 | [TRP] D5/8,C5,B4 [/TRP]; A4/2; ; |
T2: [C3,G3]/1; ; ;     | F3/2; ; G3/2;               |
L1: Twink-; le; twink-; le | lit-; tle; _ ; star      |
```

## 6. Parsing Strategy
1. Split by `|` (measures).
2. For each measure, split by `;` (beat slots).
3. If slot contains `,`, split into sub-events.
4. Scale durations by current tuplet factor or time signature.
5. Resolve `/dur` inheritance measure-locally.
