# Using the .mmd Validator in an LLM Feedback Loop

## The Problem

LLMs have no .mmd examples in their training data. They understand the spec when
it is placed in the prompt, but their first attempts will commonly contain:

- Wrong semicolon counts (forgetting held-beat placeholders)
- Wrong duration fractions (choosing /3 instead of /4, etc.)
- Sharp signs in pitch names (`F#`) accidentally treated as comments
- Measure-length errors (notes not summing to the time signature total)
- Desynchronized tracks (T1 and T2 with different measure counts)

The validator is a **deterministic oracle** that catches all of these. The workflow
below turns every generation attempt into a tight feedback loop: generate → validate
→ fix → repeat, until the file passes. In practice this converges in 1–3 rounds.

---

## Quick Reference

```bash
# Install: no external dependencies — Python 3.9+ stdlib only
python mmd_validator.py score.mmd            # human-readable report
python mmd_validator.py score.mmd --json     # structured JSON for LLM feedback
python mmd_validator.py score.mmd --normalize  # canonical (whitespace-free) form
echo "T1: C4/4;D4/4;E4/4;F4/4|" | python mmd_validator.py -  # from stdin

# Exit codes
#   0  valid (may have warnings)
#   1  one or more errors
#   2  file not found / IO error
```

---

## Workflow A — Single-Turn LLM Request (Simplest)

Use this when calling an LLM API once per iteration.

### Step 1 — System prompt

Include the full .mmd specification **plus** this validation contract:

```
You are a musical notation assistant that writes .mmd (Musical Markdown) files.
After generating a .mmd file, it will be run through a syntax validator.
The validator returns a JSON object:

{
  "valid": true | false,
  "error_count": N,
  "errors": [
    {
      "severity": "error" | "warning",
      "track": "T1" | null,
      "measure": 3 | null,
      "beat": 2 | null,
      "message": "human-readable description",
      "raw": "the offending token"
    }
  ]
}

Rules:
1. A file is only finished when "valid": true.
2. Fix ALL "severity": "error" items before considering the file done.
3. Warnings are optional but preferred to resolve.
4. Fix errors in this priority order:
   a. Global / cross-track errors (measure count mismatches)
   b. Semicolon count errors (wrong beat-slot structure)
   c. Measure-total duration errors (notes don't sum to measure length)
   d. Individual token syntax errors (bad pitch, bad denominator, etc.)
```

### Step 2 — Generation loop (pseudocode)

```python
import subprocess, json, tempfile, os

SYSTEM_PROMPT = open('spec.mmd.md').read() + VALIDATION_CONTRACT

def validate(mmd_text: str) -> dict:
    with tempfile.NamedTemporaryFile(suffix='.mmd', mode='w', delete=False) as f:
        f.write(mmd_text); fname = f.name
    result = subprocess.run(
        ['python', 'mmd_validator.py', fname, '--json'],
        capture_output=True, text=True)
    os.unlink(fname)
    return json.loads(result.stdout)

def generate_mmd(user_request: str, previous_attempt: str = None,
                 errors: list = None) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({"role": "user", "content": user_request})
    if previous_attempt and errors:
        messages.append({"role": "assistant", "content": previous_attempt})
        messages.append({"role": "user", "content":
            f"The validator found these errors. Fix them and return the complete "
            f"corrected .mmd file:\n\n{json.dumps(errors, indent=2)}"})
    # call your LLM here and return the generated .mmd text
    ...

MAX_ROUNDS = 5
user_request = "Write a 4-bar melody in G major at 120 BPM"
mmd = generate_mmd(user_request)

for round_ in range(MAX_ROUNDS):
    report = validate(mmd)
    if report['valid']:
        print(f"Valid after {round_+1} round(s).")
        break
    errors = [e for e in report['errors'] if e['severity'] == 'error']
    print(f"Round {round_+1}: {len(errors)} error(s) — retrying…")
    mmd = generate_mmd(user_request, previous_attempt=mmd, errors=errors)
else:
    print("Did not converge. Manual review required.")
```

---

## Workflow B — Interactive Chat Session

Use this when working with an LLM in a conversational interface (Claude.ai,
ChatGPT, etc.). The LLM generates .mmd; you run the validator and paste the
JSON back.

### Prompt template for first turn

```
Please write a .mmd file for: [your request]

Requirements:
- Follow the .mmd spec (attached)
- End your response with the .mmd content in a code block tagged ```mmd
- I will run it through the validator and paste back any errors
```

### Prompt template for correction turns

```
The validator returned these errors. Please fix the complete .mmd file:

[paste JSON errors here]

Return the corrected file in a ```mmd code block.
```

### Tip: ask for self-validation first

You can ask the LLM to count its own semicolons before you run the validator:

```
Before giving me the file, verify: for each measure in each T-track,
count the semicolons and confirm the count equals (beats_per_measure - 1).
Show your count, then give me the file.
```

This catches the most common class of error before it reaches the validator.

---

## Workflow C — Claude Code / Automated Pipeline

For fully automated pipelines using Claude Code or a script:

```bash
#!/usr/bin/env bash
# generate_and_validate.sh

SPEC="musical-markdown-spec.md"
REQUEST="$1"
MAX_ROUNDS=5
OUTFILE="output.mmd"

for i in $(seq 1 $MAX_ROUNDS); do
    echo "=== Round $i ==="

    if [ $i -eq 1 ]; then
        # First generation — no error context
        claude -p "$(cat $SPEC)

Write a .mmd file for: $REQUEST
Return only the .mmd content, no explanation." > "$OUTFILE"
    else
        # Correction round — include error JSON
        ERRORS=$(python mmd_validator.py "$OUTFILE" --json)
        claude -p "$(cat $SPEC)

The following .mmd file has validation errors. Fix ALL errors and return
the complete corrected file. Return only the .mmd content.

CURRENT FILE:
$(cat $OUTFILE)

VALIDATION ERRORS:
$ERRORS" > "$OUTFILE"
    fi

    python mmd_validator.py "$OUTFILE"
    if [ $? -eq 0 ]; then
        echo "✓ Valid after $i round(s)."
        exit 0
    fi
done

echo "✗ Did not converge after $MAX_ROUNDS rounds."
exit 1
```

---

## Common Error Patterns and Their Fixes

The validator messages are designed to be directly actionable. Here is how to
interpret the most common ones:

### "Semicolon count: got N, need M"

**Meaning:** The beat-slot grid is malformed. A 4/4 measure needs exactly 3
semicolons; 3/4 needs 2; 6/8 needs 5; etc.

**Most common cause:** Forgetting to write empty `;` placeholder slots after
a note that spans multiple beats.

```
# WRONG — whole note with no held slots (0 semicolons in 4/4)
T1: C4/1|

# CORRECT — whole note with 3 held-beat placeholders (3 semicolons)
T1: C4/1;;;|

# WRONG — half note pair with no held slots (1 semicolon; needs 3)
T1: C4/2;A4/2|

# CORRECT
T1: C4/2;;A4/2;|
```

### "Measure total N QN ≠ expected M QN"

**Meaning:** The notes in the measure don't add up to the right length.

**Common causes:**
- Used `/2` when `/4` was intended (half note instead of quarter)
- Used `/3` as a denominator (not a power of 2 — use tuplets instead)
- Left out a note that should be there

### "Beat slot N comma-subdivisions overfill one beat"

**Meaning:** You wrote `C4/4,D4/4` in one beat slot — two quarter notes that
together = 2 beats, which is more than the 1-beat slot allows.

**Fix:** Use `;` to separate beats. Commas are only for true subdivisions
(e.g., two eighth notes that together fill one beat):

```
# WRONG
T1: C4/4,D4/4;E4/4;F4/4|     # two quarters in one slot = 2 beats

# CORRECT — each quarter gets its own slot
T1: C4/4;D4/4;E4/4;F4/4|

# CORRECT subdivision — two eighths share one slot (together = 1 beat)
T1: C4/8,D4/8;E4/4;F4/4;G4/4|
```

### "Note has no duration and no previous note to inherit from"

**Meaning:** A note at the start of a measure has no `/N` duration and can't
inherit from a previous note (inheritance resets at each bar line).

**Fix:** Always give the first note in a measure an explicit duration.

### "Tone track measure counts are inconsistent"

**Meaning:** T1 has 4 measures but T2 has 3. All tone tracks must have the
same count to be time-synchronized.

**Fix:** Add a rest measure (`R/M`) to the shorter track, or remove a measure
from the longer one.

---

## Understanding Warnings vs Errors

| Severity | Meaning | Action required |
|----------|---------|----------------|
| `error`  | Structural or syntactic violation. The file cannot be correctly parsed or performed. | **Must fix** before file is considered valid. |
| `warning`| Non-standard but parseable (e.g., unrecognized key signature, octave > 8). | Fix if possible; validator still returns `valid: true`. |

---

## Normalizing for Diff

Use `--normalize` to strip all whitespace before comparing two versions:

```bash
python mmd_validator.py v1.mmd --normalize > v1_norm.mmd
python mmd_validator.py v2.mmd --normalize > v2_norm.mmd
diff v1_norm.mmd v2_norm.mmd
```

This is useful when an LLM regenerates a file with different spacing but
claims it hasn't changed the music.
