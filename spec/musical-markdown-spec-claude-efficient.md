# Musical Markdown (.mmd) — Claude-Efficient Spec

## Invariants

1. **Explicit everything**: every note carries pitch+octave+duration. Nothing is inferred from position or context.
2. **Beat grid**: semicolons `;` are mandatory beat boundaries. In N/M time, every measure has exactly (N−1) semicolons per track — always, regardless of note durations.
3. **Held beats**: a note spanning >1 beat occupies its attack slot plus empty slots for each held beat. `C4/1` in 4/4 → `C4/1; ; ; |` (3 empty slots). Slot count, not duration values, defines measure length.
4. **Whitespace is insignificant** everywhere except *inside* a token. `C 4/4` is invalid; `C4/4 ; D4/4` is valid.
5. **Key signatures are display-only**. They do not alter explicit pitches. Always honor the written pitch.
6. **Duration inheritance**: a note may omit `/dur` to inherit the previous note's duration within the same track. Resets at every `|`.

---

## Token Anatomy

```
note      = PITCH ACCIDENTAL? OCTAVE / DENOM DOTS? MODIFIER* TIE?
chord     = [ PITCH, PITCH, ... ] / DENOM INVERSION? MODIFIER*
rest      = R / DENOM  |  R/M
grace     = { !? NOTE+ } PRINCIPAL_NOTE       # ! = appoggiatura (metered)
```

| Part | Values |
|------|--------|
| PITCH | `A B C D E F G` |
| ACCIDENTAL | `# b ## bb n` (n = natural, cancels key sig) |
| OCTAVE | `0–8`; C4 = middle C, A4 = 440 Hz |
| DENOM | `1 2 4 8 16 32 64` (powers of 2 only) |
| DOTS | `.` (+50% duration) `..` (+75% duration) |
| TIE | `~NOTE` (same pitch, same octave; adds duration, no re-attack) |
| INVERSION | `/PITCH_CLASS` after closing `]` |

Examples: `F#5/8(mf)(.)` · `[C4,Eb4,G4,Bb4]/2` · `{B3/16}C4/4` · `C4/4~C4/4`

---

## Beat Grid Rules

```
measure   = BEAT (; BEAT)* |
beat      = EVENT (, EVENT)*       # comma = subdivision within a beat
```

- Semicolons count beats; commas subdivide within a beat.
- Duration sum between any two adjacent `;` (or between `|` and first `;`, or last `;` and `|`) must equal exactly one beat (= 4/DENOM quarter notes).
- Empty slot `; ;` or `;;` = held beat. Both parse identically.
- Full-measure rest: `R/M` (time-signature-agnostic).

**4/4 examples:**
```
T1: C4/1; ; ;   |      ← whole note: 1 attack + 3 held
T1: C4/2; ; A4/2; |    ← two halves: held beat after each
T1: C4/8,D4/8; E4/4; F4/4; G4/4 |   ← beat 1 subdivided
```

Multi-track: measure N of T1 plays simultaneously with measure N of T2. All tracks must have equal measure counts.

---

## File Structure

```
@HEADER_FIELD: value       # optional metadata (@TITLE @BPM @TIME @KEY @TRACKS)
[GLOBAL_COMMAND]           # optional; applies to all following content
Tn: BEAT ; BEAT ... |      # tone track (simultaneous tracks play together)
Ln: syllable ; word ... |  # lyric track (beat-synced to matching Tn)
Pn: ...                    # percussion track
```

**Track continuation** (long scores): start continuation line with `|`
```
T1: C4/4; D4/4; E4/4; F4/4 | G4/4; A4/4; B4/4; C5/4 |
  | D5/4; C5/4; B4/4; A4/4 |.
```

**Dual voice on one track**: `T1: Voice1notes // Voice2notes |` (independent grids)

**Bar line types**: `|` normal · `||` section · `|.` final · `|:` begin repeat · `:|` end repeat

---

## Modifiers

Append after duration, left-to-right, no separator. E.g. `C4/4(f)(.)` = forte staccato.

**Dynamics**
| Token | Meaning |
|-------|---------|
| `(ppp)(pp)(p)(mp)(mf)(f)(ff)(fff)` | soft → loud |
| `(+)` | forte (shorthand) — reverts to "stopped" if a dynamic already present |
| `(-)` | piano (shorthand) — reverts to "tenuto" if a dynamic already present |

**Articulation**: `(.)` staccato · `(..)` staccatissimo · `(-)` tenuto · `(^)` accent · `(>)` marcato · `(~)` vibrato · `(/)` gliss up · `(\\)` gliss down

**Ornaments**: `(tr)` trill · `(tr-)` whole-step trill · `(tr+)` half-step trill · `(m)` mordent · `(mu)` upper mordent · `(t)` turn · `(ti)` inv. turn

**Pedal**: `(ped)` down · `(ped*)` up · `(sost)/(sost*)` sostenuto · `(una)/(tre)` soft pedal

**Bowing**: `(up)` up-bow · `(dn)` down-bow · `(pizz)` pizzicato · `(arco)` arco · `(sul)` sul ponticello

**Arpeggio**: `(arp)` up · `(arp^)` explicit up · `(arpv)` down

---

## Global Commands

| Command | Effect |
|---------|--------|
| `[BPM:120]` | Set tempo |
| `[TIME:4/4]` | Change time sig (next measure forward) |
| `[KEY:Bb]` `[KEY:F#m]` `[KEY:none]` | Change key sig (display only; next measure forward) |
| `[DYN:mf]` | Set dynamic level |
| `[CRESC:4]` `[CRESC:4:p:f]` | Crescendo over N measures |
| `[DIM:2]` `[DIM:2:ff:mp]` | Diminuendo |
| `[SFZ]` `[FP]` | Sforzando / forte-piano on next note |
| `[XPOSE:+3]` `[XPOSE:T1:+3]` `[XPOSE:0]` | Transpose (semitones); 0 = cancel |
| `[CLEF:T1:treble]` | Display hint only, no pitch effect |
| `[SECT:Label]` | Section annotation |
| `[TEMPO:accel]` `[TEMPO:rit]` `[TEMPO:ato]` | Tempo change/return |
| `[8VA]` `[8VA*]` `[8VB]` `[8VB*]` | Ottava brackets |
| `[MUTE:T2]` `[SOLO:T1]` `[UNMUTE:all]` | Track routing |
| `[GROUP:G1=T1,T2]` | Define track group for collective commands |

**Repeats**
```
|: ... :|              play twice
|: ... :| [REP:x3]     play 3×
T1: |: C; D; E [VOLTA:1] F :| [VOLTA:2] G |.    volta brackets
[BLK:A] ... [/BLK:A]  →  [FORM: A A B A]        named blocks
```

**Comments & AI tags**
```
# line comment
#[ block comment ]#
#AI: instruction passed to AI processor only
```

---

## Tuplets

```
[TRP] n1,n2,n3 [/TRP]          3 notes in time of 2 (triplet)
[QNT] n1,n2,n3,n4,n5 [/QNT]   5 in time of 4
[SPT] ... [/SPT]                7 in time of 4
[TUP:actual:normal] ... [/TUP]  general form
```

---

## Lyric Tracks

Beat-synced to matching Tn. Rules: `-` = syllable break · `_` = melisma continuation · `%` = rest beat.

```
T1: C4/4;  D4/4;  E4/4;  F4/4 | G4/2;    ;   R/4   |
L1: Hel- ; lo   ; there; friend| how      ; _ ; %    |
```

---

## AI Operations Reference

| Operation | Rule |
|-----------|------|
| Transpose | ±N semitones on all PITCH+OCTAVE values; adjust octave at boundary |
| Inversion | `new_semitone = 2 × axis − original_semitone` |
| Retrograde | Reverse note order within phrase; preserve individual durations |
| Augmentation | Multiply all duration denominators by 2; update `[TIME:]` |
| Diminution | Divide all duration denominators by 2 |
| Harmonization | Generate T2/T3 at specified interval distance from T1 |

**Resolve duration inheritance at parse time.** Store all notes with explicit durations internally; treat omitted `/dur` as syntactic sugar only.

**Recommended internal repr per event:**
```json
{ "tick": 0, "track": 1, "pitch_class": "C", "accidental": null,
  "octave": 4, "semitone_abs": 60, "duration_beats": 1.0,
  "modifiers": [], "tied_to": null, "measure": 1, "beat": 1 }
```

---

## Complete Example

```mmd
@TITLE: Study
@BPM: 108
@TIME: 4/4
@KEY: D
@TRACKS: T1=Violin, T2=Cello

[DYN:mf]
[CLEF:T1:treble]
[CLEF:T2:bass]

T1: F#5/4; E5/4; D5/4; C#5/4 | [TRP] B4/8,A4/8,G4/8 [/TRP]; A4/4; G4/4; F#4/4 |
  | <E4/4; F#4/4; G4/4>(^); A4/4                            | D4/1; ; ;           |.
T2: D3/1; ; ;                 | D3/2; ; A2/2;                |
  | G2/2; ; D2/2;             | D2/1; ; ;                   |.

#AI: Generate a 4-measure continuation developing the opening motive in T1.
```
