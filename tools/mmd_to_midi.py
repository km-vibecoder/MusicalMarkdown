#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 km-vibecoder
"""
Musical Markdown (.mmd) → MIDI exporter  —  Spec v1.0 companion
Usage:
    python tools/mmd_to_midi.py score.mmd              # writes score.mid
    python tools/mmd_to_midi.py score.mmd -o out.mid   # explicit output path
    python tools/mmd_to_midi.py score.mmd --no-validate  # skip validator pre-check

Exit: 0=success  1=parse/MIDI error  2=IO error  3=validation failure
Requires: midiutil  (pip install midiutil)
"""
import re, sys, argparse
from fractions import Fraction
from pathlib import Path

try:
    from midiutil import MIDIFile
except ImportError:
    print("Error: midiutil not installed.  Run:  pip install midiutil", file=sys.stderr)
    sys.exit(1)

# ── Pitch tables ──────────────────────────────────────────────────────────────
_PITCH_CLASS = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
_ACCIDENTAL  = {'#':1,'##':2,'b':-1,'bb':-2,'n':0}

def spn_to_midi(pitch_class:str, accidental:str|None, octave:int) -> int:
    """Convert Scientific Pitch Notation to MIDI note number (C4=60)."""
    semitone = _PITCH_CLASS[pitch_class.upper()]
    semitone += _ACCIDENTAL.get(accidental or '', 0)
    return (octave + 1) * 12 + semitone

# ── Dynamic → MIDI velocity ───────────────────────────────────────────────────
_DYN_VEL = {'ppp':16,'pp':33,'p':49,'mp':64,'mf':80,'f':96,'ff':112,'fff':127}

def dyn_to_vel(dyn:str) -> int:
    return _DYN_VEL.get(dyn, 80)

# ── Duration arithmetic ───────────────────────────────────────────────────────
def dur_beats(denom:int, dots:str) -> Fraction:
    base = Fraction(4, denom)
    if dots == '..':  return base * Fraction(7, 4)
    if dots == '.':   return base * Fraction(3, 2)
    return base

# ── Regex patterns (mirrors validator) ───────────────────────────────────────
RE_HEADER = re.compile(r'^@(\w+)\s*:\s*(.+)$')
RE_CMD    = re.compile(r'^\[([A-Z][A-Z0-9_/]*|/[A-Z][A-Z0-9_]*)(?::([^\]]*))?\]$')
RE_TRACK  = re.compile(r'^([TLPCtlpc]\d+)\s*:(.+)$')
RE_CONT   = re.compile(r'^\s*\|(.+)$')
RE_NOTE   = re.compile(
    r'^([A-Ga-g])(#{1,2}|b{1,2}|n)?([0-9])(/(\d+)(\.{0,2}))?'
    r'(~[A-Ga-g][#b]?[0-9](/\d+[.]{0,2})?)?(\([^)]*\))*$'
)
RE_REST   = re.compile(r'^R(/(\d+)(\.{0,2})|/M)(\([^)]*\))*$')
RE_CHORD  = re.compile(r'^\[([^\]]+)\](/(\d+)(\.{0,2})?)?(/[A-Ga-g][#b]?)?(\([^)]*\))*$')
RE_GRACE  = re.compile(r'^\{(!)?([^}]+)\}(.+)$')

NAMED_TIME = {'C':(4,4), 'C|':(2,2)}

def parse_ts(val:str):
    if val in NAMED_TIME: return NAMED_TIME[val]
    m = re.match(r'^(\d+)/(\d+)$', val)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if a > 0 and b > 0: return a, b
    return None

# ── Whitespace / comment helpers ──────────────────────────────────────────────
def strip_inline_comment(line:str) -> str:
    depth = 0
    for i, ch in enumerate(line):
        if ch in ('(', '['): depth += 1
        elif ch in (')', ']'): depth -= 1
        elif ch == '#' and depth == 0 and i > 0 and line[i-1] in (' ', '\t'):
            return line[:i].rstrip()
    return line

def strip_ws(s:str) -> str:
    return re.sub(r'[ \t]+', '', s)

# ── Beat-slot token splitter (mirrors validator) ──────────────────────────────
def split_slot(slot:str) -> list[tuple[str,bool]]:
    """Return list of (token, is_command) for one beat slot."""
    tokens = []; s = slot
    while s:
        if s.startswith('['):
            end = s.find(']')
            if end == -1: tokens.append((s, False)); break
            bk = s[:end+1]
            if RE_CMD.match(bk): tokens.append((bk, True)); s = s[end+1:]
            else:
                ce = _chord_end(s); tokens.append((s[:ce], False)); s = s[ce:]
                if s.startswith(','): s = s[1:]
        else:
            c = s.find(','); tokens.append((s if c == -1 else s[:c], False))
            if c == -1: break
            s = s[c+1:]
    return tokens

def _chord_end(s:str) -> int:
    i = 0; depth = 0
    while i < len(s):
        if s[i] == '[': depth += 1
        elif s[i] == ']':
            depth -= 1
            if depth == 0: i += 1; break
        i += 1
    while i < len(s) and s[i] not in (',', ';', '|'):
        if s[i] == '(':
            e = s.find(')', i); i = e + 1 if e != -1 else len(s)
        else: i += 1
    return i

# ── Modifier extraction ───────────────────────────────────────────────────────
_DYN_TAGS = {'ppp','pp','p','mp','mf','f','ff','fff','+','-'}
_ART_STACCATO = {'.', '..'}

def extract_modifiers(token:str) -> dict:
    """Pull dynamic and articulation modifiers out of a token string."""
    mods = {'dyn': None, 'staccato': False}
    for m in re.finditer(r'\(([^)]*)\)', token):
        tag = m.group(1).strip()
        if tag in _DYN_TAGS:
            if tag == '+': mods['dyn'] = 'f'
            elif tag == '-': mods['dyn'] = 'p'
            else: mods['dyn'] = tag
        elif tag in _ART_STACCATO:
            mods['staccato'] = True
    return mods

# ── Event data class ──────────────────────────────────────────────────────────
class NoteEvent:
    __slots__ = ('midi_note','start_beat','dur_beats','velocity','channel')
    def __init__(self, midi_note, start_beat, dur_beats, velocity, channel):
        self.midi_note  = midi_note
        self.start_beat = start_beat
        self.dur_beats  = dur_beats
        self.velocity   = velocity
        self.channel    = channel

# ── Parser / event builder ────────────────────────────────────────────────────
class MMDParser:
    def __init__(self):
        self.bpm        = 120
        self.time_num   = 4
        self.time_den   = 4
        self.global_dyn = 'mf'
        self.xpose      = 0        # semitone offset applied to all tracks
        self.tracks: dict[str, list[NoteEvent]] = {}

    # ── top-level parse ───────────────────────────────────────────────────────
    def parse(self, source:str):
        lines = source.splitlines()
        in_block = False
        cur_track = None

        for raw in lines:
            line = raw.rstrip()
            if '#[' in line: in_block = True
            if in_block:
                if ']#' in line: in_block = False
                continue
            s = line.strip()
            if not s or s == '---' or s.startswith('#'): continue

            m = RE_HEADER.match(s)
            if m:
                self._apply_header(m.group(1).upper(), m.group(2).strip())
                cur_track = None; continue

            clean = strip_ws(s)
            if RE_CMD.match(clean):
                self._apply_cmd(clean, None); cur_track = None; continue

            m = RE_TRACK.match(s)
            if m:
                cur_track = m.group(1).upper()
                self._parse_track_body(cur_track, m.group(2)); continue

            m = RE_CONT.match(s)
            if m and cur_track:
                self._parse_track_body(cur_track, m.group(1)); continue

    # ── header / command application ─────────────────────────────────────────
    def _apply_header(self, key:str, val:str):
        if key == 'BPM' and val.isdigit():       self.bpm = int(val)
        elif key == 'TIME':
            r = parse_ts(val)
            if r: self.time_num, self.time_den = r
        # KEY, TITLE, etc. are ignored for MIDI export

    def _apply_cmd(self, tok:str, track_hint):
        m = RE_CMD.match(tok)
        if not m: return
        cmd = m.group(1).upper().lstrip('/'); val = (m.group(2) or '').strip()
        if cmd == 'BPM' and val.isdigit():       self.bpm = max(1, int(val))
        elif cmd == 'TIME':
            r = parse_ts(val)
            if r: self.time_num, self.time_den = r
        elif cmd == 'DYN' and val in _DYN_TAGS:  self.global_dyn = val
        elif cmd == 'XPOSE':
            xv = val.split(':')[0]
            if xv == '0': self.xpose = 0
            elif re.match(r'^[+-]\d+$', xv): self.xpose = int(xv)
        # CRESC, DIM, CLEF, SECT, MUTE, 8VA, etc. — ignored in this pass

    # ── track body parser ─────────────────────────────────────────────────────
    def _parse_track_body(self, prefix:str, body:str):
        if prefix[0] not in ('T',):
            return   # skip lyric (L), percussion (P), chord-symbol (C) tracks

        body = strip_ws(strip_inline_comment(body))
        body = body.replace('|:', '|').replace(':|', '|')

        if prefix not in self.tracks:
            self.tracks[prefix] = []

        # Determine the beat offset = where this continuation starts
        # (count beats already stored for this track)
        events = self.tracks[prefix]
        start_offset = Fraction(0)
        if events:
            last = events[-1]
            start_offset = last.start_beat + last.dur_beats

        # Split into measures
        raw_measures = [s.strip('.').strip() for s in body.split('|') if s.strip('.').strip()]
        beat_cursor = start_offset
        last_dur: Fraction|None = None

        for mb in raw_measures:
            # Handle dual-voice: take only Voice 1 (before //)
            if '//' in mb:
                mb = mb.split('//')[0]

            beat_cursor, last_dur = self._parse_measure(
                mb, prefix, beat_cursor, last_dur, events
            )

    def _parse_measure(self, body:str, prefix:str,
                       beat_cursor:Fraction, last_dur:Fraction|None,
                       events:list) -> tuple[Fraction, Fraction|None]:
        """Parse one measure body; append NoteEvents; return updated cursor and last_dur."""
        meas_dur_f = Fraction(self.time_num * 4, self.time_den)

        # Full-measure rest
        if re.match(r'^R/M(\([^)]*\))*$', body):
            return beat_cursor + meas_dur_f, None

        slots = body.split(';')
        slot_cursor = beat_cursor
        beat_size   = Fraction(4, self.time_den)

        for slot in slots:
            slot = slot.strip()
            if not slot:
                # Empty held-beat slot — advance by one beat
                slot_cursor += beat_size
                last_dur = None   # don't carry duration across empty slots
                continue

            token_list = split_slot(slot)
            slot_start = slot_cursor
            slot_total = Fraction(0)

            for tok, is_cmd in token_list:
                tok = tok.strip()
                if not tok: continue
                if is_cmd:
                    self._apply_cmd(tok, prefix); continue

                midi_notes, dur, mods = self._parse_token(tok, last_dur, prefix)
                if dur is not None:
                    last_dur = dur

                if midi_notes and dur is not None and dur > 0:
                    vel = dyn_to_vel(mods.get('dyn') or self.global_dyn)
                    actual_dur = dur * Fraction(1, 2) if mods.get('staccato') else dur
                    ch = _track_channel(prefix)
                    for mn in midi_notes:
                        events.append(NoteEvent(mn, slot_start, actual_dur, vel, ch))
                    slot_total += dur

            # Advance cursor by the slot total, but at minimum one beat
            # so that subdivisions (commas) within a slot share the same beat position
            # and the cursor moves by one beat (the slot's "grid" size).
            # We use the actual slot_total so subdivided slots advance correctly.
            slot_cursor += slot_total if slot_total > 0 else beat_size

        return slot_cursor, last_dur

    def _parse_token(self, raw:str, last_dur:Fraction|None, prefix:str) \
            -> tuple[list[int], Fraction|None, dict]:
        """Return (midi_note_list, duration_in_beats, mods) for one token."""
        mods = extract_modifiers(raw)
        t = raw.strip()

        # Grace note — strip wrapper, parse inner note with zero duration
        g = RE_GRACE.match(t)
        if g:
            is_appoggiatura = bool(g.group(1))
            inner = g.group(3)
            notes, dur, inner_mods = self._parse_token(inner, last_dur, prefix)
            if is_appoggiatura:
                # Appoggiatura borrows half the principal's duration;
                # for MIDI export we simply play the principal at its full duration
                return notes, dur, inner_mods
            # Acciaccatura — play as grace (very short); duration = 1/64 note
            return notes, Fraction(4, 64), inner_mods

        # Slur wrapper — strip <...>
        if t.startswith('<') and t.endswith('>'):
            return self._parse_token(t[1:-1], last_dur, prefix)

        # Rest
        if t.startswith('R'):
            m = RE_REST.match(t)
            if not m: return [], None, mods
            if '/M' in t:
                meas_f = Fraction(self.time_num * 4, self.time_den)
                return [], meas_f, mods
            d = int(m.group(2)); dots = m.group(3) or ''
            return [], dur_beats(d, dots), mods

        # Chord
        if t.startswith('['):
            m = RE_CHORD.match(t)
            if not m: return [], None, mods
            pitches = [p.strip() for p in m.group(1).split(',')]
            ds = m.group(3); dots = (m.group(4) or '') if m.group(4) else ''
            dur = dur_beats(int(ds), dots) if ds else last_dur
            midi_notes = []
            for p in pitches:
                mn = _parse_pitch_token(p)
                if mn is not None:
                    midi_notes.append(mn + self.xpose)
            return midi_notes, dur, mods

        # Tied note: C4/4~C4/4 — sum durations, play combined
        if '~' in t:
            parts = t.split('~')
            total_dur = Fraction(0)
            first_notes = None
            ld = last_dur
            for part in parts:
                notes, d, _ = self._parse_token(part, ld, prefix)
                if d is not None:
                    total_dur += d; ld = d
                if first_notes is None:
                    first_notes = notes
            return (first_notes or []), total_dur or None, mods

        # Plain note
        m = RE_NOTE.match(t)
        if not m: return [], None, mods
        pc = m.group(1).upper(); acc = m.group(2); oct_ = int(m.group(3))
        ds = m.group(5); dots = m.group(6) or ''
        dur = dur_beats(int(ds), dots) if ds else last_dur
        mn = spn_to_midi(pc, acc, oct_) + self.xpose
        return [mn], dur, mods


def _parse_pitch_token(p:str) -> int|None:
    """Parse a bare pitch token (no duration) like 'C#4'."""
    m = re.match(r'^([A-Ga-g])(#{1,2}|b{1,2}|n)?([0-9])$', p.strip())
    if not m: return None
    return spn_to_midi(m.group(1), m.group(2), int(m.group(3)))

def _track_channel(prefix:str) -> int:
    """Map T1..T16 to MIDI channels 0–15 (channel 9 is reserved for drums)."""
    num = int(re.search(r'\d+', prefix).group())
    ch = (num - 1) % 16
    if ch == 9: ch = 15   # skip percussion channel
    return ch

# ── MIDI writer ───────────────────────────────────────────────────────────────
def build_midi(parser:MMDParser, ticks_per_beat:int=480) -> MIDIFile:
    tracks = list(parser.tracks.keys())
    if not tracks:
        raise ValueError("No T-prefix tracks found in .mmd file.")

    midi = MIDIFile(len(tracks), ticks_per_quarternote=ticks_per_beat)

    for ti, tname in enumerate(sorted(tracks)):
        midi.addTrackName(ti, 0, tname)
        midi.addTempo(ti, 0, parser.bpm)
        events = parser.tracks[tname]
        for ev in events:
            start_f = float(ev.start_beat)
            dur_f   = float(ev.dur_beats)
            midi.addNote(ti, ev.channel, ev.midi_note, start_f, dur_f, ev.velocity)

    return midi

# ── Validation pre-check ──────────────────────────────────────────────────────
def validate_source(source:str) -> bool:
    """Run the mmd_validator and return True if the file has no errors."""
    try:
        import importlib.util, os
        spec_path = Path(__file__).parent / 'mmd_validator.py'
        spec = importlib.util.spec_from_file_location('mmd_validator', spec_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        valid, errors, _ = mod.validate(source)
        if not valid:
            err_count = sum(1 for e in errors if e.severity == 'error')
            print(f"Validation failed: {err_count} error(s). "
                  "Fix with mmd_validator.py or pass --no-validate to skip.",
                  file=sys.stderr)
            for e in errors:
                if e.severity == 'error':
                    parts = []
                    if e.track:   parts.append(e.track)
                    if e.measure: parts.append(f"M{e.measure}")
                    if e.beat:    parts.append(f"B{e.beat}")
                    loc = ' '.join(parts) if parts else 'global'
                    print(f"  ✗ {loc}: {e.message}", file=sys.stderr)
        return valid
    except Exception as exc:
        print(f"Warning: could not run validator ({exc}); proceeding anyway.", file=sys.stderr)
        return True

# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(
        description='Convert a Musical Markdown (.mmd) file to MIDI.')
    ap.add_argument('file', nargs='?', default='-',
                    help='Input .mmd file (or - for stdin)')
    ap.add_argument('-o', '--output', default=None,
                    help='Output .mid file (default: <input>.mid)')
    ap.add_argument('--no-validate', action='store_true',
                    help='Skip mmd_validator pre-check')
    ap.add_argument('--ticks', type=int, default=480,
                    help='MIDI ticks per quarter note (default: 480)')
    args = ap.parse_args()

    # Read source
    try:
        if args.file == '-':
            source = sys.stdin.read()
            out_path = Path('output.mid') if args.output is None else Path(args.output)
        else:
            src_path = Path(args.file)
            if not src_path.exists():
                print(f"Error: file not found: {args.file}", file=sys.stderr); sys.exit(2)
            source   = src_path.read_text(encoding='utf-8')
            out_path = src_path.with_suffix('.mid') if args.output is None \
                       else Path(args.output)
    except IOError as e:
        print(f"IO error: {e}", file=sys.stderr); sys.exit(2)

    # Validate
    if not args.no_validate:
        if not validate_source(source):
            sys.exit(3)

    # Parse
    parser = MMDParser()
    try:
        parser.parse(source)
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr); sys.exit(1)

    if not parser.tracks:
        print("Error: no pitched tracks (T1, T2, …) found.", file=sys.stderr); sys.exit(1)

    # Build + write MIDI
    try:
        midi = build_midi(parser, ticks_per_beat=args.ticks)
        with open(out_path, 'wb') as f:
            midi.writeFile(f)
        track_list = ', '.join(sorted(parser.tracks))
        total_events = sum(len(v) for v in parser.tracks.values())
        print(f"✓  Wrote {out_path}  "
              f"({len(parser.tracks)} track(s): {track_list} | "
              f"{total_events} note(s) | {parser.bpm} BPM)")
    except Exception as e:
        print(f"MIDI write error: {e}", file=sys.stderr); sys.exit(1)

if __name__ == '__main__':
    main()
