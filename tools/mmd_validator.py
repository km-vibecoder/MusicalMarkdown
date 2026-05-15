#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 km-vibecoder
"""
Musical Markdown (.mmd) Syntax Validator  —  Spec v1.0 companion
Usage:
    python mmd_validator.py score.mmd              # human-readable
    python mmd_validator.py score.mmd --json       # JSON for LLM loops
    python mmd_validator.py score.mmd --normalize  # canonical form
    echo "T1: C4/4;D4/4;E4/4;F4/4|" | python mmd_validator.py -
Exit: 0=valid  1=errors  2=IO error
"""
import re, sys, json, argparse
from dataclasses import dataclass, field
from typing import Optional

# ── Data ──────────────────────────────────────────────────────────────────────
@dataclass
class Error:
    severity: str; track: Optional[str]; measure: Optional[int]
    beat: Optional[int]; message: str; raw: Optional[str] = None
    def to_dict(self):
        return {"severity":self.severity,"track":self.track,"measure":self.measure,
                "beat":self.beat,"message":self.message,"raw":self.raw}

@dataclass
class ParseState:
    time_num:int=4; time_den:int=4; key:str="C"; bpm:int=120
    measure_counts:dict=field(default_factory=dict)
    errors:list=field(default_factory=list)
    tuplet_stack:list=field(default_factory=list)
    last_dur:Optional[float]=None # unscaled duration for inheritance

# ── Patterns ──────────────────────────────────────────────────────────────────
RE_HEADER = re.compile(r'^@(\w+)\s*:\s*(.+)$')
RE_CMD    = re.compile(r'^\[([A-Z][A-Z0-9_/]*|/[A-Z][A-Z0-9_]*)(?::([^\]]*))?\]$')
RE_TRACK  = re.compile(r'^([TLPCtlpc]\d+)\s*:(.+)$')
RE_CONT   = re.compile(r'^\s*\|(.+)$')
RE_NOTE   = re.compile(r'^(~)?([A-Ga-g])(#{1,2}|b{1,2}|n)?([0-9])(/(\d+)(\.{0,2}))?(~)?(\([^)]*\))*$')
RE_REST   = re.compile(r'^R(/(\d+)(\.{0,2})|/M)?(\([^)]*\))*$')
RE_CHORD  = re.compile(r'^\[([^\]]+)\](/(\d+)(\.{0,2})?)?(/[A-Ga-g][#b]?)?(\([^)]*\))*$')
RE_GRACE  = re.compile(r'^\{(!)?([^}]+)\}(.+)$')

RE_TUPLET = re.compile(r'^\[(TUP:(\d+):(\d+)|TRP|QNT|SPT)\]$')
RE_TUPLET_END = re.compile(r'^\[/(TUP|TRP|QNT|SPT)\]$')

NAMED_TIME = {'C':(4,4),'C|':(2,2)}
VALID_KEYS = {'C','G','D','A','E','B','F#','C#','F','Bb','Eb','Ab','Db','Gb','Cb',
              'Am','Em','Bm','F#m','C#m','G#m','D#m','A#m','Dm','Gm','Cm','Fm','Bbm','Ebm','Abm','none'}
VALID_DYN  = {'ppp','pp','p','mp','mf','f','ff','fff'}
VALID_CLEF = {'treble','bass','alto','tenor','treble8vb','treble8va','percussion'}
VALID_TEMPO= {'accel','rit','rall','ato','rubato'}
PITCHED    = {'T', 'P'}   # track prefixes needing duration validation

# ── Duration helpers ──────────────────────────────────────────────────────────
def dur_qn(denom:int, dots:str) -> float:
    b = 4.0/denom
    return b*1.75 if dots=='..' else b*1.5 if dots=='.' else b

def beat_unit(st:ParseState) -> float: return 4.0/st.time_den
def meas_dur(st:ParseState)  -> float: return st.time_num*beat_unit(st)
def is_p2(n:int)             -> bool:  return n>0 and (n&(n-1))==0

def parse_ts(val:str):
    if val in NAMED_TIME: return NAMED_TIME[val]
    m=re.match(r'^(\d+)/(\d+)$',val)
    if m:
        a,b=int(m.group(1)),int(m.group(2))
        if a>0 and is_p2(b): return a,b
    return None

# ── Comment / whitespace ──────────────────────────────────────────────────────
def strip_comment(line:str) -> str:
    """Strip inline # only when preceded by whitespace (not in pitch names like F#4)."""
    depth=0
    for i,ch in enumerate(line):
        if ch in ('(','['): depth+=1
        elif ch in (')',']'): depth-=1
        elif ch=='#' and depth==0 and i>0 and line[i-1] in (' ','\t'):
            return line[:i].rstrip()
    return line

def strip_ws(s:str) -> str: return re.sub(r'[ \t]+','',s)

# ── Beat-slot token splitter ──────────────────────────────────────────────────
def split_slot(slot:str):
    """Return list of (token, is_command) from a single beat slot (no whitespace)."""
    tokens = []
    # Combined regex for all Musical Markdown tokens.
    # We stop at [ and { because they start blocks, and , ; | which are separators.
    pattern = re.compile(
        r'\[(TUP:[^\]]+|TRP|QNT|SPT)\]'
        r'|\[/(TUP|TRP|QNT|SPT)\]'
        r'|\[[A-Z][A-Z0-9_/]*(:[^\]]*)?\]'
        r'|\[[^\]]+\][^,;\|\[\{]*'
        r'|\{[^\}]+\}[^,;\|\[\{]*'
        r'|[^,;\|\[\{]+'
    )
    for m in pattern.finditer(slot):
        tok = m.group(0)
        is_cmd = False
        if tok.startswith('['):
            if RE_CMD.match(tok) or RE_TUPLET.match(tok) or RE_TUPLET_END.match(tok):
                is_cmd = True
        tokens.append((tok, is_cmd))
    return tokens

# ── Token validation ──────────────────────────────────────────────────────────
def val_token(raw:str, track:str, mnum:int, bnum:int, st:ParseState) -> Optional[float]:
    t=raw.strip()
    if not t: return 0.0

    # Slur markers < > and trailing commas (from split_slot over-match)
    t = t.lstrip('<').rstrip('>').rstrip(',')
    if not t: return 0.0

    # Grace note
    g=RE_GRACE.match(t)
    if g: return val_token(g.group(3),track,mnum,bnum,st)

    # Rest
    if t.startswith('R'):
        m=RE_REST.match(t)
        if not m:
            st.errors.append(Error('error',track,mnum,bnum,
                f"Malformed rest '{t}' — expected R/N, R/N., or R/M",t)); return None
        if '/M' in t: return meas_dur(st)

        raw_dur = None
        if m.group(2):
            d,dots=int(m.group(2)),(m.group(3) or '')
            if not is_p2(d):
                st.errors.append(Error('error',track,mnum,bnum,
                    f"Rest '{t}': denominator {d} is not a power of 2",t)); return None
            raw_dur = dur_qn(d,dots)
            st.last_dur = raw_dur
        elif st.last_dur is not None:
            raw_dur = st.last_dur
        else:
            st.errors.append(Error('error',track,mnum,bnum,
                f"Rest '{t}' has no duration and no previous note to inherit from",t)); return None

        dur = raw_dur
        if dur and st.tuplet_stack:
            actual, normal = st.tuplet_stack[-1]
            dur = dur * (normal / actual)
        return dur

    # Chord
    if t.startswith('['):
        m=RE_CHORD.match(t)
        if not m:
            st.errors.append(Error('error',track,mnum,bnum,
                f"Malformed chord '{t}' — expected [P,P,...]/dur",t)); return None
        for p in m.group(1).split(','):
            if not RE_NOTE.match(p.strip()+'/4'):
                st.errors.append(Error('error',track,mnum,bnum,
                    f"Invalid pitch '{p.strip()}' inside chord '{t}'",p.strip()))

        ds=m.group(3); dots=(m.group(4) or '') if m.group(4) else ''
        raw_dur = None
        if ds:
            d=int(ds)
            if not is_p2(d):
                st.errors.append(Error('error',track,mnum,bnum,
                    f"Chord '{t}': denominator {d} not a power of 2",t)); return None
            raw_dur = dur_qn(d,dots)
            st.last_dur = raw_dur
        elif st.last_dur is not None:
            raw_dur = st.last_dur
        else:
            st.errors.append(Error('error',track,mnum,bnum,
                f"Chord '{t}' has no duration and no previous note to inherit from",t)); return None

        dur = raw_dur
        if dur and st.tuplet_stack:
            actual, normal = st.tuplet_stack[-1]
            dur = dur * (normal / actual)
        return dur

    # Plain note
    base=t.split('~')[0]

    # Percussion tracks allow non-SPN identifiers (e.g. BD, SN)
    if track.startswith('P'):
        m = re.match(r'^(~)?([A-Z]+)(/(\d+)(\.{0,2}))?(~)?(\([^)]*\))*$', base)
        if not m:
            st.errors.append(Error('error',track,mnum,bnum,f"Malformed percussion token '{t}'",t)); return None
        ds = m.group(4); dots = (m.group(5) or '')
    else:
        m=RE_NOTE.match(base)
        if not m:
            st.errors.append(Error('error',track,mnum,bnum,
                f"Unrecognized token '{t}' — expected note (C4/4), rest (R/4), chord ([C4,E4]/4), or command ([BPM:120])",t))
            return None
        oct_=int(m.group(4)); ds=m.group(6); dots=(m.group(7) or '')
        if oct_>8:
            st.errors.append(Error('warning',track,mnum,bnum,
                f"Note '{t}': octave {oct_} exceeds standard piano range (max 8)",t))

    raw_dur = None
    if ds:
        d=int(ds)
        if d==0:
            st.errors.append(Error('error',track,mnum,bnum,
                f"Note '{t}': duration denominator cannot be 0",t)); return None
        if not is_p2(d):
            st.errors.append(Error('error',track,mnum,bnum,
                f"Note '{t}': denominator {d} not a power of 2 (valid: 1,2,4,8,16,32,64)",t)); return None
        raw_dur = dur_qn(d,dots)
        st.last_dur = raw_dur
    elif st.last_dur is not None:
        raw_dur = st.last_dur
    else:
        st.errors.append(Error('error',track,mnum,bnum,
            f"Note '{t}' has no duration and no previous note in this measure to inherit from",t)); return None

    # Handle tie sum if same-token tie like C4/4~C4/4
    if '~' in t:
        parts = [p for p in t.split('~') if p]
        if len(parts) > 1:
            total_raw_dur = 0.0; temp_last = st.last_dur
            for p in parts:
                m_p = RE_NOTE.match(p)
                if not m_p: continue
                p_ds = m_p.group(6); p_dots = m_p.group(7) or ''
                if p_ds:
                    p_dur = dur_qn(int(p_ds), p_dots); temp_last = p_dur
                elif temp_last is not None:
                    p_dur = temp_last
                else: p_dur = 0.0
                total_raw_dur += p_dur
            if total_raw_dur > 0:
                # Update st.last_dur to the LAST part of the tie?
                # Spec: inheritance carries last explicit duration.
                # If C4/4~C4/2, then last_dur should be 0.5 (quarter? no 0.5 is half).
                st.last_dur = temp_last
                dur = total_raw_dur
                if dur and st.tuplet_stack:
                    actual, normal = st.tuplet_stack[-1]
                    dur = dur * (normal / actual)
                return dur

    dur = raw_dur
    if dur and st.tuplet_stack:
        actual, normal = st.tuplet_stack[-1]
        dur = dur * (normal / actual)

    return dur


# ── Command validation ────────────────────────────────────────────────────────
def val_cmd(tok:str, track, mnum, bnum, st:ParseState):
    # Tuplet start
    mt = RE_TUPLET.match(tok)
    if mt:
        kind = mt.group(1)
        if kind == 'TRP':   st.tuplet_stack.append((3, 2))
        elif kind == 'QNT': st.tuplet_stack.append((5, 4))
        elif kind == 'SPT': st.tuplet_stack.append((7, 4))
        elif kind.startswith('TUP:'):
            parts = kind.split(':')
            st.tuplet_stack.append((int(parts[1]), int(parts[2])))
        return

    # Tuplet end
    me = RE_TUPLET_END.match(tok)
    if me:
        if st.tuplet_stack: st.tuplet_stack.pop()
        else: st.errors.append(Error('error',track,mnum,bnum,f"Mismatched tuplet end '{tok}'",tok))
        return

    m=RE_CMD.match(tok)
    if not m:
        st.errors.append(Error('error',track,mnum,bnum,f"Malformed command block '{tok}'",tok)); return
    cmd=m.group(1).upper().lstrip('/'); val=(m.group(2) or '').strip()

    if cmd=='BPM':
        # Allow numeric or common musical notation like ♩=120
        clean_val = val.replace('♩','').replace('=','').strip()
        if not clean_val.isdigit() or int(clean_val)<=0:
            st.errors.append(Error('error',track,mnum,bnum,f"[BPM:{val}]: must contain positive integer",tok))
    elif cmd=='TEMPO':
        if val.split(':')[0].lower() not in VALID_TEMPO:
            st.errors.append(Error('warning',track,mnum,bnum,
                f"[TEMPO:{val}]: unrecognized (valid: {','.join(sorted(VALID_TEMPO))})",tok))
    elif cmd=='TIME':
        r=parse_ts(val)
        if r is None:
            st.errors.append(Error('error',track,mnum,bnum,f"[TIME:{val}]: invalid time signature",tok))
        else: st.time_num,st.time_den=r
    elif cmd=='KEY':
        if val not in VALID_KEYS:
            st.errors.append(Error('warning',track,mnum,bnum,f"[KEY:{val}]: unrecognized key",tok))
    elif cmd=='DYN':
        if val not in VALID_DYN:
            st.errors.append(Error('error',track,mnum,bnum,
                f"[DYN:{val}]: invalid dynamic (valid: {','.join(sorted(VALID_DYN))})",tok))
    elif cmd in ('CRESC','DIM'):
        if not (val.split(':')[0]).isdigit():
            st.errors.append(Error('error',track,mnum,bnum,
                f"[{cmd}:{val}]: first arg must be measure count",tok))
    elif cmd=='XPOSE':
        xv=val.split(':')[0]
        if not re.match(r'^[+-]\d+$',xv) and xv!='0':
            st.errors.append(Error('error',track,mnum,bnum,f"[XPOSE:{val}]: expected +N, -N, or 0",tok))
    elif cmd=='CLEF':
        parts=val.split(':'); cn=parts[-1].lower() if parts else ''
        if cn not in VALID_CLEF:
            st.errors.append(Error('warning',track,mnum,bnum,f"[CLEF:{val}]: unrecognized clef '{cn}'",tok))
    # All other commands (REP, VOLTA, BLK, SECT, MUTE, 8VA, etc.) accepted silently

# ── Measure validation ────────────────────────────────────────────────────────
def val_measure(body:str, track:str, mnum:int, st:ParseState):
    # R/M (full-measure rest) is a special single-token measure — no semicolons needed
    stripped_body = body.strip().split('(')[0].strip()  # ignore modifiers for this check
    if stripped_body == 'R/M' or re.match(r'^R/M(\([^)]*\))*$', body.strip()):
        return   # valid by definition; no grid structure to check

    expected_semis = st.time_num-1
    is_pitched     = track[0].upper() in PITCHED
    bu = beat_unit(st); expected_total = meas_dur(st)

    voices = body.split('//')
    for vi, voice in enumerate(voices):
        actual_semis = voice.count(';')
        if actual_semis != expected_semis:
            st.errors.append(Error('error',track,mnum,None,
                f"Semicolon count (voice {vi+1}): got {actual_semis}, need {expected_semis} "
                f"for {st.time_num}/{st.time_den}. Use empty ';' for held beats.",voice[:80]))

        if not is_pitched: continue

        slots = voice.split(';'); meas_total=0.0
        st.tuplet_stack = [] # Reset tuplet stack for each voice
        st.last_dur = None   # Reset duration inheritance for each voice

        for bi,slot in enumerate(slots):
            bnum=bi+1; slot=slot.strip()
            if not slot: continue
            tlist=split_slot(slot); slot_total=0.0
            for tok,is_cmd in tlist:
                if is_cmd: val_cmd(tok,track,mnum,bnum,st); continue
                d=val_token(tok,track,mnum,bnum,st)
                if d is None or d==0.0: continue
                slot_total+=d
            
            note_toks = [tok for tok,is_cmd in tlist if not is_cmd and tok.strip()]
            if len(note_toks) > 1 and slot_total > bu+1e-6:
                st.errors.append(Error('error',track,mnum,bnum,
                    f"Beat slot {bnum} (voice {vi+1}) comma-subdivisions overfill one beat: {slot_total:.4f} QN "
                    f"but one beat = {bu:.4f} QN. Subdivisions must sum to exactly one beat.",slot))
            meas_total+=slot_total

        if abs(meas_total-expected_total)>1e-6:
            st.errors.append(Error('error',track,mnum,None,
                f"Measure total (voice {vi+1}) {meas_total:.4f} QN ≠ expected {expected_total:.4f} QN "
                f"({st.time_num}/{st.time_den}). Check durations and held-beat placeholders.",
                voice[:80]))

# ── Track line ────────────────────────────────────────────────────────────────
def val_track(prefix:str, body:str, st:ParseState):
    body=strip_ws(strip_comment(body))
    body=body.replace('|:','|').replace(':|','|')
    measures=[s.strip('.') for s in body.split('|') if s.strip('.').strip()]
    if not measures:
        st.errors.append(Error('warning',prefix,None,None,f"Track {prefix} has no measures",body[:80])); return
    base=st.measure_counts.get(prefix,0)
    st.measure_counts[prefix]=base+len(measures)
    for i,mb in enumerate(measures): val_measure(mb,prefix,base+i+1,st)

# ── Header ────────────────────────────────────────────────────────────────────
def val_header(key:str, val:str, st:ParseState):
    key=key.upper().strip(); val=val.strip()
    if key=='BPM':
        clean_val = val.replace('♩','').replace('=','').strip()
        if not clean_val.isdigit() or int(clean_val)<=0:
            st.errors.append(Error('error',None,None,None,f"@BPM must contain positive integer, got '{val}'",f"@BPM:{val}"))
        else: st.bpm=int(clean_val)
    elif key=='TIME':
        r=parse_ts(val)
        if r is None:
            st.errors.append(Error('error',None,None,None,f"@TIME '{val}' is not a valid time signature",f"@TIME:{val}"))
        else: st.time_num,st.time_den=r
    elif key=='KEY':
        if val not in VALID_KEYS:
            st.errors.append(Error('warning',None,None,None,f"@KEY '{val}' unrecognized",f"@KEY:{val}"))

# ── Main validator ────────────────────────────────────────────────────────────
def validate(source:str):
    st=ParseState(); lines=source.splitlines()
    in_block=False; cur_track=None

    for lno,raw in enumerate(lines,1):
        line=raw.rstrip()
        if '#[' in line: in_block=True
        if in_block:
            if ']#' in line: in_block=False
            continue
        s=line.strip()
        if not s or s=='---' or s.startswith('#AI:'): cur_track=(None if not s else cur_track); continue
        if s.startswith('#'): continue

        m=RE_HEADER.match(s)
        if m: val_header(m.group(1),m.group(2),st); cur_track=None; continue

        clean=strip_ws(s)
        if RE_CMD.match(clean): val_cmd(clean,None,None,None,st); cur_track=None; continue

        m=RE_TRACK.match(s)
        if m: cur_track=m.group(1).upper(); val_track(cur_track,m.group(2),st); continue

        m=RE_CONT.match(s)
        if m and cur_track: val_track(cur_track,m.group(1),st); continue

        st.errors.append(Error('warning',None,None,None,
            f"Line {lno}: unrecognized content '{s[:60]}'",s[:60]))

    # Cross-track consistency
    if len(st.measure_counts) > 1 and len(set(st.measure_counts.values())) > 1:
        d=', '.join(f"{t}={c}" for t,c in sorted(st.measure_counts.items()))
        st.errors.append(Error('error',None,None,None,
            f"Track measure counts inconsistent: {d}. All tracks must match length."))

    return not any(e.severity=='error' for e in st.errors), st.errors, st

# ── Formatters ────────────────────────────────────────────────────────────────
def fmt_text(errors,valid:bool) -> str:
    errs=sum(1 for e in errors if e.severity=='error')
    warns=sum(1 for e in errors if e.severity=='warning')
    if valid and not errors: return '✓  Valid .mmd — no issues found.'
    lines=[]
    lines.append(f'{"⚠" if valid else "✗"}  {"Valid .mmd with" if valid else "Invalid .mmd —"} '
                 f'{errs} error(s), {warns} warning(s).\n')
    for e in [e for e in errors if not e.track]:
        icon='✗' if e.severity=='error' else '⚠'
        lines.append(f'  {icon}  [global] {e.message}')
        if e.raw: lines.append(f'        → "{e.raw}"')
    seen=[]
    for e in errors:
        if e.track and e.track not in seen: seen.append(e.track)
    for tr in seen:
        lines.append(f'\n  Track {tr}:')
        for e in [e for e in errors if e.track==tr]:
            loc=(f'M{e.measure}' if e.measure else '')+(f' B{e.beat}' if e.beat else '')
            icon='✗' if e.severity=='error' else '⚠'
            lines.append(f'    {icon}  {"["+loc+"] " if loc else ""}{e.message}')
            if e.raw: lines.append(f'          → "{e.raw}"')
    return '\n'.join(lines)

def fmt_json(errors,valid:bool) -> str:
    return json.dumps({'valid':valid,
        'error_count':sum(1 for e in errors if e.severity=='error'),
        'warning_count':sum(1 for e in errors if e.severity=='warning'),
        'errors':[e.to_dict() for e in errors],
        'llm_hint':('Fix all severity=="error" items. Address structural errors first '
                    '(semicolon counts → measure totals → token syntax). Re-run after each fix.'
                    if not valid else 'File is valid.')},indent=2)

def normalize(source:str) -> str:
    out=[]
    for line in source.splitlines():
        line=line.strip()
        if not line or line.startswith('#') or line=='---': continue
        if line.startswith('@'): out.append(line); continue
        m=RE_TRACK.match(line)
        if m: out.append(f'{m.group(1).upper()}:{strip_ws(strip_comment(m.group(2)))}'); continue
        out.append(strip_ws(line))
    return '\n'.join(out)

# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    ap=argparse.ArgumentParser(description='.mmd Musical Markdown validator')
    ap.add_argument('file',nargs='?',default='-')
    ap.add_argument('--json',action='store_true')
    ap.add_argument('--normalize',action='store_true')
    args=ap.parse_args()
    try:
        src=sys.stdin.read() if args.file=='-' else open(args.file,encoding='utf-8').read()
    except FileNotFoundError: print(f'Error: not found: {args.file}',file=sys.stderr); sys.exit(2)
    except IOError as e:      print(f'IO error: {e}',file=sys.stderr); sys.exit(2)
    if args.normalize: print(normalize(src)); sys.exit(0)
    valid,errors,_=validate(src)
    print(fmt_json(errors,valid) if args.json else fmt_text(errors,valid))
    sys.exit(0 if valid else 1)

if __name__=='__main__': main()
