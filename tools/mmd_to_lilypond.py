#!/usr/bin/env python3
"""
Musical Markdown (.mmd) → LilyPond (.ly) exporter  —  Spec v1.0 companion
Usage:
    python tools/mmd_to_lilypond.py score.mmd              # writes score.ly
    python tools/mmd_to_lilypond.py score.mmd -o out.ly    # explicit path
    python tools/mmd_to_lilypond.py score.mmd --no-validate

Render the resulting .ly with:
    lilypond score.ly          # → score.pdf + score.midi

Supported:  notes, rests (R/M), chords, ties, grace notes (acciaccatura /
            appoggiatura), dynamics, staccato / accent articulations,
            multi-track (one Staff per T-track), clef hints, inline
            [BPM] / [TIME] / [KEY] / [DYN] / [XPOSE] commands.
Not yet:    tuplets, slurs, repeats with voltas, dual-voice //.

Exit: 0=success  1=parse error  2=IO error  3=validation failure
Zero external dependencies (stdlib only).
"""
import re, sys, argparse
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

# ── Pitch conversion: SPN → LilyPond ─────────────────────────────────────────
_PC_TO_SEMI  = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
_SEMI_TO_PC  = {0:'C',1:'C#',2:'D',3:'D#',4:'E',5:'F',
                6:'F#',7:'G',8:'G#',9:'A',10:'A#',11:'B'}
_LY_PC       = {'C':'c','D':'d','E':'e','F':'f','G':'g','A':'a','B':'b'}
_LY_ACC      = {'#':'is','##':'isis','b':'es','bb':'eses','n':''}

def _octave_marks(octave:int) -> str:
    if octave >= 4:  return "'" * (octave - 3)
    if octave == 3:  return ''
    return "," * (3 - octave)

def spn_to_ly_pitch(pc:str, acc:str|None, octave:int, xpose:int=0) -> str:
    """Convert SPN note to a LilyPond pitch string, e.g. 'fis\\'' or 'bes,'."""
    if xpose == 0:
        # Preserve the original accidental spelling (flat stays flat, sharp stays sharp)
        return _LY_PC[pc.upper()] + _LY_ACC.get(acc or '', '') + _octave_marks(octave)
    # With transposition: convert to semitone and back (output uses sharps)
    semi = _PC_TO_SEMI[pc.upper()]
    if acc: semi += acc.count('#') - acc.count('b')
    semi = (octave + 1) * 12 + semi + xpose
    semi = max(0, min(127, semi))
    oct_out = semi // 12 - 1
    pc_out  = _SEMI_TO_PC[semi % 12]
    if len(pc_out) == 1:
        base_ly = _LY_PC[pc_out]
    else:
        base_ly = _LY_PC[pc_out[0]] + 'is'
    return base_ly + _octave_marks(oct_out)

# ── Duration conversion ───────────────────────────────────────────────────────
def dur_beats(denom:int, dots:str) -> Fraction:
    base = Fraction(4, denom)
    if dots == '..': return base * Fraction(7, 4)
    if dots == '.':  return base * Fraction(3, 2)
    return base

def beats_to_ly_dur(beats:Fraction) -> str:
    """Convert a duration in quarter-note beats to a LilyPond duration string."""
    for denom in [1, 2, 4, 8, 16, 32, 64]:
        base = Fraction(4, denom)
        if base == beats:            return str(denom)
        if base * Fraction(3,2) == beats: return str(denom) + '.'
        if base * Fraction(7,4) == beats: return str(denom) + '..'
    # Fallback: express as whole-note multiplier (e.g. 5/4 time full rest)
    frac = beats / 4
    return f"1*{frac.numerator}/{frac.denominator}"

# ── Key signature ─────────────────────────────────────────────────────────────
_KEY_MAP = {
    'C':'c','G':'g','D':'d','A':'a','E':'e','B':'b','F#':'fis','C#':'cis',
    'F':'f','Bb':'bes','Eb':'ees','Ab':'aes','Db':'des','Gb':'ges','Cb':'ces',
    'Am':'a','Em':'e','Bm':'b','F#m':'fis','C#m':'cis','G#m':'gis',
    'D#m':'dis','A#m':'ais','Dm':'d','Gm':'g','Cm':'c','Fm':'f',
    'Bbm':'bes','Ebm':'ees','Abm':'aes',
}

def key_to_ly(key:str) -> str:
    mode = 'minor' if key.endswith('m') else 'major'
    root = _KEY_MAP.get(key, 'c')
    return f'\\key {root} \\{mode}'

# ── Dynamic / articulation maps ───────────────────────────────────────────────
_DYN_LY  = {'ppp':'\\ppp','pp':'\\pp','p':'\\p','mp':'\\mp',
             'mf':'\\mf','f':'\\f','ff':'\\ff','fff':'\\fff'}
_ART_LY  = {'.':'-.','..':'-!','^':'-^','>':'->','-':'--'}

def extract_ly_mods(token:str) -> tuple[str, str]:
    """Return (dynamics_str, articulation_str) from a token's modifier list."""
    dyn = art = ''
    for m in re.finditer(r'\(([^)]*)\)', token):
        tag = m.group(1).strip()
        if tag in _DYN_LY:
            dyn = _DYN_LY[tag]
        elif tag == '+' and not dyn:
            dyn = '\\f'
        elif tag == '-' and not dyn:
            dyn = '\\p'
        elif tag in _ART_LY:
            art = _ART_LY[tag]
    return dyn, art

# ── Clef map ──────────────────────────────────────────────────────────────────
_CLEF_LY = {
    'treble':'treble','bass':'bass','alto':'alto','tenor':'tenor',
    'treble8vb':'treble_8','treble8va':'treble^8','percussion':'percussion',
}

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
NAMED_TIME = {'C':(4,4),'C|':(2,2)}
VALID_KEYS = {
    'C','G','D','A','E','B','F#','C#','F','Bb','Eb','Ab','Db','Gb','Cb',
    'Am','Em','Bm','F#m','C#m','G#m','D#m','A#m','Dm','Gm','Cm','Fm',
    'Bbm','Ebm','Abm','none'
}

def _parse_ts(val:str):
    if val in NAMED_TIME: return NAMED_TIME[val]
    m = re.match(r'^(\d+)/(\d+)$', val)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if a > 0 and b > 0: return a, b
    return None

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

# ── Beat-slot splitter (mirrors validator) ────────────────────────────────────
def _split_slot(slot:str) -> list[tuple[str,bool]]:
    tokens=[]; s=slot
    while s:
        if s.startswith('['):
            end=s.find(']')
            if end==-1: tokens.append((s,False)); break
            bk=s[:end+1]
            if RE_CMD.match(bk): tokens.append((bk,True)); s=s[end+1:]
            else:
                ce=_chord_end(s); tokens.append((s[:ce],False)); s=s[ce:]
                if s.startswith(','): s=s[1:]
        else:
            c=s.find(','); tokens.append((s if c==-1 else s[:c],False))
            if c==-1: break
            s=s[c+1:]
    return tokens

def _chord_end(s:str) -> int:
    i=0; depth=0
    while i<len(s):
        if s[i]=='[': depth+=1
        elif s[i]==']':
            depth-=1
            if depth==0: i+=1; break
        i+=1
    while i<len(s) and s[i] not in (',',';','|'):
        if s[i]=='(':
            e=s.find(')',i); i=e+1 if e!=-1 else len(s)
        else: i+=1
    return i

# ── LilyPond token builder ────────────────────────────────────────────────────
@dataclass
class LyEvent:
    tokens: list[str]             # LilyPond token(s); usually one, tuple for mid-measure cmds
    is_spacer: bool = False       # True for bar-check emitted between measures

def _parse_pitch_bare(p:str, xpose:int) -> str|None:
    """Parse a bare pitch like 'C#4' → LilyPond pitch string."""
    m = re.match(r'^([A-Ga-g])(#{1,2}|b{1,2}|n)?([0-9])$', p.strip())
    if not m: return None
    return spn_to_ly_pitch(m.group(1), m.group(2), int(m.group(3)), xpose)

def _token_to_ly(raw:str, last_dur:Fraction|None, xpose:int,
                 meas_dur:Fraction) -> tuple[list[str], Fraction|None]:
    """
    Convert one .mmd token to a list of LilyPond tokens.
    Returns (ly_tokens, updated_last_dur).
    An empty list means 'held beat — emit nothing'.
    """
    t = raw.strip()
    if not t: return [], last_dur

    # Grace note
    g = RE_GRACE.match(t)
    if g:
        is_appog = bool(g.group(1))
        cmd = '\\appoggiatura' if is_appog else '\\acciaccatura'
        # Parse the grace pitch(es)
        grace_body = _strip_ws(g.group(2))
        grace_tokens = []
        for gp in grace_body.split(','):
            gm = RE_NOTE.match(gp.strip())
            if gm:
                p = spn_to_ly_pitch(gm.group(1), gm.group(2), int(gm.group(3)), xpose)
                d = beats_to_ly_dur(dur_beats(int(gm.group(5)), gm.group(6) or '')) \
                    if gm.group(5) else '16'
                grace_tokens.append(f"{p}{d}")
        grace_str = f"{cmd} {{ {''.join(grace_tokens)} }}"
        # Parse principal note
        principal_tokens, ld = _token_to_ly(g.group(3), last_dur, xpose, meas_dur)
        if principal_tokens:
            principal_tokens[0] = grace_str + ' ' + principal_tokens[0]
        return principal_tokens, ld

    # Slur wrapper — strip and recurse (slur marking not emitted in v1)
    if t.startswith('<') and t.endswith('>'):
        return _token_to_ly(t[1:-1], last_dur, xpose, meas_dur)

    # Rest
    if t.startswith('R'):
        m = RE_REST.match(t)
        if not m: return [], last_dur
        if '/M' in t:
            d = beats_to_ly_dur(meas_dur)
            return [f'R{d}'], last_dur
        denom = int(m.group(2)); dots = m.group(3) or ''
        dur = dur_beats(denom, dots)
        return [f'r{beats_to_ly_dur(dur)}'], dur

    # Chord
    if t.startswith('['):
        m = RE_CHORD.match(t)
        if not m: return [], last_dur
        pitches = [_parse_pitch_bare(p, xpose) for p in m.group(1).split(',')]
        pitches = [p for p in pitches if p]
        ds = m.group(3); dots = (m.group(4) or '') if m.group(4) else ''
        dur = dur_beats(int(ds), dots) if ds else last_dur
        dyn, art = extract_ly_mods(t)
        dur_str = beats_to_ly_dur(dur) if dur else '4'
        chord_str = f"<{' '.join(pitches)}>{dur_str}{dyn}{art}"
        return [chord_str], dur

    # Tied note(s): C4/4~C4/4 — emit each note with ~ connector
    if '~' in t:
        parts = t.split('~')
        all_tokens = []; ld = last_dur
        for i, part in enumerate(parts):
            toks, ld = _token_to_ly(part, ld, xpose, meas_dur)
            if toks and i < len(parts) - 1:
                toks[-1] += '~'   # add tie connector after each note except the last
            all_tokens.extend(toks)
        return all_tokens, ld

    # Plain note
    m = RE_NOTE.match(t)
    if not m: return [], last_dur
    pc = m.group(1); acc = m.group(2); octave = int(m.group(3))
    ds = m.group(5); dots = m.group(6) or ''
    dur = dur_beats(int(ds), dots) if ds else last_dur
    pitch = spn_to_ly_pitch(pc, acc, octave, xpose)
    dur_str = beats_to_ly_dur(dur) if dur else '4'
    dyn, art = extract_ly_mods(t)
    return [f'{pitch}{dur_str}{dyn}{art}'], dur

# ── Parser ────────────────────────────────────────────────────────────────────
class MMDToLyParser:
    def __init__(self):
        # Header metadata
        self.title    = ''
        self.composer = ''
        self.arranger = ''
        self.bpm      = 120
        self.time_num = 4
        self.time_den = 4
        self.key      = 'C'
        self.track_labels: dict[str,str] = {}

        # Per-track state
        self.tracks: dict[str, list[list[str]]] = {}  # prefix → [[measure tokens], ...]
        self.clefs:  dict[str, str] = {}              # prefix → LilyPond clef string
        self.xpose  = 0
        self._cur_dyn = ''   # current global dynamic

        # Inline state changes per track (BPM/TIME/KEY changes mid-score)
        # Stored as (measure_index, ly_command) to inject at measure boundaries
        self.inline_cmds: dict[str, list[tuple[int,str]]] = {}

    # ── public entry point ────────────────────────────────────────────────────
    def parse(self, source:str):
        lines = source.splitlines()
        in_block = False; cur_track = None

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

            clean = _strip_ws(s)
            if RE_CMD.match(clean):
                self._apply_cmd(clean, None, None); cur_track = None; continue

            m = RE_TRACK.match(s)
            if m:
                cur_track = m.group(1).upper()
                self._parse_track_body(cur_track, m.group(2)); continue

            m = RE_CONT.match(s)
            if m and cur_track:
                self._parse_track_body(cur_track, m.group(1)); continue

    # ── header / command application ─────────────────────────────────────────
    def _apply_header(self, key:str, val:str):
        if key == 'TITLE':    self.title    = val
        elif key == 'COMPOSER': self.composer = val
        elif key == 'ARRANGER': self.arranger = val
        elif key == 'BPM' and val.isdigit(): self.bpm = int(val)
        elif key == 'TIME':
            r = _parse_ts(val)
            if r: self.time_num, self.time_den = r
        elif key == 'KEY' and val in VALID_KEYS: self.key = val
        elif key == 'TRACKS':
            # @TRACKS: T1=Right Hand, T2=Left Hand
            for part in val.split(','):
                part = part.strip()
                if '=' in part:
                    tn, label = part.split('=', 1)
                    self.track_labels[tn.strip().upper()] = label.strip()

    def _apply_cmd(self, tok:str, cur_track, meas_idx):
        m = RE_CMD.match(tok)
        if not m: return
        cmd = m.group(1).upper().lstrip('/'); val = (m.group(2) or '').strip()
        if cmd == 'BPM' and val.isdigit():
            self.bpm = max(1, int(val))
            if cur_track and meas_idx is not None:
                self._add_inline(cur_track, meas_idx, f'\\tempo {self.time_den} = {self.bpm}')
        elif cmd == 'TIME':
            r = _parse_ts(val)
            if r:
                self.time_num, self.time_den = r
                if cur_track and meas_idx is not None:
                    self._add_inline(cur_track, meas_idx, f'\\time {self.time_num}/{self.time_den}')
        elif cmd == 'KEY' and val in VALID_KEYS:
            self.key = val
            if cur_track and meas_idx is not None:
                self._add_inline(cur_track, meas_idx, key_to_ly(val))
        elif cmd == 'DYN' and val in _DYN_LY:
            self._cur_dyn = val
        elif cmd == 'XPOSE':
            xv = val.split(':')[0]
            if xv == '0': self.xpose = 0
            elif re.match(r'^[+-]\d+$', xv): self.xpose = int(xv)
        elif cmd == 'CLEF':
            parts = val.split(':')
            if len(parts) >= 2:
                tname = parts[0].upper()
                cname = parts[-1].lower()
                self.clefs[tname] = _CLEF_LY.get(cname, 'treble')

    def _add_inline(self, track:str, meas_idx:int, cmd_str:str):
        self.inline_cmds.setdefault(track, []).append((meas_idx, cmd_str))

    # ── track body parser ─────────────────────────────────────────────────────
    def _parse_track_body(self, prefix:str, body:str):
        if prefix[0] not in ('T',): return   # skip L, P, C tracks

        body = _strip_ws(_strip_comment(body))
        body = body.replace('|:', '|').replace(':|', '|')

        if prefix not in self.tracks:
            self.tracks[prefix] = []

        raw_measures = [s.strip('.').strip() for s in body.split('|') if s.strip('.').strip()]
        last_dur: Fraction|None = None

        for mb in raw_measures:
            meas_idx = len(self.tracks[prefix])
            meas_dur_beats = Fraction(self.time_num * 4, self.time_den)
            measure_tokens: list[str] = []

            # Dual-voice: take voice 1 only (before //)
            if '//' in mb:
                mb = mb.split('//')[0]

            # Full-measure rest
            if re.match(r'^R/M(\([^)]*\))*$', mb):
                d = beats_to_ly_dur(meas_dur_beats)
                measure_tokens.append(f'R{d}')
                self.tracks[prefix].append(measure_tokens)
                last_dur = None
                continue

            slots = mb.split(';')
            for slot in slots:
                slot = slot.strip()
                if not slot:
                    continue    # held-beat placeholder — no LilyPond output

                token_list = _split_slot(slot)
                for tok, is_cmd in token_list:
                    tok = tok.strip()
                    if not tok: continue
                    if is_cmd:
                        self._apply_cmd(tok, prefix, meas_idx)
                        # Inline command goes into the measure token stream
                        # (handled later during emit via inline_cmds)
                        continue
                    ly_toks, last_dur = _token_to_ly(tok, last_dur, self.xpose, meas_dur_beats)
                    measure_tokens.extend(ly_toks)

            self.tracks[prefix].append(measure_tokens)

    # ── LilyPond emitter ──────────────────────────────────────────────────────
    def emit(self) -> str:
        lines = ['\\version "2.24.0"']

        # \header block
        hdr = []
        if self.title:    hdr.append(f'  title = "{self.title}"')
        if self.composer: hdr.append(f'  composer = "{self.composer}"')
        if self.arranger: hdr.append(f'  arranger = "{self.arranger}"')
        if hdr:
            lines += ['\\header {'] + hdr + ['}']

        # Global tempo/time/key (used in each Staff preamble)
        tempo_str = f'\\tempo {self.time_den} = {self.bpm}'
        time_str  = f'\\time {self.time_num}/{self.time_den}'
        key_str   = key_to_ly(self.key) if self.key != 'none' else ''

        lines.append('\\score {')
        lines.append('  <<')

        for prefix in sorted(self.tracks):
            label   = self.track_labels.get(prefix, prefix)
            clef    = self.clefs.get(prefix, 'treble')
            measures = self.tracks[prefix]
            # Collect inline commands for this track
            icmds: dict[int, list[str]] = {}
            for midx, cmd_str in self.inline_cmds.get(prefix, []):
                icmds.setdefault(midx, []).append(cmd_str)

            lines.append(f'    \\new Staff \\with {{ instrumentName = "{label}" }} {{')
            lines.append(f'      \\clef {clef}')
            if key_str: lines.append(f'      {key_str}')
            lines.append(f'      {time_str}')
            lines.append(f'      {tempo_str}')

            for midx, mtoks in enumerate(measures):
                # Inject any inline commands that apply before this measure
                for icmd in icmds.get(midx, []):
                    lines.append(f'      {icmd}')
                # Emit measure notes + bar check
                bar = '      ' + ' '.join(mtoks) + ' |'
                lines.append(bar)

            lines.append('    }')

        lines.append('  >>')
        lines.append('  \\layout { }')
        lines.append('  \\midi { }')
        lines.append('}')

        return '\n'.join(lines)

# ── Validation ────────────────────────────────────────────────────────────────
def _validate(source:str) -> bool:
    try:
        import importlib.util
        sp = Path(__file__).parent / 'mmd_validator.py'
        spec = importlib.util.spec_from_file_location('mmd_validator', sp)
        mod  = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        valid, errors, _ = mod.validate(source)
        if not valid:
            n = sum(1 for e in errors if e.severity == 'error')
            print(f"Validation failed: {n} error(s). "
                  "Use --no-validate to skip.", file=sys.stderr)
            for e in errors:
                if e.severity == 'error':
                    parts = [p for p in [e.track,
                             f'M{e.measure}' if e.measure else None,
                             f'B{e.beat}' if e.beat else None] if p]
                    print(f"  ✗ {' '.join(parts) or 'global'}: {e.message}", file=sys.stderr)
        return valid
    except Exception as exc:
        print(f"Warning: could not run validator ({exc}).", file=sys.stderr)
        return True

# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(
        description='Convert a Musical Markdown (.mmd) file to LilyPond (.ly).')
    ap.add_argument('file', nargs='?', default='-',
                    help='Input .mmd file (or - for stdin)')
    ap.add_argument('-o', '--output', default=None,
                    help='Output .ly file (default: <input>.ly)')
    ap.add_argument('--no-validate', action='store_true',
                    help='Skip mmd_validator pre-check')
    args = ap.parse_args()

    try:
        if args.file == '-':
            source   = sys.stdin.read()
            out_path = Path('output.ly') if not args.output else Path(args.output)
        else:
            src = Path(args.file)
            if not src.exists():
                print(f"Error: not found: {args.file}", file=sys.stderr); sys.exit(2)
            source   = src.read_text(encoding='utf-8')
            out_path = src.with_suffix('.ly') if not args.output else Path(args.output)
    except IOError as e:
        print(f"IO error: {e}", file=sys.stderr); sys.exit(2)

    if not args.no_validate:
        if not _validate(source): sys.exit(3)

    parser = MMDToLyParser()
    try:
        parser.parse(source)
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr); sys.exit(1)

    if not parser.tracks:
        print("Error: no pitched tracks (T1, T2, …) found.", file=sys.stderr); sys.exit(1)

    ly_source = parser.emit()

    try:
        out_path.write_text(ly_source, encoding='utf-8')
        track_list = ', '.join(sorted(parser.tracks))
        total = sum(len(m) for t in parser.tracks.values() for m in t)
        print(f"✓  Wrote {out_path}  "
              f"({len(parser.tracks)} staff/staves: {track_list} | "
              f"{total} note token(s) | {parser.bpm} BPM)  "
              f"→ render with:  lilypond {out_path}")
    except IOError as e:
        print(f"IO error writing output: {e}", file=sys.stderr); sys.exit(2)

if __name__ == '__main__':
    main()
