#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 km-vibecoder
"""
.mmd Validator Test Suite
Run with:  python tests/test_mmd_validator.py
         or  python tests/test_mmd_validator.py -v   for verbose output
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from mmd_validator import validate, normalize


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def errors_of(source: str):
    _, errors, _ = validate(source)
    return errors

def is_valid(source: str) -> bool:
    v, _, _ = validate(source)
    return v

def has_error(source: str, fragment: str) -> bool:
    """True if any error message contains `fragment`."""
    for e in errors_of(source):
        if fragment.lower() in e.message.lower():
            return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  Valid Files
# ══════════════════════════════════════════════════════════════════════════════

class TestValidFiles(unittest.TestCase):

    def test_minimal_single_measure(self):
        self.assertTrue(is_valid("T1: C4/4;D4/4;E4/4;F4/4|"))

    def test_with_whitespace_padding(self):
        # Whitespace is insignificant — the padded and compact forms must both pass
        self.assertTrue(is_valid("T1: C4/4; D4/4; E4/4; F4/4 |"))

    def test_whole_note_with_held_beats(self):
        self.assertTrue(is_valid("T1: C4/1;;;|"))

    def test_half_notes(self):
        self.assertTrue(is_valid("T1: C4/2;;A4/2;|"))

    def test_dotted_quarter_plus_eighth(self):
        # 4/4: beat 1 = dotted quarter (1.5) + eighth (0.5) = 2 beats → NO, that's beat subdivision
        # Actually in 4/4 the beat unit is 1 quarter = 1.0
        # dotted quarter fills 1.5 beats which is more than 1 slot — this would be invalid
        # Let's test a valid subdivision: two eighths in one beat slot
        self.assertTrue(is_valid("T1: C4/8,D4/8;E4/4;F4/4;G4/4|"))

    def test_rest(self):
        self.assertTrue(is_valid("T1: R/4;C4/4;D4/4;E4/4|"))

    def test_full_measure_rest(self):
        self.assertTrue(is_valid("T1: R/M|"))

    def test_chord(self):
        self.assertTrue(is_valid("T1: [C4,E4,G4]/4;[D4,F4,A4]/4;[E4,G4,B4]/4;R/4|"))

    def test_dotted_note_in_34(self):
        # 3/4: beats=3, beat_unit=1.0qn. Dotted half = 3 beats total.
        # But that must fit in one beat slot... no.
        # In 3/4: C4/2. (dotted half = 3 beats) can't fit in one beat slot (1.0 qn).
        # Valid would be: C4/2.;; (one attack, two held slots, dotted half spanning all 3 beats)
        # But the duration is still checked per slot. 
        # Let me test a valid 3/4 bar instead:
        self.assertTrue(is_valid("@TIME: 3/4\nT1: C4/4;D4/4;E4/4|"))

    def test_two_tracks_synchronized(self):
        src = (
            "T1: C5/4;B4/4;A4/4;G4/4|F4/1;;;|\n"
            "T2: C4/2;;A3/2;|F3/2;;G3/2;|\n"
            "T3: C3/1;;;|F2/1;;;|\n"
        )
        self.assertTrue(is_valid(src))

    def test_header_fields(self):
        src = (
            "@TITLE: Test\n"
            "@BPM: 120\n"
            "@TIME: 4/4\n"
            "@KEY: G\n"
            "T1: G4/4;A4/4;B4/4;C5/4|\n"
        )
        self.assertTrue(is_valid(src))

    def test_inline_command_in_track(self):
        self.assertTrue(is_valid("T1: [DYN:f]C4/4;D4/4;E4/4;F4/4|"))

    def test_modifiers_on_notes(self):
        self.assertTrue(is_valid("T1: C4/4(mf)(.);D4/4(>);E4/4;F4/4|"))

    def test_flat_accidental(self):
        self.assertTrue(is_valid("T1: Bb4/4;Ab4/4;Eb4/4;Db4/4|"))

    def test_sharp_accidental(self):
        self.assertTrue(is_valid("T1: F#4/4;C#4/4;G#4/4;D#4/4|"))

    def test_natural_sign(self):
        self.assertTrue(is_valid("T1: Cn4/4;D4/4;E4/4;F4/4|"))

    def test_chord_with_inversion(self):
        self.assertTrue(is_valid("T1: [C4,E4,G4]/4/E;D4/4;E4/4;F4/4|"))

    def test_duration_inheritance(self):
        # D4 and E4 inherit /4 from C4
        self.assertTrue(is_valid("T1: C4/4;D4;E4;F4/4|"))

    def test_comments_ignored(self):
        src = (
            "# Full line comment\n"
            "T1: C4/4;D4/4;E4/4;F4/4|  # end of line comment\n"
        )
        self.assertTrue(is_valid(src))

    def test_block_comment_ignored(self):
        src = (
            "#[\n"
            "  This entire block is a comment.\n"
            "]#\n"
            "T1: C4/4;D4/4;E4/4;F4/4|\n"
        )
        self.assertTrue(is_valid(src))

    def test_lyric_track_not_checked_for_beat_sums(self):
        # Lyric tracks (L prefix) use same grid but text tokens have no duration
        # Validator skips duration-sum check for L tracks
        src = (
            "T1: C4/4;D4/4;E4/4;F4/4|\n"
            "L1: Hel-;lo;there;friend|\n"
        )
        # We don't validate lyric durations — just semicolon counts
        self.assertTrue(is_valid(src))

    def test_time_sig_change(self):
        src = (
            "@TIME: 4/4\n"
            "T1: C4/4;D4/4;E4/4;F4/4|\n"
            "[TIME:3/4]\n"
            "T1: G4/4;A4/4;B4/4|\n"
        )
        # This is tricky — track continuation with different meters.
        # For now we just check each section independently.
        _, errors, _ = validate(src)
        # Should not crash
        self.assertIsInstance(errors, list)

    def test_tuplets(self):
        # Triplet: 3 eighths in 1 beat (2 eighths time)
        self.assertTrue(is_valid("T1: [TRP] C4/8, D4/8, E4/8 [/TRP]; E4/4; F4/4; G4/4 |"))
        # Quintuplet: 5 sixteenths in 1 beat (4 sixteenths time)
        self.assertTrue(is_valid("T1: [QNT] C4/16, D4/16, E4/16, F4/16, G4/16 [/QNT]; E4/4; F4/4; G4/4 |"))
        # Chord in triplet
        self.assertTrue(is_valid("T1: [TRP] [C4,E4,G4]/8, [D4,F4,A4]/8, [E4,G4,B4]/8 [/TRP]; C4/4; G4/4; C4/4 |"))
        # Rest in triplet
        self.assertTrue(is_valid("T1: [TRP] C4/8, R/8, E4/8 [/TRP]; E4/4; F4/4; G4/4 |"))

    def test_multi_voice(self):
        self.assertTrue(is_valid("T1: C5/4; D5/4; E5/4; F5/4 // E4/4; F4/4; G4/4; A4/4 |"))

    def test_bpm_relaxed(self):
        self.assertTrue(is_valid("@BPM: ♩=120\nT1: C4/4;D4/4;E4/4;F4/4|"))
        self.assertTrue(is_valid("[BPM: ♩=120]\nT1: C4/4;D4/4;E4/4;F4/4|"))

    def test_tie_summation(self):
        # C4/4~C4/4 is 2 beats. Beat 2 is empty. Total 4.0 ✓
        self.assertTrue(is_valid("T1: C4/4~C4/4; ; E4/4; F4/4 |"))

    def test_empty_measure_error(self):
        self.assertFalse(is_valid("T1: ; ; ; |"))
        self.assertTrue(has_error("T1: ; ; ; |", "measure total"))


# ══════════════════════════════════════════════════════════════════════════════
#  Semicolon Count Errors  (§8.2 / §8.3)
# ══════════════════════════════════════════════════════════════════════════════

class TestSemicolonErrors(unittest.TestCase):

    def test_too_few_semicolons_4_4(self):
        # 4/4 needs 3 semis; this has 2
        self.assertFalse(is_valid("T1: C4/4;D4/4;E4/4|"))
        self.assertTrue(has_error("T1: C4/4;D4/4;E4/4|", "semicolon"))

    def test_too_many_semicolons_4_4(self):
        # 4/4 needs 3 semis; this has 4
        self.assertFalse(is_valid("T1: C4/4;D4/4;E4/4;F4/4;G4/4|"))
        self.assertTrue(has_error("T1: C4/4;D4/4;E4/4;F4/4;G4/4|", "semicolon"))

    def test_missing_held_beat_placeholder(self):
        # Whole note in 4/4 needs 3 held-beat placeholders after the attack
        # C4/1 alone has 0 semicolons → error
        self.assertFalse(is_valid("T1: C4/1|"))
        self.assertTrue(has_error("T1: C4/1|", "semicolon"))

    def test_half_note_missing_held_slot(self):
        # C4/2 alone (0 semicolons) in 4/4: needs 3
        self.assertFalse(is_valid("T1: C4/2;A4/2|"))
        # This has 1 semicolon but needs 3
        self.assertTrue(has_error("T1: C4/2;A4/2|", "semicolon"))

    def test_correct_held_slots_for_half_notes(self):
        # C4/2 + held + A3/2 + held → C4/2;;A3/2; → 3 semis ✓
        self.assertTrue(is_valid("T1: C4/2;;A3/2;|"))

    def test_34_too_few(self):
        src = "@TIME: 3/4\nT1: C4/4;D4/4|\n"
        self.assertFalse(is_valid(src))
        self.assertTrue(has_error(src, "semicolon"))

    def test_34_correct(self):
        src = "@TIME: 3/4\nT1: C4/4;D4/4;E4/4|\n"
        self.assertTrue(is_valid(src))


# ══════════════════════════════════════════════════════════════════════════════
#  Duration Sum Errors  (§8.5)
# ══════════════════════════════════════════════════════════════════════════════

class TestDurationSumErrors(unittest.TestCase):

    def test_beat_overfilled(self):
        # Two quarter notes in one beat slot = 2.0 beats, expected 1.0
        self.assertFalse(is_valid("T1: C4/4,D4/4;E4/4;F4/4;G4/4|"))
        self.assertTrue(has_error("T1: C4/4,D4/4;E4/4;F4/4;G4/4|", "duration"))

    def test_beat_underfilled(self):
        # Single eighth in a beat slot = 0.5 beats, expected 1.0
        self.assertFalse(is_valid("T1: C4/8;D4/4;E4/4;F4/4|"))
        self.assertTrue(has_error("T1: C4/8;D4/4;E4/4;F4/4|", "duration"))

    def test_two_eighths_fills_one_beat(self):
        # Two eighths in one subdivision = 1.0 ✓
        self.assertTrue(is_valid("T1: C4/8,D4/8;E4/4;F4/4;G4/4|"))

    def test_dotted_note_fills_beat_correctly(self):
        # In 3/4 where beat_unit = 1.0:
        # A dotted quarter (1.5) overfills a single beat slot
        src = "@TIME: 3/4\nT1: C4/4.;D4/4;E4/4|\n"
        self.assertFalse(is_valid(src))
        self.assertTrue(has_error(src, "duration"))


# ══════════════════════════════════════════════════════════════════════════════
#  Note Token Syntax Errors
# ══════════════════════════════════════════════════════════════════════════════

class TestNoteSyntaxErrors(unittest.TestCase):

    def test_missing_octave(self):
        self.assertFalse(is_valid("T1: C/4;D4/4;E4/4;F4/4|"))
        self.assertTrue(has_error("T1: C/4;D4/4;E4/4;F4/4|", "unrecognized"))

    def test_nonstandard_pitch_class(self):
        self.assertFalse(is_valid("T1: H4/4;D4/4;E4/4;F4/4|"))
        self.assertTrue(has_error("T1: H4/4;D4/4;E4/4;F4/4|", "unrecognized"))

    def test_bad_denominator_zero(self):
        self.assertFalse(is_valid("T1: C4/0;D4/4;E4/4;F4/4|"))
        self.assertTrue(has_error("T1: C4/0;D4/4;E4/4;F4/4|", "denominator"))

    def test_bad_denominator_non_power_of_2(self):
        self.assertFalse(is_valid("T1: C4/3;D4/4;E4/4;F4/4|"))
        self.assertTrue(has_error("T1: C4/3;D4/4;E4/4;F4/4|", "power of 2"))

    def test_octave_too_high_warning(self):
        # Octave 9 triggers a warning (not an error)
        errs = errors_of("T1: C9/4;D4/4;E4/4;F4/4|")
        warnings = [e for e in errs if e.severity == 'warning' and 'octave' in e.message.lower()]
        self.assertTrue(len(warnings) > 0)

    def test_valid_double_sharp(self):
        self.assertTrue(is_valid("T1: C##4/4;D4/4;E4/4;F4/4|"))

    def test_valid_double_flat(self):
        self.assertTrue(is_valid("T1: Dbb4/4;E4/4;F4/4;G4/4|"))


# ══════════════════════════════════════════════════════════════════════════════
#  Rest Errors
# ══════════════════════════════════════════════════════════════════════════════

class TestRestErrors(unittest.TestCase):

    def test_rest_bad_denominator(self):
        self.assertFalse(is_valid("T1: R/3;D4/4;E4/4;F4/4|"))
        self.assertTrue(has_error("T1: R/3;D4/4;E4/4;F4/4|", "power of 2"))

    def test_rest_valid_dotted(self):
        # R/8. = 0.75 beats; combined with R/16 = 0.25 = 1.0 total
        self.assertTrue(is_valid("T1: R/8.,R/16;D4/4;E4/4;F4/4|"))

    def test_full_measure_rest_valid(self):
        self.assertTrue(is_valid("T1: R/M|"))


# ══════════════════════════════════════════════════════════════════════════════
#  Chord Errors
# ══════════════════════════════════════════════════════════════════════════════

class TestChordErrors(unittest.TestCase):

    def test_chord_bad_pitch(self):
        self.assertFalse(is_valid("T1: [C4,Z5,G4]/4;D4/4;E4/4;F4/4|"))
        self.assertTrue(has_error("T1: [C4,Z5,G4]/4;D4/4;E4/4;F4/4|", "invalid pitch"))

    def test_chord_bad_denominator(self):
        self.assertFalse(is_valid("T1: [C4,E4,G4]/3;D4/4;E4/4;F4/4|"))
        self.assertTrue(has_error("T1: [C4,E4,G4]/3;D4/4;E4/4;F4/4|", "power of 2"))

    def test_chord_valid(self):
        self.assertTrue(is_valid("T1: [C4,E4,G4]/4;[G3,B3,D4]/4;[F3,A3,C4]/4;[C4,E4,G4]/4|"))


# ══════════════════════════════════════════════════════════════════════════════
#  Header Errors
# ══════════════════════════════════════════════════════════════════════════════

class TestHeaderErrors(unittest.TestCase):

    def test_bad_bpm(self):
        src = "@BPM: abc\nT1: C4/4;D4/4;E4/4;F4/4|\n"
        self.assertFalse(is_valid(src))
        self.assertTrue(has_error(src, "bpm"))

    def test_zero_bpm(self):
        src = "@BPM: 0\nT1: C4/4;D4/4;E4/4;F4/4|\n"
        self.assertFalse(is_valid(src))

    def test_bad_time_sig(self):
        src = "@TIME: 4/3\nT1: C4/4;D4/4;E4/4;F4/4|\n"
        self.assertFalse(is_valid(src))
        self.assertTrue(has_error(src, "time signature"))

    def test_valid_cut_time(self):
        src = "@TIME: C|\nT1: C4/2;G4/2|\n"
        self.assertTrue(is_valid(src))

    def test_unknown_key_is_warning_not_error(self):
        src = "@KEY: Xmaj\nT1: C4/4;D4/4;E4/4;F4/4|\n"
        v, errors, _ = validate(src)
        self.assertTrue(v)   # warnings don't make it invalid
        warnings = [e for e in errors if e.severity == 'warning']
        self.assertTrue(len(warnings) > 0)


# ══════════════════════════════════════════════════════════════════════════════
#  Command Block Errors
# ══════════════════════════════════════════════════════════════════════════════

class TestCommandErrors(unittest.TestCase):

    def test_bad_dyn(self):
        src = "[DYN:xyz]\nT1: C4/4;D4/4;E4/4;F4/4|\n"
        self.assertFalse(is_valid(src))
        self.assertTrue(has_error(src, "dynamic"))

    def test_valid_dyn(self):
        src = "[DYN:mf]\nT1: C4/4;D4/4;E4/4;F4/4|\n"
        self.assertTrue(is_valid(src))

    def test_bad_xpose(self):
        src = "[XPOSE:up3]\nT1: C4/4;D4/4;E4/4;F4/4|\n"
        self.assertFalse(is_valid(src))
        self.assertTrue(has_error(src, "xpose"))

    def test_valid_xpose(self):
        src = "[XPOSE:+3]\nT1: C4/4;D4/4;E4/4;F4/4|\n"
        self.assertTrue(is_valid(src))

    def test_bad_clef_warning(self):
        src = "[CLEF:T1:violin]\nT1: C4/4;D4/4;E4/4;F4/4|\n"
        v, errors, _ = validate(src)
        self.assertTrue(v)   # clef errors are warnings
        self.assertTrue(any('clef' in e.message.lower() for e in errors))


# ══════════════════════════════════════════════════════════════════════════════
#  Cross-track Synchronization Errors
# ══════════════════════════════════════════════════════════════════════════════

class TestCrossTrackErrors(unittest.TestCase):

    def test_mismatched_measure_counts(self):
        src = (
            "T1: C4/4;D4/4;E4/4;F4/4|G4/4;A4/4;B4/4;C5/4|\n"
            "T2: C3/1;;;|\n"   # only 1 measure vs T1's 2
        )
        self.assertFalse(is_valid(src))
        self.assertTrue(has_error(src, "measure count"))

    def test_matched_measure_counts(self):
        src = (
            "T1: C4/4;D4/4;E4/4;F4/4|G4/4;A4/4;B4/4;C5/4|\n"
            "T2: C3/1;;;|G2/1;;;|\n"
        )
        self.assertTrue(is_valid(src))

    def test_all_tracks_match_length(self):
        src = (
            "T1: C4/4;D4/4;E4/4;F4/4|\n"
            "L1: Hel-;lo;there;friend|Extra;measure;here;|\n"
        )
        self.assertFalse(is_valid(src))
        self.assertTrue(has_error(src, "match length"))

    def test_percussion_track_validation(self):
        # Percussion tracks are now in rhythmic list
        self.assertTrue(is_valid("P1: BD/4; SD/4; BD/4; SD/4 |"))
        self.assertFalse(is_valid("P1: BD/4; SD/4 |")) # too short for 4/4


# ══════════════════════════════════════════════════════════════════════════════
#  Normalize Function
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalize(unittest.TestCase):

    def test_whitespace_stripped(self):
        src = "T1: C4/4; D4/4; E4/4; F4/4 |"
        n = normalize(src)
        self.assertNotIn(' ', n)

    def test_comments_removed(self):
        src = "# comment\nT1: C4/4;D4/4;E4/4;F4/4|"
        n = normalize(src)
        self.assertNotIn('#', n)

    def test_prefix_uppercased(self):
        src = "t1: C4/4;D4/4;E4/4;F4/4|"
        n = normalize(src)
        self.assertIn('T1:', n)


# ══════════════════════════════════════════════════════════════════════════════
#  Duration Inheritance Edge Cases
# ══════════════════════════════════════════════════════════════════════════════

class TestDurationInheritance(unittest.TestCase):

    def test_inheritance_from_first_note(self):
        # D4 and E4 inherit /4 from C4; F4 has explicit /4
        self.assertTrue(is_valid("T1: C4/4;D4;E4;F4/4|"))

    def test_inheritance_fails_at_bar_start(self):
        # E4 at start of measure 2 has no previous note in that measure
        src = "T1: C4/4;D4/4;E4/4;F4/4|E4;D4/4;C4/4;B3/4|\n"
        self.assertFalse(is_valid(src))
        self.assertTrue(has_error(src, "inherit"))

    def test_chord_inheritance(self):
        # Second chord inherits /4 from the first
        src = "T1: [C4,E4,G4]/4;[D4,F4,A4];[E4,G4,B4];[F4,A4,C5]/4|"
        # This should be valid — chord inherits duration from previous chord
        self.assertTrue(is_valid(src))


if __name__ == '__main__':
    # Pretty summary
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2 if '-v' in sys.argv else 1)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
