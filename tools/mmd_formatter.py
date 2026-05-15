#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 km-vibecoder
"""
Musical Markdown (.mmd) Formatter
Modes:
    --expand    (HRExpand)   Align tracks into visual columns using whitespace.
    --condense  (AICondense) Strip all non-functional whitespace for token efficiency.
"""
import sys
import re
import argparse

def strip_comment(line: str) -> str:
    depth = 0
    for i, ch in enumerate(line):
        if ch in ('(', '['): depth += 1
        elif ch in (')', ']'): depth -= 1
        elif ch == '#' and depth == 0 and i > 0 and line[i-1] in (' ', '\t'):
            return line[:i].rstrip()
    return line

def condense(source: str) -> str:
    lines = source.splitlines()
    out = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith('#') or s == '---':
            out.append(s)
            continue
        if s.startswith('@'):
            out.append(re.sub(r'\s*:\s*', ':', s))
            continue
        # For track lines and commands, strip all internal spaces
        # except inside lyric tracks (which we should handle carefully)
        if re.match(r'^[TLPCtlpc]\d+\s*:', s):
            prefix, body = s.split(':', 1)
            # Remove whitespace but preserve it in lyrics if needed?
            # Spec says whitespace is insignificant everywhere except inside tokens.
            # For lyrics, L1: Hel- ; lo ; world;
            # Actually L tracks use ; as beat separators too.
            condensed_body = re.sub(r'\s+', '', body)
            out.append(f"{prefix.upper()}:{condensed_body}")
        elif s.startswith('['):
            out.append(re.sub(r'\s+', '', s))
        else:
            # Continuation line
            out.append(re.sub(r'\s+', '', s))
    return '\n'.join(out)

def expand(source: str) -> str:
    lines = source.splitlines()
    
    # 1. Parse into a grid of [Measure][Track][BeatSlot]
    # We need to preserve header/comments/commands in order.
    
    processed = []
    track_data = {} # {track_name: [[measure_slots]]}
    track_order = []
    
    # Initial pass to group track lines
    for line in lines:
        comment = ""
        if ' #' in line:
            line, comment = line.rsplit(' #', 1)
            comment = " #" + comment
            
        s = line.strip()
        if not s or s.startswith('#') or s == '---' or s.startswith('@') or (s.startswith('[') and ']' in s and not re.match(r'^[TLPC]\d+', s)):
            processed.append({'type': 'meta', 'content': s + comment})
            continue
            
        m_track = re.match(r'^([TLPC]\d+)\s*:(.+)$', s, re.I)
        m_cont = re.match(r'^\s*\|(.+)$', s)
        
        if m_track:
            name = m_track.group(1).upper()
            body = m_track.group(2)
            if name not in track_data:
                track_data[name] = []
                track_order.append(name)
            
            # Split by measures
            measures = [m.strip() for m in body.split('|') if m.strip()]
            for m in measures:
                # Split by beats
                slots = [slot.strip() for slot in m.split(';')]
                track_data[name].append(slots)
            processed.append({'type': 'track_placeholder', 'name': name})
        else:
            processed.append({'type': 'meta', 'content': line}) # Unrecognized

    # 2. Determine max width for every beat slot in every measure
    # Find max measures
    if not track_data: return source
    
    max_measures = max(len(v) for v in track_data.values())
    measure_widths = [] # List of lists: [measure_idx][beat_idx] = max_width
    
    for m_idx in range(max_measures):
        # Find max beats in this measure across all tracks
        max_beats = 0
        for name in track_order:
            if m_idx < len(track_data[name]):
                max_beats = max(max_beats, len(track_data[name][m_idx]))
        
        widths = [0] * max_beats
        for b_idx in range(max_beats):
            for name in track_order:
                if m_idx < len(track_data[name]) and b_idx < len(track_data[name][m_idx]):
                    widths[b_idx] = max(widths[b_idx], len(track_data[name][m_idx][b_idx]))
        measure_widths.append(widths)

    # 3. Reconstruct
    final_output = []
    track_cursors = {name: 0 for name in track_order}
    
    # We want to keep blocks of tracks together as they appeared.
    # This is a bit complex if tracks are interleaved with meta.
    # Simple approach: If we hit a track_placeholder, output the full measure for all active tracks?
    # No, usually MMD has T1, T2, T3 for Measure 1-4, then Meta, then T1, T2, T3 for Measure 5-8.
    
    # Let's group track placeholders that are contiguous
    i = 0
    while i < len(processed):
        item = processed[i]
        if item['type'] == 'meta':
            final_output.append(item['content'])
            i += 1
        else:
            # Group contiguous track definitions
            group = []
            while i < len(processed) and processed[i]['type'] == 'track_placeholder':
                if processed[i]['name'] not in [g['name'] for g in group]:
                    group.append(processed[i])
                i += 1
            
            # Determine how many measures to output for this group
            # We'll output until we hit a measure count boundary if we had one,
            # but for simplicity, let's just output the next measure for each.
            
            # Find how many measures are "available" for all in this group
            # In most MMD, they have same count per block.
            names = [g['name'] for g in group]
            
            # We'll just do one measure at a time for the group
            # Need to know how many measures were in the original block. 
            # This logic is getting complex. Let's simplify:
            # Reconstruct track-by-track but aligned.
            
            # Better: for each track in group, format their next measure.
            # But wait, T1: M1 | M2 \n T2: M1 | M2 is common.
            # If we see T1 followed by T2, they are simultaneous.
            
            # Let's just output the formatted lines for the group
            # To do this correctly we need to know how many measures were on that line.
            # For now, let's just output one measure per line for alignment demo.
            
            # Process all measures available for this group
            # We assume all tracks in the group have the same number of measures
            # (which is required by the spec).
            num_measures = max(len(track_data[name]) for name in names)
            
            # For each measure index in the group
            while any(track_cursors[name] < len(track_data[name]) for name in names):
                for name in names:
                    m_idx = track_cursors[name]
                    if m_idx < len(track_data[name]):
                        slots = track_data[name][m_idx]
                        widths = measure_widths[m_idx]
                        
                        formatted_slots = []
                        for b_idx, slot in enumerate(slots):
                            # Handle cases where some tracks might have fewer slots than max_beats
                            w = widths[b_idx] if b_idx < len(widths) else 0
                            formatted_slots.append(slot.ljust(w))
                        
                        line = f"{name}: " + " ; ".join(formatted_slots) + " |"
                        final_output.append(line)
                        track_cursors[name] += 1
                # Add a blank line between blocks of simultaneous measures if there are more
                # but only if we are not at the end. Actually, MMD usually groups
                # T1-T3 for M1, then T1-T3 for M2? Or T1: M1|M2.
                # Let's keep them together for now.
                    
    return '\n'.join(final_output)

def main():
    ap = argparse.ArgumentParser(description='Musical Markdown Formatter')
    ap.add_argument('file', nargs='?', default='-')
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--expand', action='store_true', help='HRExpand: visual alignment')
    group.add_argument('--condense', action='store_true', help='AICondense: character efficiency')
    args = ap.parse_args()

    try:
        src = sys.stdin.read() if args.file == '-' else open(args.file, encoding='utf-8').read()
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    if args.condense:
        print(condense(src))
    else:
        print(expand(src))

if __name__ == '__main__':
    main()
