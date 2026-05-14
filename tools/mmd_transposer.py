#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 km-vibecoder
"""
Musical Markdown (.mmd) mathematical transformation tool — Spec v1.0 companion
Usage:
    python tools/mmd_transposer.py score.mmd --transpose +5
    python tools/mmd_transposer.py score.mmd --invert C4
    python tools/mmd_transposer.py score.mmd --retrograde
    python tools/mmd_transposer.py score.mmd --augment
    python tools/mmd_transposer.py score.mmd --diminish
    python tools/mmd_transposer.py score.mmd --transpose +3 --track T1,T2
    python tools/mmd_transposer.py score.mmd --augment -o out.mmd

Operations can be chained (applied left to right):
    python tools/mmd_transposer.py score.mmd --transpose +2 --augment

Output preserves original whitespace for pitch/duration operations.
Retrograde collapses continuation lines into one line per track (whitespace stripped).
Exit: 0=success  1=transform error  2=IO error  3=validation failure
"""
import re, sys, argparse
from pathlib import Path

# ── Pitch tables ──────────────────────────────────────────────────────────────
_PC_TO_SEMI = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
_SEMI_TO_PC = {0:'C',1:'C#',2:'D',3:'D#',4:'E',5:'F',
               6:'F#',7:'G',8:'G#',9:'A',10:'A#',11:'B'}

def _spn_semitone(pc:str, acc:str|None, octave:int) -> int:
    s = _PC_TO_SEMI[pc.upper()]
    if acc:
        s += acc.count('#') - acc.count('b')
    return (octave + 1) * 12 + s

def _semitone_to_spn(st:int) -> tuple[str, int]:
    st = max(0, min(127, st))
    return _SEMI_TO_PC[st % 12], st // 12 - 1

# ── Patterns ──────────────────────────────────────────────────────────────────
# Matches a pitch token (pitch-class + optional accidental + octave digit) at a
# position that is NOT inside a word (guards against matching inside BPM, KEY…).
# Lookahead ensures what follows is a note-continuation character.
NOTE_RE = re.compile(
    r'(?<![A-Za-z\d])'
    r'([A-Ga-g])(#{1,2}|b{1,2}|n)?([0-9])'
    r'(?=[/,\]~;| \t]|$)'
)
# Matches /N or /N. or /N.. in note/rest position
DUR_RE = re.compile(r'/(\d+)(\.{0,2})')

RE_HEADER   = re.compile(r'^@(\w+)\s*:\s*(.+)$')
RE_TRACK    = re.compile(r'^([TLPCtlpc]\d+)\s*:(.+)$')
RE_CONT     = re.compile(r'^\s*\|(.+)$')
RE_TIME_HDR = re.compile(r'^(@TIME\s*:\s*)(\d+)/(\d+)$')
RE_TIME_CMD = re.compile(r'(\[TIME:)(\d+)/(\d+)(\])')

# ── Helpers ───────────────────────────────────────────────────────────────────
def _strip_comment(line:str) -> str:
    depth = 0
    for i, ch in enumerate(line):
        if ch in ('(','['): depth += 1
        elif ch in (')',']'): depth -= 1
        elif ch == '#' and depth == 0 and i > 0 and line[i-1] in (' ','\t'):
            return line[:i].rstrip()
    return line

def _strip_ws(s:str) -> str:
    return re.sub(r'[ \t]+', '', s)

# ── Bracket-aware body splitter ───────────────────────────────────────────────
# Splits a track body into alternating (non-bracket, bracket-block) segments.
# Bracket blocks include optional /dur, /inversion, and modifier suffixes.
_BRACKET_RE = re.compile(
    r'(\[[^\]]*\]'            # [...]
    r'(?:/\d+[.]{0,2})?'     # optional /dur
    r'(?:/[A-Ga-g][#b]?)?'   # optional /inversion
    r'(?:\([^)]*\))*)'        # optional modifier(s)
)

def _split_on_brackets(body:str) -> list[str]:
    """Return alternating [outside, bracket-block, outside, …] segments."""
    return _BRACKET_RE.split(body)

def _is_chord_block(seg:str) -> bool:
    """True if seg is a chord [...] block (no colon inside the brackets)."""
    m = re.match(r'^\[([^\]]*)\]', seg)
    return bool(m) and ':' not in m.group(1)

# ── Pitch operations ──────────────────────────────────────────────────────────
def _apply_pitch_to_body(body:str, pitch_fn) -> str:
    """Apply pitch_fn to every pitch token in a track body, skipping command blocks."""
    def _replace(m:re.Match) -> str:
        new_pc, new_oct = pitch_fn(m.group(1).upper(), m.group(2), int(m.group(3)))
        return f"{new_pc}{new_oct}"

    parts = _split_on_brackets(body)
    out = []
    for seg in parts:
        if seg.startswith('['):
            if _is_chord_block(seg):
                # Transform pitches inside [...], leave the rest (/dur, modifiers) unchanged
                inner_m = re.match(r'^\[([^\]]*)\]', seg)
                new_inner = NOTE_RE.sub(_replace, inner_m.group(1))
                out.append('[' + new_inner + ']' + seg[len(inner_m.group(0)):])
            else:
                out.append(seg)   # command block — copy verbatim
        else:
            out.append(NOTE_RE.sub(_replace, seg))
    return ''.join(out)


def make_transpose_fn(semitones:int):
    def fn(pc:str, acc:str|None, octave:int) -> tuple[str, int]:
        return _semitone_to_spn(_spn_semitone(pc, acc, octave) + semitones)
    return fn


def make_invert_fn(axis:int):
    def fn(pc:str, acc:str|None, octave:int) -> tuple[str, int]:
        return _semitone_to_spn(2 * axis - _spn_semitone(pc, acc, octave))
    return fn


def apply_pitch_op(source:str, pitch_fn, targets:set|None) -> str:
    lines = source.splitlines()
    out = []; cur_track = None
    for line in lines:
        s = line.strip()
        m = RE_TRACK.match(s)
        if m:
            cur_track = m.group(1).upper()
            if targets is None or cur_track in targets:
                out.append(f"{cur_track}:" + _apply_pitch_to_body(m.group(2), pitch_fn))
            else:
                out.append(line)
            continue
        m2 = RE_CONT.match(line)
        if m2 and cur_track:
            if targets is None or cur_track in targets:
                out.append('|' + _apply_pitch_to_body(m2.group(1), pitch_fn))
            else:
                out.append(line)
            continue
        out.append(line)
    return '\n'.join(out)


# ── Duration scaling ──────────────────────────────────────────────────────────
def _scale_denom(denom:int, augment:bool, msgs:list, ctx:str) -> int:
    if augment:
        if denom == 1:
            msgs.append(f"Error: {ctx} /1 cannot be augmented (would require a double-whole note)")
            return 1
        if denom % 2 != 0:
            msgs.append(f"Warning: {ctx} /{ denom} is odd; augmented result may be non-standard")
        return denom // 2
    else:   # diminish
        new = denom * 2
        if new > 128:
            msgs.append(f"Warning: {ctx} /{denom} diminished to /{new} (exceeds /64 standard range)")
        return new


def _scale_durs_in_body(body:str, augment:bool, msgs:list, ctx:str) -> str:
    parts = _split_on_brackets(body)
    out = []
    for seg in parts:
        if seg.startswith('['):
            if _is_chord_block(seg):
                inner_m = re.match(r'^\[([^\]]*)\]', seg)
                tail = seg[len(inner_m.group(0)):]
                # Scale only the first /N in the tail (the chord duration, not /inversion)
                scaled_tail = DUR_RE.sub(
                    lambda m: '/' + str(_scale_denom(int(m.group(1)), augment, msgs, ctx)) + m.group(2),
                    tail, count=1
                )
                out.append('[' + inner_m.group(1) + ']' + scaled_tail)
            else:
                out.append(seg)
        else:
            out.append(DUR_RE.sub(
                lambda m: '/' + str(_scale_denom(int(m.group(1)), augment, msgs, ctx)) + m.group(2),
                seg
            ))
    return ''.join(out)


def apply_duration_scale(source:str, augment:bool, targets:set|None) -> tuple[str, list]:
    msgs = []; lines = source.splitlines(); out = []; cur_track = None

    def _scale_time(num:int, den:int) -> str:
        new_den = _scale_denom(den, augment, msgs, '@TIME / [TIME]')
        return f"{num}/{new_den}"

    for line in lines:
        s = line.strip()

        # @TIME header
        m = RE_TIME_HDR.match(s)
        if m:
            out.append(m.group(1) + _scale_time(int(m.group(2)), int(m.group(3)))); continue

        # [TIME:n/n] inline command (may appear mid-track-line)
        if '[TIME:' in s:
            def _replace_time(tm):
                return tm.group(1) + _scale_time(int(tm.group(2)), int(tm.group(3))) + tm.group(4)
            out.append(RE_TIME_CMD.sub(_replace_time, line)); continue

        m = RE_TRACK.match(s)
        if m:
            cur_track = m.group(1).upper()
            if targets is None or cur_track in targets:
                out.append(f"{cur_track}:" + _scale_durs_in_body(m.group(2), augment, msgs, cur_track))
            else:
                out.append(line)
            continue

        m2 = RE_CONT.match(line)
        if m2 and cur_track:
            if targets is None or cur_track in targets:
                out.append('|' + _scale_durs_in_body(m2.group(1), augment, msgs, cur_track))
            else:
                out.append(line)
            continue

        out.append(line)

    return '\n'.join(out), msgs


# ── Retrograde ────────────────────────────────────────────────────────────────
def _slots_to_events(slots:list[str]) -> list[tuple[str, int]]:
    """
    Group beat slots into (attack_token, held_count) pairs.
    Each non-empty slot is an attack; subsequent empty slots are held beats for that attack.
    """
    events: list[tuple[str, int]] = []
    for slot in slots:
        s = slot.strip()
        if s:
            events.append((s, 0))
        else:
            if events:
                tok, held = events[-1]
                events[-1] = (tok, held + 1)
            else:
                events.append(('', 1))   # leading empty slot (unusual but valid)
    return events


def _events_to_slots(events:list[tuple[str, int]]) -> list[str]:
    slots = []
    for tok, held in events:
        slots.append(tok)
        slots.extend([''] * held)
    return slots


def _retrograde_measure(body:str) -> str:
    """Reverse note order within one measure body."""
    slots = body.split(';')
    events = _slots_to_events(slots)
    new_slots = _events_to_slots(list(reversed(events)))
    return ';'.join(new_slots)


def apply_retrograde(source:str, targets:set|None) -> str:
    """
    Collect all measures per track (joining continuations), reverse their order,
    apply within-measure retrograde, and reconstruct the source with one line per track.
    """
    lines = source.splitlines()
    track_measures: dict[str, list[str]] = {}
    track_first_line: dict[str, int] = {}   # line index of first track line
    cur_track = None

    def _collect(prefix:str, body:str):
        b = _strip_ws(_strip_comment(body))
        b = b.replace('|:','|').replace(':|','|')
        measures = [s.strip('.').strip() for s in b.split('|') if s.strip('.').strip()]
        if prefix not in track_measures:
            track_measures[prefix] = []
        track_measures[prefix].extend(measures)

    for i, line in enumerate(lines):
        s = line.strip()
        m = RE_TRACK.match(s)
        if m:
            cur_track = m.group(1).upper()
            if cur_track.startswith('T') and (targets is None or cur_track in targets):
                if cur_track not in track_first_line:
                    track_first_line[cur_track] = i
                _collect(cur_track, m.group(2))
            continue
        m2 = RE_CONT.match(line)
        if m2 and cur_track and cur_track in track_measures:
            _collect(cur_track, m2.group(1))

    # Retrograde: reverse measure order, retrograde within each measure
    retro: dict[str, str] = {}
    for prefix, measures in track_measures.items():
        retro[prefix] = '|'.join(_retrograde_measure(mb) for mb in reversed(measures)) + '|.'

    # Reconstruct: replace original track lines/continuations with retrograded output
    out = []; emitted: set[str] = set(); cur_track = None
    for line in lines:
        s = line.strip()
        m = RE_TRACK.match(s)
        if m:
            cur_track = m.group(1).upper()
            if cur_track in retro:
                if cur_track not in emitted:
                    emitted.add(cur_track)
                    out.append(f"{cur_track}:{retro[cur_track]}")
                # continuation lines for this track are absorbed → skip
            else:
                out.append(line)
            continue
        m2 = RE_CONT.match(line)
        if m2 and cur_track and cur_track in retro:
            continue   # absorbed
        out.append(line)

    return '\n'.join(out)


# ── Validation ────────────────────────────────────────────────────────────────
def _validate(source:str, label:str='') -> bool:
    try:
        import importlib.util
        spec_path = Path(__file__).parent / 'mmd_validator.py'
        spec = importlib.util.spec_from_file_location('mmd_validator', spec_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        valid, errors, _ = mod.validate(source)
        if not valid:
            tag = f' of {label}' if label else ''
            n = sum(1 for e in errors if e.severity == 'error')
            print(f"Validation{tag} failed: {n} error(s).", file=sys.stderr)
            for e in errors:
                if e.severity == 'error':
                    parts = []
                    if e.track:   parts.append(e.track)
                    if e.measure: parts.append(f"M{e.measure}")
                    if e.beat:    parts.append(f"B{e.beat}")
                    print(f"  ✗ {' '.join(parts) or 'global'}: {e.message}", file=sys.stderr)
        return valid
    except Exception as exc:
        print(f"Warning: could not run validator ({exc}).", file=sys.stderr)
        return True


# ── SPN parser (for --invert axis pitch) ─────────────────────────────────────
def _parse_spn(s:str) -> tuple[str, str|None, int]:
    m = re.match(r'^([A-Ga-g])(#{1,2}|b{1,2}|n)?([0-9])$', s.strip())
    if not m:
        raise ValueError(f"Invalid pitch '{s}' — expected format: C4, F#3, Bb5")
    return m.group(1).upper(), m.group(2), int(m.group(3))


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(
        description='Apply mathematical transformations to a Musical Markdown (.mmd) file.')
    ap.add_argument('file', nargs='?', default='-',
                    help='Input .mmd file (or - for stdin)')
    ap.add_argument('-o', '--output', default=None,
                    help='Output file (default: <stem>_transformed.mmd, or stdout for stdin)')
    ap.add_argument('--transpose', metavar='N',
                    help='Transpose by N semitones (e.g. +5, -3, 7)')
    ap.add_argument('--invert', metavar='PITCH',
                    help='Mirror all pitches around axis (e.g. C4, F#3)')
    ap.add_argument('--retrograde', action='store_true',
                    help='Reverse note order (measures reversed, notes within each measure reversed)')
    ap.add_argument('--augment', action='store_true',
                    help='Double all note durations: /4 → /2, @TIME 4/4 → 4/2')
    ap.add_argument('--diminish', action='store_true',
                    help='Halve all note durations: /4 → /8, @TIME 4/4 → 4/8')
    ap.add_argument('--track', metavar='T1,T2,...',
                    help='Apply operations to specific tracks only (default: all T-tracks)')
    ap.add_argument('--no-validate', action='store_true',
                    help='Skip validator pre- and post-check')
    args = ap.parse_args()

    ops = [args.transpose, args.invert, args.retrograde, args.augment, args.diminish]
    if not any(ops):
        ap.error("Specify at least one operation: --transpose, --invert, --retrograde, "
                 "--augment, --diminish")
    if args.augment and args.diminish:
        ap.error("--augment and --diminish are mutually exclusive")

    targets = {t.strip().upper() for t in args.track.split(',')} if args.track else None

    # Read
    try:
        if args.file == '-':
            source = sys.stdin.read(); stem = None
        else:
            p = Path(args.file)
            if not p.exists():
                print(f"Error: not found: {args.file}", file=sys.stderr); sys.exit(2)
            source = p.read_text(encoding='utf-8'); stem = p.stem
    except IOError as e:
        print(f"IO error: {e}", file=sys.stderr); sys.exit(2)

    # Pre-validate
    if not args.no_validate:
        if not _validate(source, 'input'): sys.exit(3)

    result = source; msgs = []

    # Apply operations left to right
    if args.transpose:
        try:
            n = int(args.transpose.lstrip('+'))
        except ValueError:
            print(f"Error: --transpose expects an integer like +5 or -3", file=sys.stderr)
            sys.exit(1)
        result = apply_pitch_op(result, make_transpose_fn(n), targets)

    if args.invert:
        try:
            pc, acc, oct_ = _parse_spn(args.invert)
            axis = _spn_semitone(pc, acc, oct_)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr); sys.exit(1)
        result = apply_pitch_op(result, make_invert_fn(axis), targets)

    if args.retrograde:
        result = apply_retrograde(result, targets)

    if args.augment or args.diminish:
        result, scale_msgs = apply_duration_scale(result, augment=args.augment, targets=targets)
        msgs.extend(scale_msgs)

    # Report messages, exit on errors
    has_error = False
    for msg in msgs:
        print(msg, file=sys.stderr)
        if msg.startswith('Error'): has_error = True
    if has_error: sys.exit(1)

    # Post-validate
    if not args.no_validate:
        if not _validate(result, 'output'):
            print("Tip: the transformation may have produced invalid .mmd. "
                  "Use mmd_validator.py for details.", file=sys.stderr)

    # Write
    try:
        if args.output:
            out_path = Path(args.output)
            out_path.write_text(result, encoding='utf-8')
            print(f"✓  Wrote {out_path}")
        elif stem:
            out_path = Path(stem + '_transformed.mmd')
            out_path.write_text(result, encoding='utf-8')
            print(f"✓  Wrote {out_path}")
        else:
            print(result)
    except IOError as e:
        print(f"IO error writing output: {e}", file=sys.stderr); sys.exit(2)

if __name__ == '__main__':
    main()
